"""Memory agent — persistent learning storage with SQLite."""
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
    system_prompt = ""  # Memory agent doesn't use LLM directly

    def __init__(self):
        # Short-term memory: ephemerally store context per task
        self._short_term_memory: dict[str, dict[str, Any]] = {}
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database and perform migrations."""
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

        # Migration: ensure inputs and outputs columns exist in task_history
        c.execute("PRAGMA table_info(task_history)")
        columns = [row[1] for row in c.fetchall()]
        if "inputs" not in columns:
            c.execute("ALTER TABLE task_history ADD COLUMN inputs TEXT")
        if "outputs" not in columns:
            c.execute("ALTER TABLE task_history ADD COLUMN outputs TEXT")

        conn.commit()
        conn.close()

    # ─── 1. Short-Term Memory ─────────────────────────────────────

    def set_short_term(self, task_id: str, key: str, value: Any):
        """Store a temporary value for the duration of a task."""
        if task_id not in self._short_term_memory:
            self._short_term_memory[task_id] = {}
        self._short_term_memory[task_id][key] = value

    def get_short_term(self, task_id: str, key: str, default: Any = None) -> Any:
        """Retrieve a temporary value for a task."""
        return self._short_term_memory.get(task_id, {}).get(key, default)

    def get_all_short_term(self, task_id: str) -> dict[str, Any]:
        """Get all short-term memory keys for a task."""
        return self._short_term_memory.get(task_id, {})

    def clear_short_term(self, task_id: str):
        """Clear short-term memory when a task is completed."""
        self._short_term_memory.pop(task_id, None)

    # ─── 2. Long-Term Memory (History) ────────────────────────────

    def store_task(self, task_id: str, description: str, status: str, cost: float, tokens: int, inputs: dict = None, outputs: dict = None):
        """Store detailed task history including inputs and results."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            """INSERT OR REPLACE INTO task_history 
               (task_id, description, status, cost, tokens, created_at, inputs, outputs) 
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                task_id, 
                description, 
                status, 
                cost, 
                tokens, 
                time.time(),
                json.dumps(inputs) if inputs else None,
                json.dumps(outputs) if outputs else None
            )
        )
        conn.commit()
        conn.close()

    def retrieve_previous_results(self, query: str, limit: int = 5) -> list[dict]:
        """Search past tasks for similar patterns or outputs."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Simple exact word matching for demonstration
        keywords = [word.lower() for word in query.split() if len(word) > 3]
        if not keywords:
            conn.close()
            return []

        conditions = " OR ".join(["description LIKE ? OR outputs LIKE ?" for _ in keywords])
        params = [f"%{kw}%" for kw in keywords for _ in range(2)]

        c.execute(
            f"SELECT task_id, description, status, outputs FROM task_history WHERE {conditions} ORDER BY created_at DESC LIMIT ?",
            params + [limit]
        )
        rows = c.fetchall()
        conn.close()

        results = []
        for r in rows:
            try:
                out = json.loads(r[3]) if r[3] else None
            except:
                out = r[3]
            results.append({
                "task_id": r[0],
                "description": r[1],
                "status": r[2],
                "outputs": out
            })
        return results

    def get_task_history(self, limit: int = 20) -> list[dict]:
        """Get recent task history."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM task_history ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()
        return [
            {
                "task_id": r[0], 
                "description": r[1], 
                "status": r[2],
                "cost": r[3], 
                "tokens": r[4], 
                "created_at": r[5],
                "inputs": json.loads(r[6]) if r[6] else None,
                "outputs": json.loads(r[7]) if r[7] else None
            }
            for r in rows
        ]

    # ─── 3. Reflections & Learnings (Unchanged logic) ─────────────

    def store_learning(self, learning: Learning):
        """Store a learning in the database."""
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
        """Store a task reflection."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO reflections VALUES (?,?,?,?,?,?,?,?,?)",
            (reflection.task_id,
             json.dumps(reflection.successes),
             json.dumps(reflection.failures),
             json.dumps(reflection.key_learnings),
             reflection.strategy_improvement,
             reflection.confidence_score,
             reflection.total_cost,
             reflection.total_tokens,
             reflection.created_at)
        )
        conn.commit()
        conn.close()

    def get_relevant_learnings(self, task_description: str, limit: int = 5) -> list[Learning]:
        """Retrieve relevant learnings using keyword matching."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        keywords = [w.lower() for w in task_description.split() if len(w) > 3]
        if not keywords:
            conn.close()
            return []

        conditions = " OR ".join(["insight LIKE ?" for _ in keywords])
        params = [f"%{kw}%" for kw in keywords]

        c.execute(
            f"SELECT * FROM learnings WHERE {conditions} ORDER BY relevance_score DESC, times_applied DESC LIMIT ?",
            params + [limit]
        )
        rows = c.fetchall()
        conn.close()

        return [
            Learning(
                id=r[0], category=r[1], insight=r[2],
                source_task_id=r[3], relevance_score=r[4],
                times_applied=r[5], created_at=r[6]
            )
            for r in rows
        ]

    def get_all_learnings(self) -> list[Learning]:
        """Get all stored learnings."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM learnings ORDER BY created_at DESC LIMIT 50")
        rows = c.fetchall()
        conn.close()
        return [
            Learning(
                id=r[0], category=r[1], insight=r[2],
                source_task_id=r[3], relevance_score=r[4],
                times_applied=r[5], created_at=r[6]
            )
            for r in rows
        ]

    def get_reflections(self, limit: int = 10) -> list[dict]:
        """Get recent reflections."""
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
        """Increment times_applied counter for a learning."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "UPDATE learnings SET times_applied = times_applied + 1 WHERE id = ?",
            (learning_id,)
        )
        conn.commit()
        conn.close()

    def compress_memory(self, max_entries: int = 100):
        """Remove low-value learnings to keep memory concise."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM learnings")
        count = c.fetchone()[0]
        if count > max_entries:
            c.execute(
                "DELETE FROM learnings WHERE id IN (SELECT id FROM learnings ORDER BY relevance_score ASC, times_applied ASC LIMIT ?)",
                (count - max_entries,)
            )
        conn.commit()
        conn.close()

    async def execute(self, context: dict) -> AgentResult:
        """Memory agent doesn't execute via LLM — it's called directly."""
        return AgentResult(
            agent=self.agent_type,
            success=True,
            output="Memory operations are performed directly, not via execute().",
        )
