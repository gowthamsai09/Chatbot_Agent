from typing import TypedDict, List
import json
import requests
from langgraph.graph import StateGraph, END


# Agent State
class AgentState(TypedDict):
    user_query: str
    retrieved_docs: List[str]
    final_answer: str
    coverage: str
    path_taken: str
    memory: str
    # hf_token: str


# Agent Nodes
def retrieve_node(state: AgentState):
    from .rag_engine import retrieve
    query = state["user_query"]
    results = retrieve(query=query, top_k=3)
    texts = [doc.page_content for doc in results]
    return {"retrieved_docs": texts}


def coverage_node(state: AgentState):
    from .llm_service import hf_chat
    context = "\n\n".join(state.get("retrieved_docs", []))

    prompt = f"""
        You are evaluating information coverage.

        Conversation history:
        {state.get("memory", "")}

        User question:
        {state['user_query']}

        Context:
        {context}

        Choose ONE:
        - DIRECT  → context clearly answers the question
        - PARTIAL → context is relevant but incomplete (definitions, components, background)
        - NONE    → context is unrelated

        If the question is comparative ("better than", "difference between"),
        and the context explains only one side,
        choose PARTIAL.

        Return ONLY one word.
        """
    # response = hf_chat(prompt, state["hf_token"]).upper()
    response = hf_chat(prompt).upper()

    if "DIRECT" in response:
        coverage = "DIRECT"
    elif "PARTIAL" in response:
        coverage = "PARTIAL"
    else:
        coverage = "NONE"

    return {"coverage": coverage}


def answer_node(state: AgentState):
    from .llm_service import hf_chat
    from .eval_service import extract_json
    context = "\n\n".join(state.get("retrieved_docs", []))

    prompt = f"""
        You are answering a follow-up question in a conversation.
        Use the conversation history ONLY to understand what the user is referring to.
        DO NOT quote or summarize the conversation history.
        DO NOT treat it as factual evidence.

        Conversation history (for reference only):
        {state.get("memory", "")}
        Use ONLY the retrieved context below as evidence.

        Use the conversation history to understand what the user is referring to.
        If the current question is vague (e.g. "that", "it", "this"),
        interpret it as a follow-up to the most recent topic.

        Use ONLY the retrieved context to answer.

        Context:
        {context}

        Current question:
        {state['user_query']}

        Return VALID JSON:
        {{"answer": "..."}}
        """
    # response = hf_chat(prompt, state["hf_token"])
    response = hf_chat(prompt)

    try:
        # parsed = extract_json(response)
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
    from .llm_service import hf_chat
    from .eval_service import extract_json
    context = "\n\n".join(state.get("retrieved_docs", []))

    prompt = f"""
        You are answering a follow-up question in a conversation.
        Use the conversation history ONLY to understand what the user is referring to.
        DO NOT quote or summarize the conversation history.
        DO NOT treat it as factual evidence.
        Conversation history (for reference only):
        {state.get("memory", "")}

        Use ONLY the retrieved context below as evidence.
        The context may not fully answer the question.
        Do NOT hallucinate or use external knowledge.

        If a comparison is requested but only partial information is available:
        - Explain what the context supports
        - Clearly state what is missing
        - Provide a cautious, evidence-based explanation

        Context:
        {context}

        Question:
        {state['user_query']}

        Return VALID JSON:
        {{"answer": "..."}}
        """
    # response = hf_chat(prompt, state["hf_token"])
    response = hf_chat(prompt)

    try:
        parsed = json.loads(response)
        # parsed = extract_json(response)
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
def run_agent(query: str, session_id: str) -> dict:
    from .memory_service import get_memory, update_memory
    memory = get_memory(session_id)

    initial_state: AgentState = {
        "user_query": query,
        "retrieved_docs": [],
        "final_answer": "",
        "coverage": "",
        "path_taken": "",
        "memory": memory,
        # "hf_token": hf_token
    }

    result = agent.invoke(initial_state)

    answer = result.get("final_answer", "")
    update_memory(session_id, query, answer)

    return {
        "answer": answer,
        "coverage": result.get("coverage"),
        "path_taken": result.get("path_taken")
    }