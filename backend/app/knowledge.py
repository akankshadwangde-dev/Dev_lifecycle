"""Local full-text index over Confluence pages, resolved tickets and pages written by the studio.

SQLite FTS5 with BM25 ranking. Phase 2 adds embeddings for semantic search next to it.
"""

import re
import sqlite3
import threading

from .config import settings

STOP_WORDS = {
    "the", "and", "for", "with", "from", "that", "this", "are", "was", "since", "into", "not", "but",
    "get", "gets", "has", "have", "instead", "only", "all", "any", "can", "must", "should", "will",
}


class KnowledgeIndex:
    def __init__(self, path):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        with self.lock:
            self.conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5("
                "project_id UNINDEXED, source UNINDEXED, ref UNINDEXED, title, body, "
                "url UNINDEXED, updated UNINDEXED)"
            )

    def upsert(self, project_id: int, source: str, ref: str, title: str, body: str,
               url: str = "", updated: str = "") -> None:
        with self.lock:
            self.conn.execute("DELETE FROM docs WHERE project_id = ? AND ref = ?", (project_id, ref))
            self.conn.execute("INSERT INTO docs VALUES (?, ?, ?, ?, ?, ?, ?)",
                              (project_id, source, ref, title, body, url, updated))
            self.conn.commit()

    def search(self, project_id: int, query: str, limit: int = 6) -> list[dict]:
        terms = [t for t in re.findall(r"[A-Za-z0-9_]{3,}", query) if t.lower() not in STOP_WORDS][:40]
        if not terms:
            return []
        match = " OR ".join(f'"{t}"' for t in dict.fromkeys(terms))
        with self.lock:
            rows = self.conn.execute(
                "SELECT source, ref, title, body, url, updated, bm25(docs, 0, 0, 0, 4.0, 1.0, 0, 0) AS rank "
                "FROM docs WHERE docs MATCH ? AND project_id = ? ORDER BY rank LIMIT ?",
                (match, project_id, limit),
            ).fetchall()
        if not rows:
            return []
        best = rows[0][6] or -1.0
        return [{
            "source": source, "ref": ref, "title": title, "body": body[:2500],
            "excerpt": body[:220] + ("…" if len(body) > 220 else ""), "url": url, "updated": updated,
            "score": max(1, round(100 * rank / best)) if best else 0,
        } for source, ref, title, body, url, updated, rank in rows]

    def counts(self, project_id: int) -> dict[str, int]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT source, count(*) FROM docs WHERE project_id = ? GROUP BY source", (project_id,)
            ).fetchall()
        return dict(rows)

    def delete_refs(self, project_id: int, refs: list[str], prefixes: tuple[str, ...] = ()) -> None:
        with self.lock:
            for ref in refs:
                self.conn.execute("DELETE FROM docs WHERE project_id = ? AND ref = ?", (project_id, ref))
            for prefix in prefixes:
                self.conn.execute("DELETE FROM docs WHERE project_id = ? AND ref LIKE ?", (project_id, f"{prefix}%"))
            self.conn.commit()

    def clear_source(self, project_id: int, source: str) -> None:
        with self.lock:
            self.conn.execute("DELETE FROM docs WHERE project_id = ? AND source = ?", (project_id, source))
            self.conn.commit()


_index: KnowledgeIndex | None = None


def get_index() -> KnowledgeIndex:
    global _index
    if _index is None:
        _index = KnowledgeIndex(settings.knowledge_path)
    return _index


def reindex(project_id: int, issues, confluence) -> dict[str, int]:
    """Pull Confluence pages and resolved tickets into the index. Pages written by the studio are kept."""
    index = get_index()
    counts = {"confluence": 0, "ticket": 0}
    if confluence is not None:
        index.clear_source(project_id, "confluence")
        for page in confluence.pages():
            index.upsert(project_id, "confluence", page["ref"], page["title"], page["body"],
                         page.get("url", ""), page.get("updated", ""))
            counts["confluence"] += 1
    if issues is not None:
        index.clear_source(project_id, "ticket")
        for t in issues.resolved_items():
            body = f"{t.get('description', '')}\nResolution: {t.get('resolution', '')}"
            index.upsert(project_id, "ticket", t["key"], t["title"], body, t.get("url", ""))
            counts["ticket"] += 1
    return counts
