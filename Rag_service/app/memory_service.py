from typing import List, Dict
from collections import defaultdict

# In-memory store (session-scoped)
_memory_store: Dict[str, List[str]] = defaultdict(list)

MAX_TURNS = 5  # keep last N turns only


def get_memory(session_id: str) -> str:
    """
    Returns conversation history as a single string.
    """
    history = _memory_store.get(session_id, [])
    return "\n".join(history)


def update_memory(session_id: str, user_query: str, agent_answer: str):
    if "does not contain" in agent_answer.lower():
        return  # do NOT store failed answers, Saves from Memory poisoning

    entry = f"User: {user_query}\nAssistant: {agent_answer}"
    _memory_store[session_id].append(entry)

    if len(_memory_store[session_id]) > MAX_TURNS:
        _memory_store[session_id] = _memory_store[session_id][-MAX_TURNS:]


def clear_memory(session_id: str):
    _memory_store.pop(session_id, None)