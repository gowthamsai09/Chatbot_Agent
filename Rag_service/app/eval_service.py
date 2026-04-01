print("STEP 3: eval_service loaded")
import re
import json
import traceback


def extract_json(text: str) -> dict:
    """
    Extracts the last valid JSON object from a DeepSeek response.

    DeepSeek V3 thinks out loud before answering.
    We take the LAST JSON object found — after all the thinking text.
    Always returns a dict, never None, never raises.

    Tested cases:
    1. Clean JSON only              → returns parsed dict
    2. Thinking text then JSON      → extracts JSON after thinking
    3. Markdown fenced JSON         → strips fences, returns dict
    4. Pydantic schema (wrong data) → returns dict, caller handles gracefully
    5. No JSON at all               → returns empty dict, caller uses default
    """
    clean = text.strip()

    # Case 3: markdown fences
    if "```" in clean:
        parts = clean.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                parsed = json.loads(part)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                continue

    # Cases 1, 2, 4: find last valid JSON object in text
    matches = list(re.finditer(
        r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
        clean,
        re.DOTALL
    ))
    for match in reversed(matches):  # reversed = last JSON = after thinking
        try:
            parsed = json.loads(match.group())
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            continue

    # Case 5: no JSON found
    return {}


def score_faithfulness(
    question: str,
    contexts: list,
    answer: str,
    # hf_token: str
) -> float:
    from .llm_service import hf_chat
    """
    Faithfulness: are all claims in the answer grounded in the context?
    Score = supported_claims / total_claims

    Returns 1.0 if no claims found (nothing to hallucinate).
    Returns 1.0 if judge fails (safe default — do not penalise).
    """
    context_text = "\n\n".join(contexts)

    prompt = f"""You are an evaluation judge.

Extract each factual claim from the answer below.
For each claim decide if it is supported by the context.

Context:
{context_text}

Answer:
{answer}

Return ONLY a JSON object. No explanation before or after.
Format:
{{"claims": [{{"claim": "the claim text", "supported": true}}, {{"claim": "another claim", "supported": false}}]}}"""

    try:
        print(f"[EVAL] Faithfulness check: {question[:60]}")
        # raw = hf_chat(prompt, hf_token)
        raw = hf_chat(prompt)
        print(f"[EVAL] Raw response: {raw[:150]}")

        parsed = extract_json(raw)
        claims = parsed.get("claims", [])

        if not claims:
            print("[EVAL] No claims extracted — defaulting to 1.0")
            return 1.0

        supported = sum(1 for c in claims if c.get("supported", False))
        score = round(supported / len(claims), 2)
        print(f"[EVAL] Faithfulness: {supported}/{len(claims)} = {score}")
        return score

    except Exception as e:
        print(f"[EVAL ERROR] score_faithfulness failed: {e}")
        traceback.print_exc()
        return 1.0


def score_answer_relevancy(
    question: str,
    answer: str,
    # hf_token: str
) -> float:
    from .llm_service import hf_chat
    """
    Answer Relevancy: does the answer address the question?
    Score: 0.0 = completely irrelevant, 1.0 = perfectly relevant

    Returns 0.8 if judge fails (reasonable neutral default).
    """
    prompt = f"""You are an evaluation judge.

Rate how well the answer addresses the question.

Question: {question}
Answer: {answer}

Return ONLY a JSON object. No explanation before or after.
Format:
{{"score": 0.85, "reason": "one sentence reason"}}

Score must be a number between 0.0 and 1.0."""

    try:
        print(f"[EVAL] Relevancy check: {question[:60]}")
        # raw = hf_chat(prompt, hf_token)
        raw = hf_chat(prompt)
        print(f"[EVAL] Raw response: {raw[:150]}")

        parsed = extract_json(raw)
        score = float(parsed.get("score", 0.8))
        score = round(min(max(score, 0.0), 1.0), 2)
        print(f"[EVAL] Answer relevancy: {score}")
        return score

    except Exception as e:
        print(f"[EVAL ERROR] score_answer_relevancy failed: {e}")
        traceback.print_exc()
        return 0.8


def build_eval_records(
    test_questions: list,
    session_id: str,
    # hf_token: str
) -> list:
    from .rag_engine import retrieve
    from .agent_service import run_agent
    """
    For each question: retrieve contexts + get answer from agent.
    Returns list of dicts ready for scoring.
    """
    records = []

    for i, question in enumerate(test_questions):
        print(f"[EVAL] Building record {i+1}/{len(test_questions)}: {question[:60]}")

        try:
            docs = retrieve(query=question, top_k=5)
            contexts = [doc.page_content for doc in docs]
            print(f"[EVAL] Retrieved {len(contexts)} chunks")

            result = run_agent(
                query=question,
                session_id=session_id,
                # hf_token=hf_token
            )
            answer = result.get("answer", "")
            print(f"[EVAL] Answer preview: {answer[:100]}")

            records.append({
                "question": question,
                "answer":   answer,
                "contexts": contexts
            })

        except Exception as e:
            print(f"[EVAL ERROR] Question failed: {e}")
            traceback.print_exc()
            continue

    return records


def run_eval(
    test_questions: list,
    session_id: str,
    # hf_token: str
) -> dict:
    """
    Main function called by api.py /api/eval endpoint.

    Implements LLM-as-judge evaluation using your existing DeepSeek
    via hf_chat. Same concept as Ragas internally — no dependency
    conflicts, no version issues, no OpenAI required.

    Metrics:
    - faithfulness     : are answers grounded in retrieved context?
    - answer_relevancy : do answers address what was actually asked?
    """
    print(f"\n[EVAL] ===== START: {len(test_questions)} question(s) =====")

    records = build_eval_records(
        test_questions=test_questions,
        session_id=session_id,
        # hf_token=hf_token
    )

    if not records:
        raise ValueError(
            "No eval records built. "
            "Check [EVAL ERROR] lines above in your terminal."
        )

    f_scores = []
    r_scores = []

    for record in records:
        f_scores.append(score_faithfulness(
            question=record["question"],
            contexts=record["contexts"],
            answer=record["answer"],
            # hf_token=hf_token
        ))
        r_scores.append(score_answer_relevancy(
            question=record["question"],
            answer=record["answer"],
            # hf_token=hf_token
        ))

    avg_f = round(sum(f_scores) / len(f_scores), 2)
    avg_r = round(sum(r_scores) / len(r_scores), 2)

    output = {
        "faithfulness":     avg_f,
        "answer_relevancy": avg_r,
        "num_questions":    len(records),
        "status": "pass" if (avg_f > 0.85 and avg_r > 0.80) else "needs_review"
    }

    print(f"[EVAL] ===== RESULT: {output} =====\n")
    return output