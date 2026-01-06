import os
import json
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

HF_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")
if not HF_TOKEN:
    raise RuntimeError("HUGGINGFACEHUB_API_TOKEN not set")

# Hugging Face DeepSeek LLM

MODEL_ID = "deepseek-ai/DeepSeek-V3.2"

hf_client = InferenceClient(
    token=HF_TOKEN
)

def hf_chat(prompt: str) -> str:
    """
    Single-turn chat completion using DeepSeek.
    """
    response = hf_client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=300,
    )

    return response.choices[0].message.content.strip()

# RAG Prompt (Grounded)

def build_rag_prompt(question: str, context: str) -> str:
    return f"""
You are an AI assistant.
Answer the question using ONLY the context below.
If the answer is not contained in the context, say:
"I do not have enough information."

Context:
{context}

Question:
{question}

Return VALID JSON only.

{{"answer": "..."}}
""".strip()


def generate_answer(question: str, context: str) -> str:
    prompt = build_rag_prompt(question, context)
    response = hf_chat(prompt)

    try:
        parsed = json.loads(response)
        return parsed.get("answer", "I do not have enough information.")
    except json.JSONDecodeError:
        return "I do not have enough information."