"""Agent activity logger — tracks execution time, task assignments, and errors natively."""
import logging
import sqlite3
import time
import json
from config import DB_PATH

logging.basicConfig(level=logging.INFO)
file_logger = logging.getLogger("agent_activity")

class AgentLogger:
    """Manages tracking metrics for agent executions across the system."""
    
    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS agent_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                task_id TEXT,
                execution_time_s REAL,
                status TEXT,
                error_msg TEXT,
                created_at REAL
            )
        """)
        conn.commit()
        conn.close()

    def log_execution(self, agent_name: str, task_id: str, duration_s: float, error: str = None):
        """Record the performance and outcome of a specific agent's execution."""
        status = "error" if error else "success"
        
        # Log to stdout natively
        if error:
            file_logger.error(f"[{agent_name}] Task {task_id} FAILED in {duration_s:.2f}s | Error: {error}")
        else:
            file_logger.info(f"[{agent_name}] Task {task_id} SUCCESS in {duration_s:.2f}s")
            
        # Log to SQLite for persistent monitoring
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute(
                "INSERT INTO agent_metrics (agent_name, task_id, execution_time_s, status, error_msg, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (agent_name, task_id, duration_s, status, error, time.time())
            )
            conn.commit()
            conn.close()
        except Exception as e:
            file_logger.error(f"Failed to write metrics to SQLite: {e}")

global_agent_logger = AgentLogger()

def track_agent_execution(func):
    """
    Decorator for tracking the execution time, errors, and task_id of an agent's execute() method.
    """
    import functools

    @functools.wraps(func)
    async def wrapper(self, context: dict, *args, **kwargs):
        # Ensure context is safe dictionary and grab a default ID
        safe_ctx = context if isinstance(context, dict) else {}
        task_id = safe_ctx.get("task_id", getattr(self, "current_task_id", "unknown_task"))
        agent_name = getattr(self, "agent_type", self.__class__.__name__)
        if hasattr(agent_name, "value"):
            agent_name = agent_name.value
            
        start_time = time.time()
        error_msg = None
        
        try:
            result = await func(self, context, *args, **kwargs)
            return result
        except Exception as e:
            error_msg = str(e)
            raise
        finally:
            duration = time.time() - start_time
            global_agent_logger.log_execution(agent_name, task_id, duration, error=error_msg)

    return wrapper
