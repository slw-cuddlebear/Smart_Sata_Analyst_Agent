"""会话记忆：按 session_id 保存最近的问答对"""
from collections import defaultdict, deque
from threading import Lock


class ConversationStore:
    def __init__(self, max_turns: int = 5):
        # 每个会话最多保留最近 N 轮
        self._store: dict[str, deque] = defaultdict(lambda: deque(maxlen=max_turns))
        self._lock = Lock()

    def get(self, session_id: str) -> list[dict]:
        """返回该会话的历史 [{"question":..., "answer":...}, ...]"""
        with self._lock:
            return list(self._store[session_id])

    def append(self, session_id: str, question: str, answer: str) -> None:
        """追加一轮问答"""
        with self._lock:
            self._store[session_id].append({"question": question, "answer": answer})

    def clear(self, session_id: str) -> None:
        """清空某个会话"""
        with self._lock:
            self._store.pop(session_id, None)

    def list_sessions(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())


_store = ConversationStore()


def get_store() -> ConversationStore:
    return _store