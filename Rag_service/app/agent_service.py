from typing import TypedDict, List
import json

from langgraph.graph import StateGraph, END

from .rag_engine import retrieve
from .llm_service import hf_chat

# Agent State
class AgentState(TypedDict):
    user_query: str
    retrieved_docs: List[str]
    final_answer: str
    coverage: str
    path_taken: str


# Agent Nodes

def retrieve_node(state: AgentState):
    results = retrieve(query=state["user_query"], top_k=3)

    texts = [doc.page_content for doc in results]

    return {
        "retrieved_docs": texts
    }


def coverage_node(state: AgentState):
    context = "\n\n".join(state.get("retrieved_docs", []))

    prompt = f"""
        You are evaluating information coverage.

        User question:
        {state['user_query']}

        Context:
        {context}

        Decide ONE label:
        - DIRECT  (clearly answers the question)
        - PARTIAL (contains related information but not a full answer)
        - NONE    (completely unrelated)

        Be generous. If there is any relevant information, choose PARTIAL.
        Return ONLY one word.
        """
    response = hf_chat(prompt).upper()

    if "DIRECT" in response:
        coverage = "DIRECT"
    elif "PARTIAL" in response:
        coverage = "PARTIAL"
    else:
        coverage = "NONE"

    return {"coverage": coverage}


def answer_node(state: AgentState):
    context = "\n\n".join(state.get("retrieved_docs", []))

    prompt = f"""
        You are answering a question using ONLY the provided context.
        You MAY:
        - expand acronyms
        - rephrase concepts
        - combine multiple parts of the context

        You MUST NOT:
        - use external knowledge
        - invent facts not present in the context

        Context:
        {context}

        Question:
        {state['user_query']}

        Return VALID JSON ONLY.

        {{"answer": "..."}}
        """
    response = hf_chat(prompt)

    try:
        parsed = json.loads(response)
        answer = parsed.get("answer")
    except Exception:
        answer = None

    if not answer or not answer.strip():
        answer = (
            "Based on the available information, here is what I can infer:\n\n"
            + context[:1200]
        )

    return {
        "final_answer": answer,
        "path_taken": "answer"
    }



def synthesize_node(state: AgentState):
    context = "\n\n".join(state.get("retrieved_docs", []))

    prompt = f"""
        You are answering a question using ONLY the provided context.
        You MAY:
        - expand acronyms
        - rephrase concepts
        - combine multiple parts of the context

        You MUST NOT:
        - use external knowledge
        - invent facts not present in the context

        Context:
        {context}

        Question:
        {state['user_query']}

        Return VALID JSON ONLY.

        {{"answer": "..."}}
        """
    response = hf_chat(prompt)

    try:
        parsed = json.loads(response)
        answer = parsed.get("answer")
    except Exception:
        answer = None

    if not answer or not answer.strip():
        answer = (
            "Based on the available information, here is what I can infer:\n\n"
            + context[:1200]
        )
    return {
        "final_answer": answer,
        "path_taken": "synthesize"
    }


# Graph Definition
graph = StateGraph(AgentState)

graph.add_node("retrieve", retrieve_node)
graph.add_node("coverage", coverage_node)
graph.add_node("answer", answer_node)
graph.add_node("synthesize", synthesize_node)

graph.set_entry_point("retrieve")
graph.add_edge("retrieve", "coverage")


def route_after_coverage(state):
    # Never block answering
    if state["coverage"] == "DIRECT":
        return "answer"
    else:
        return "synthesize"



graph.add_conditional_edges(
    "coverage",
    route_after_coverage,
    {
        "answer": "answer",
        "synthesize": "synthesize"
    }
)

graph.add_edge("answer", END)
graph.add_edge("synthesize", END)

agent = graph.compile()

# Public API Function

def run_agent(query: str) -> str:
    initial_state: AgentState = {
        "user_query": query,
        "retrieved_docs": [],
        "final_answer": "",
        "coverage": ""
    }

    result = agent.invoke(initial_state)

    return {
        "answer": result.get("final_answer", "No answer generated."),
        "coverage": result.get("coverage"),
        "path_taken": result.get("path_taken")
    }
