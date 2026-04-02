print("STEP 4: llm_service loaded")
import random
from huggingface_hub import InferenceClient

MODEL_ID = "deepseek-ai/DeepSeek-V3-0324"


def _pick_hf_token() -> str:
    from .settings import HF_TOKEN_POOL, get_hf_token
    """Pick a token: user-provided token takes precedence over pool"""
    user_token = get_hf_token()
    if user_token:
        return user_token
    if not HF_TOKEN_POOL:
        print("No HF token available")
        return None
    return random.choice(HF_TOKEN_POOL)


def hf_chat(prompt: str) -> str:
    token = _pick_hf_token()

    if not token:
        return "LLM not available (no HuggingFace token configured)."

    try:
        client = InferenceClient(token=token)

        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=300,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("LLM call failed:", str(e))
        return "LLM service error."


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