import math
import re
from pathlib import Path


TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


def tokenize(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower()))


class GuidelineStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.documents = self._load_documents()

    def _load_documents(self) -> list[dict[str, str]]:
        docs = []
        for path in sorted(self.data_dir.glob("*.md")):
            raw = path.read_text(encoding="utf-8")
            for index, chunk in enumerate(raw.split("\n## ")):
                chunk = chunk.strip()
                if not chunk:
                    continue
                docs.append(
                    {
                        "id": f"{path.stem}-{index}",
                        "source": path.name,
                        "text": chunk if index == 0 else f"## {chunk}",
                    }
                )
        return docs

    def search(self, query: str, limit: int = 4) -> list[dict[str, str | float]]:
        query_tokens = tokenize(query)
        scored = []
        for doc in self.documents:
            doc_tokens = tokenize(doc["text"])
            overlap = query_tokens & doc_tokens
            if not overlap:
                continue
            score = len(overlap) / math.sqrt(max(len(doc_tokens), 1))
            scored.append({**doc, "score": round(score, 3)})
        return sorted(scored, key=lambda item: item["score"], reverse=True)[:limit]
