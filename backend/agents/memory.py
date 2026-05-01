"""Memory agent — persistent learning storage with SQLite + FTS5.

Fix #5: retrieve_previous_results and get_relevant_learnings now use
SQLite FTS5 full-text search for significantly better context recall.
"""
import sqlite3
import json
import time
import logging
from typing import Any
from agents.base import BaseAgent
from core.models import AgentResult, AgentType, Learning, Reflection
from config import DB_PATH

logger = logging.getLogger(__name__)


class MemoryAgent(BaseAgent):
    agent_type = AgentType.MEMORY
    system_prompt = ""

    def __init__(self):
        self._short_term_memory: dict[str, dict[str, Any]] = {}
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS learnings (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                insight TEXT NOT NULL,
                source_task_id TEXT,
                relevance_score REAL DEFAULT 1.0,
                times_applied INTEGER DEFAULT 0,
                created_at REAL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS reflections (
                task_id TEXT PRIMARY KEY,
                successes TEXT,
                failures TEXT,
                key_learnings TEXT,
                strategy_improvement TEXT,
                confidence_score INTEGER,
                total_cost REAL,
                total_tokens INTEGER,
                created_at REAL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS task_history (
                task_id TEXT PRIMARY KEY,
                description TEXT,
                status TEXT,
                cost REAL,
                tokens INTEGER,
                created_at REAL,
                inputs TEXT,
                outputs TEXT
            )
        """)

        # Column migrations
        c.execute("PRAGMA table_info(task_history)")
        columns = [row[1] for row in c.fetchall()]
        if "inputs" not in columns:
            c.execute("ALTER TABLE task_history ADD COLUMN inputs TEXT")
        if "outputs" not in columns:
            c.execute("ALTER TABLE task_history ADD COLUMN outputs TEXT")

        # ── FTS5 virtual tables for full-text search (Fix #5) ─────────────────
        c.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS task_history_fts
            USING fts5(
                task_id UNINDEXED,
                description,
                outputs,
                content='task_history',
                content_rowid='rowid'
            )
        """)
        c.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS learnings_fts
            USING fts5(
                id UNINDEXED,
                insight,
                category,
                content='learnings',
                content_rowid='rowid'
            )
        """)

        # Triggers to keep FTS tables in sync
        c.executescript("""
            CREATE TRIGGER IF NOT EXISTS task_history_ai AFTER INSERT ON task_history BEGIN
                INSERT INTO task_history_fts(rowid, task_id, description, outputs)
                VALUES (new.rowid, new.task_id, new.description, new.outputs);
            END;

            CREATE TRIGGER IF NOT EXISTS task_history_ad AFTER DELETE ON task_history BEGIN
                INSERT INTO task_history_fts(task_history_fts, rowid, task_id, description, outputs)
                VALUES ('delete', old.rowid, old.task_id, old.description, old.outputs);
            END;

            CREATE TRIGGER IF NOT EXISTS task_history_au AFTER UPDATE ON task_history BEGIN
                INSERT INTO task_history_fts(task_history_fts, rowid, task_id, description, outputs)
                VALUES ('delete', old.rowid, old.task_id, old.description, old.outputs);
                INSERT INTO task_history_fts(rowid, task_id, description, outputs)
                VALUES (new.rowid, new.task_id, new.description, new.outputs);
            END;

            CREATE TRIGGER IF NOT EXISTS learnings_ai AFTER INSERT ON learnings BEGIN
                INSERT INTO learnings_fts(rowid, id, insight, category)
                VALUES (new.rowid, new.id, new.insight, new.category);
            END;

            CREATE TRIGGER IF NOT EXISTS learnings_ad AFTER DELETE ON learnings BEGIN
                INSERT INTO learnings_fts(learnings_fts, rowid, id, insight, category)
                VALUES ('delete', old.rowid, old.id, old.insight, old.category);
            END;

            CREATE TRIGGER IF NOT EXISTS learnings_au AFTER UPDATE ON learnings BEGIN
                INSERT INTO learnings_fts(learnings_fts, rowid, id, insight, category)
                VALUES ('delete', old.rowid, old.id, old.insight, old.category);
                INSERT INTO learnings_fts(rowid, id, insight, category)
                VALUES (new.rowid, new.id, new.insight, new.category);
            END;
        """)

        conn.commit()
        conn.close()

    # ─── Short-Term Memory ────────────────────────────────────────

    def set_short_term(self, task_id: str, key: str, value: Any):
        if task_id not in self._short_term_memory:
            self._short_term_memory[task_id] = {}
        self._short_term_memory[task_id][key] = value

    def get_short_term(self, task_id: str, key: str, default: Any = None) -> Any:
        return self._short_term_memory.get(task_id, {}).get(key, default)

    def get_all_short_term(self, task_id: str) -> dict[str, Any]:
        return self._short_term_memory.get(task_id, {})

    def clear_short_term(self, task_id: str):
        self._short_term_memory.pop(task_id, None)

    # ─── Long-Term Memory ─────────────────────────────────────────

    def store_task(self, task_id: str, description: str, status: str,
                   cost: float, tokens: int,
                   inputs: dict = None, outputs: dict = None):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            """INSERT OR REPLACE INTO task_history
               (task_id, description, status, cost, tokens, created_at, inputs, outputs)
               VALUES (?,?,?,?,?,?,?,?)""",
            (task_id, description, status, cost, tokens, time.time(),
             json.dumps(inputs) if inputs else None,
             json.dumps(outputs) if outputs else None)
        )
        conn.commit()
        conn.close()

    def retrieve_previous_results(self, query: str, limit: int = 5) -> list[dict]:
        """Full-text search over past task history (Fix #5: FTS5 replaces LIKE)."""
        # Build FTS5 query — join meaningful words with OR for broad matching
        words = [w.lower() for w in query.split() if len(w) > 3]
        if not words:
            return []

        fts_query = " OR ".join(words)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute(
                """SELECT th.task_id, th.description, th.status, th.outputs
                   FROM task_history th
                   JOIN task_history_fts fts ON th.rowid = fts.rowid
                   WHERE task_history_fts MATCH ?
                   ORDER BY rank, th.created_at DESC
                   LIMIT ?""",
                (fts_query, limit)
            )
            rows = c.fetchall()
        except sqlite3.OperationalError:
            # FTS not available — graceful fallback to LIKE
            cond = " OR ".join(["description LIKE ? OR outputs LIKE ?" for _ in words])
            params = [f"%{w}%" for w in words for _ in range(2)]
            c.execute(
                f"SELECT task_id, description, status, outputs FROM task_history WHERE {cond} ORDER BY created_at DESC LIMIT ?",
                params + [limit]
            )
            rows = c.fetchall()
        finally:
            conn.close()

        results = []
        for r in rows:
            try:
                out = json.loads(r[3]) if r[3] else None
            except Exception:
                out = r[3]
            results.append({"task_id": r[0], "description": r[1], "status": r[2], "outputs": out})
        return results

    def get_task_history(self, limit: int = 20) -> list[dict]:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM task_history ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()
        return [
            {
                "task_id": r[0], "description": r[1], "status": r[2],
                "cost": r[3], "tokens": r[4], "created_at": r[5],
                "inputs":  json.loads(r[6]) if r[6] else None,
                "outputs": json.loads(r[7]) if r[7] else None,
            }
            for r in rows
        ]

    # ─── Reflections & Learnings ──────────────────────────────────

    def store_learning(self, learning: Learning):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO learnings VALUES (?,?,?,?,?,?,?)",
            (learning.id, learning.category, learning.insight,
             learning.source_task_id, learning.relevance_score,
             learning.times_applied, learning.created_at)
        )
        conn.commit()
        conn.close()

    def store_reflection(self, reflection: Reflection):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO reflections VALUES (?,?,?,?,?,?,?,?,?)",
            (reflection.task_id,
             json.dumps(reflection.successes), json.dumps(reflection.failures),
             json.dumps(reflection.key_learnings), reflection.strategy_improvement,
             reflection.confidence_score, reflection.total_cost,
             reflection.total_tokens, reflection.created_at)
        )
        conn.commit()
        conn.close()

    def get_relevant_learnings(self, task_description: str, limit: int = 5) -> list[Learning]:
        """FTS5-powered learning retrieval (Fix #5)."""
        words = [w.lower() for w in task_description.split() if len(w) > 3]
        if not words:
            return []

        fts_query = " OR ".join(words)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute(
                """SELECT l.*
                   FROM learnings l
                   JOIN learnings_fts fts ON l.rowid = fts.rowid
                   WHERE learnings_fts MATCH ?
                   ORDER BY rank, l.relevance_score DESC, l.times_applied DESC
                   LIMIT ?""",
                (fts_query, limit)
            )
            rows = c.fetchall()
        except sqlite3.OperationalError:
            cond = " OR ".join(["insight LIKE ?" for _ in words])
            params = [f"%{w}%" for w in words]
            c.execute(
                f"SELECT * FROM learnings WHERE {cond} ORDER BY relevance_score DESC LIMIT ?",
                params + [limit]
            )
            rows = c.fetchall()
        finally:
            conn.close()

        return [
            Learning(id=r[0], category=r[1], insight=r[2],
                     source_task_id=r[3], relevance_score=r[4],
                     times_applied=r[5], created_at=r[6])
            for r in rows
        ]

    def get_all_learnings(self) -> list[Learning]:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM learnings ORDER BY created_at DESC LIMIT 50")
        rows = c.fetchall()
        conn.close()
        return [
            Learning(id=r[0], category=r[1], insight=r[2],
                     source_task_id=r[3], relevance_score=r[4],
                     times_applied=r[5], created_at=r[6])
            for r in rows
        ]

    def get_reflections(self, limit: int = 10) -> list[dict]:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM reflections ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()
        return [
            {
                "task_id": r[0],
                "successes": json.loads(r[1]),
                "failures": json.loads(r[2]),
                "key_learnings": json.loads(r[3]),
                "strategy_improvement": r[4],
                "confidence_score": r[5],
                "total_cost": r[6],
                "total_tokens": r[7],
                "created_at": r[8],
            }
            for r in rows
        ]

    def increment_applied(self, learning_id: str):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "UPDATE learnings SET times_applied = times_applied + 1 WHERE id = ?",
            (learning_id,)
        )
        conn.commit()
        conn.close()

    async def execute(self, context: dict) -> AgentResult:
        return AgentResult(
            agent=self.agent_type, success=True,
            output="Memory agent ready", tokens_used=0,
            cost_usd=0.0, model_used="none"
        )
