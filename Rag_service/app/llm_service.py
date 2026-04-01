print("STEP 4: llm_service loaded")
import random
from huggingface_hub import InferenceClient

MODEL_ID = "deepseek-ai/DeepSeek-V3.2"


def _pick_hf_token() -> str:
    from .settings import HF_TOKEN_POOL, get_hf_token
    """Pick a token: user-provided token takes precedence over pool"""
    user_token = get_hf_token()
    
    # If user provided a token, use it
    if user_token:
        return user_token
    
    # Otherwise fall back to pool
    if not HF_TOKEN_POOL:
        raise RuntimeError(
            "No HuggingFace token available. "
            "Either provide a token via UI or set HF_TOKEN_POOL environment variable."
        )
    return random.choice(HF_TOKEN_POOL)


def hf_chat(prompt: str) -> str:
    token = _pick_hf_token()
    client = InferenceClient(token=token)

    response = client.chat.completions.create(
        model=MODEL_ID,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=300,
    )

    return response.choices[0].message.content.strip()


def build_rag_prompt(question: str, context: str) -> str:
    return f"""
Answer the question using ONLY the context below.
If the answer is not in the context, say:
"I do not have enough information."

Context:
{context}

Question:
{question}
""".strip()


def generate_answer(question: str, context: str) -> str:
    prompt = build_rag_prompt(question, context)
    return hf_chat(prompt)