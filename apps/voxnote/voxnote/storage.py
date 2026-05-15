"""SQLite storage for VoxNote sessions, segments, and summaries.

Schema is intentionally tiny:

* ``sessions``    — one per "press record"
* ``segments``    — every finalized transcript chunk
* ``summaries``   — incremental + final summaries; one of each kind per session

Full-text search uses SQLite FTS5 over ``segments.text``.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    started_at REAL NOT NULL,
    ended_at REAL,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    language TEXT,
    asr_name TEXT,
    llm_name TEXT
);

CREATE TABLE IF NOT EXISTS segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    start_ms INTEGER NOT NULL,
    end_ms INTEGER NOT NULL,
    speaker TEXT,
    text TEXT NOT NULL,
    confidence REAL
);
CREATE INDEX IF NOT EXISTS idx_segments_session ON segments(session_id);

CREATE TABLE IF NOT EXISTS summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,            -- 'incremental' | 'final'
    generated_at REAL NOT NULL,
    summary_md TEXT NOT NULL,
    todos_json TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_summaries_session ON summaries(session_id);

-- FTS5 mirror of segments.text for fast search.
CREATE VIRTUAL TABLE IF NOT EXISTS segments_fts USING fts5(
    text,
    session_id UNINDEXED,
    content='segments',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS segments_ai AFTER INSERT ON segments BEGIN
    INSERT INTO segments_fts(rowid, text, session_id) VALUES (new.id, new.text, new.session_id);
END;

CREATE TRIGGER IF NOT EXISTS segments_ad AFTER DELETE ON segments BEGIN
    INSERT INTO segments_fts(segments_fts, rowid, text, session_id)
        VALUES ('delete', old.id, old.text, old.session_id);
END;
"""


@dataclass
class Session:
    id: str
    title: str
    started_at: float
    ended_at: float | None = None
    duration_ms: int = 0
    language: str | None = None
    asr_name: str | None = None
    llm_name: str | None = None


@dataclass
class Segment:
    session_id: str
    start_ms: int
    end_ms: int
    text: str
    speaker: str | None = None
    confidence: float | None = None
    id: int | None = None


@dataclass
class Summary:
    session_id: str
    kind: str          # 'incremental' | 'final'
    generated_at: float
    summary_md: str
    todos: list[str] = field(default_factory=list)


class Storage:
    """Tiny repository over a SQLite file. All methods are thread-safe."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self._conn = _connect(self.db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        with self._tx() as cur:
            cur.executescript(SCHEMA)

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Cursor]:
        cur = self._conn.cursor()
        try:
            cur.execute("BEGIN")
            yield cur
            cur.execute("COMMIT")
        except Exception:
            cur.execute("ROLLBACK")
            raise
        finally:
            cur.close()

    # -- sessions -----------------------------------------------------------

    def create_session(self, *, title: str, asr_name: str, llm_name: str) -> Session:
        sess = Session(
            id=str(uuid.uuid4()),
            title=title,
            started_at=time.time(),
            asr_name=asr_name,
            llm_name=llm_name,
        )
        with self._tx() as cur:
            cur.execute(
                "INSERT INTO sessions(id, title, started_at, asr_name, llm_name) VALUES (?,?,?,?,?)",
                (sess.id, sess.title, sess.started_at, sess.asr_name, sess.llm_name),
            )
        return sess

    def end_session(self, session_id: str) -> None:
        now = time.time()
        with self._tx() as cur:
            cur.execute(
                """
                UPDATE sessions
                SET ended_at = ?,
                    duration_ms = CAST((? - started_at) * 1000 AS INTEGER)
                WHERE id = ?
                """,
                (now, now, session_id),
            )

    def list_sessions(self, limit: int = 100) -> list[Session]:
        rows = self._conn.execute(
            "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_session(r) for r in rows]

    def get_session(self, session_id: str) -> Session | None:
        row = self._conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return _row_to_session(row) if row else None

    def rename_session(self, session_id: str, title: str) -> None:
        with self._tx() as cur:
            cur.execute("UPDATE sessions SET title = ? WHERE id = ?", (title, session_id))

    def delete_session(self, session_id: str) -> None:
        with self._tx() as cur:
            cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    # -- segments -----------------------------------------------------------

    def add_segment(self, segment: Segment) -> int:
        with self._tx() as cur:
            cur.execute(
                """
                INSERT INTO segments(session_id, start_ms, end_ms, speaker, text, confidence)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    segment.session_id,
                    segment.start_ms,
                    segment.end_ms,
                    segment.speaker,
                    segment.text,
                    segment.confidence,
                ),
            )
            return cur.lastrowid or 0

    def list_segments(self, session_id: str) -> list[Segment]:
        rows = self._conn.execute(
            "SELECT * FROM segments WHERE session_id = ? ORDER BY start_ms ASC",
            (session_id,),
        ).fetchall()
        return [
            Segment(
                id=r["id"],
                session_id=r["session_id"],
                start_ms=r["start_ms"],
                end_ms=r["end_ms"],
                speaker=r["speaker"],
                text=r["text"],
                confidence=r["confidence"],
            )
            for r in rows
        ]

    # -- summaries ---------------------------------------------------------

    def upsert_summary(self, summary: Summary) -> None:
        with self._tx() as cur:
            cur.execute(
                "DELETE FROM summaries WHERE session_id = ? AND kind = ?",
                (summary.session_id, summary.kind),
            )
            cur.execute(
                """
                INSERT INTO summaries(session_id, kind, generated_at, summary_md, todos_json)
                VALUES (?,?,?,?,?)
                """,
                (
                    summary.session_id,
                    summary.kind,
                    summary.generated_at,
                    summary.summary_md,
                    json.dumps(summary.todos, ensure_ascii=False),
                ),
            )

    def get_latest_summary(self, session_id: str) -> Summary | None:
        row = self._conn.execute(
            """
            SELECT * FROM summaries
            WHERE session_id = ?
            ORDER BY CASE kind WHEN 'final' THEN 0 ELSE 1 END, generated_at DESC
            LIMIT 1
            """,
            (session_id,),
        ).fetchone()
        if not row:
            return None
        return Summary(
            session_id=row["session_id"],
            kind=row["kind"],
            generated_at=row["generated_at"],
            summary_md=row["summary_md"],
            todos=json.loads(row["todos_json"] or "[]"),
        )

    # -- search ------------------------------------------------------------

    def search(self, query: str, limit: int = 50) -> list[dict]:
        if not query.strip():
            return []
        rows = self._conn.execute(
            """
            SELECT s.session_id, s.text, sess.title, sess.started_at,
                   snippet(segments_fts, 0, '<b>', '</b>', '...', 8) AS snip
            FROM segments_fts
            JOIN segments s ON s.id = segments_fts.rowid
            JOIN sessions sess ON sess.id = s.session_id
            WHERE segments_fts MATCH ?
            ORDER BY sess.started_at DESC
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self._conn.close()


def _row_to_session(row: sqlite3.Row) -> Session:
    return Session(
        id=row["id"],
        title=row["title"],
        started_at=row["started_at"],
        ended_at=row["ended_at"],
        duration_ms=row["duration_ms"] or 0,
        language=row["language"],
        asr_name=row["asr_name"],
        llm_name=row["llm_name"],
    )
