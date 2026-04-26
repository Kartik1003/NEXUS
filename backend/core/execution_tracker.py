import time
import json
import sqlite3
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from config import DB_PATH

class ExecutionTracker:
    def __init__(self):
        # Store execution step logs in memory by task_id
        # Format: { "task_id_1": [ { step1 }, { step2 } ] }
        self._logs: Dict[str, List[dict]] = {}
        self._start_times: Dict[str, float] = {}
        # Initialize SQLite DB and cleanup old logs
        self._init_db()
        self.cleanup()

    def log_event(self, task_id: str, event_type: str, data: dict):
        """Log a generic event (e.g. agent_message) for a task, persisting to SQLite."""
        if task_id not in self._logs:
            self._logs[task_id] = []
        
        entry = {
            "task_id": task_id,
            "event": event_type,
            "timestamp": datetime.now().isoformat(),
            **data
        }
        self._logs[task_id].append(entry)
        
        # Persist to SQLite
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO execution_logs (task_id, event, agent, agent_name, status, message, model, duration, timestamp, raw_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    entry.get("task_id"),
                    entry.get("event"),
                    entry.get("agent"),
                    entry.get("agent_name"),
                    entry.get("status"),
                    entry.get("message"),
                    entry.get("model"),
                    entry.get("duration"),
                    entry.get("timestamp"),
                    json.dumps(entry)
                )
            )
            conn.commit()
        except Exception as e:
            # Log error silently; in production could use proper logging
            print(f"[ExecutionTracker] DB insert error: {e}")
        finally:
            conn.close()
        
        from core.websocket_handler import ws_manager
        ws_manager.trigger_log_broadcast_sync(task_id, entry)

    def log_step(
        self,
        task_id: str,
        agent_level: str,
        agent_name: str,
        status: str,
        message: str,
        model: Optional[str] = None
    ):
        tracker_key = f"{task_id}_{agent_name}"
        now = time.time()
        
        if status == "started":
            self._start_times[tracker_key] = now
            duration_s = 0.0
        else:
            start_time = self._start_times.get(tracker_key, now)
            duration_s = round(now - start_time, 3)

        data = {
            "agent": agent_level,
            "agent_name": agent_name,
            "status": status,
            "message": message,
            "duration": f"{duration_s}s"
        }
        if model:
            data["model"] = model
            
        self.log_event(task_id, "execution_log", data)

    def get_task_execution(self, task_id: str) -> List[dict]:
        """Retrieve all tracked steps for a specific task workflow.
        Falls back to SQLite if not present in memory (e.g., after restart)."""
        if task_id in self._logs:
            return self._logs[task_id]
        # Query SQLite
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT raw_json FROM execution_logs WHERE task_id = ? ORDER BY id", (task_id,))
            rows = cur.fetchall()
            logs = [json.loads(row[0]) for row in rows]
            # Cache in memory for future fast access
            if logs:
                self._logs[task_id] = logs
            return logs
        except Exception as e:
            print(f"[ExecutionTracker] DB fetch error: {e}")
            return []
        finally:
            conn.close()

    def get_all(self) -> Dict[str, List[dict]]:
        return self._logs

    # Internal helper methods
    def _init_db(self):
        """Create execution_logs table if it doesn't exist."""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS execution_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                event TEXT NOT NULL,
                agent TEXT,
                agent_name TEXT,
                status TEXT,
                message TEXT,
                model TEXT,
                duration TEXT,
                timestamp TEXT,
                raw_json TEXT
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_task_id ON execution_logs (task_id);")
        conn.commit()
        conn.close()

    def cleanup(self):
        """Delete logs older than 7 days based on timestamp."""
        cutoff = datetime.utcnow() - timedelta(days=7)
        cutoff_iso = cutoff.isoformat()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM execution_logs WHERE timestamp < ?", (cutoff_iso,))
        conn.commit()
        conn.close()

    def store_file(self, task_id: str, employee_handle: str, filename: str, content: str):
        """Store a produced file for later retrieval."""
        if task_id not in self._logs:
            self._logs[task_id] = []
        entry = {
            "task_id": task_id,
            "event": "file_produced",
            "employee_handle": employee_handle,
            "filename": filename,
            "content": content,
            "size": len(content),
            "timestamp": datetime.now().isoformat(),
        }
        self._logs[task_id].append(entry)
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO execution_logs (task_id, event, agent_name, message, raw_json, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (task_id, "file_produced", employee_handle, filename, json.dumps(entry), entry["timestamp"])
            )
            conn.commit()
        except Exception as e:
            print(f"[ExecutionTracker] store_file DB error: {e}")
        finally:
            conn.close()

    def get_files(self, task_id: str) -> list[dict]:
        """Return all files produced for a task, in order."""
        logs = self.get_task_execution(task_id)
        return [
            log for log in logs
            if log.get("event") == "file_produced"
        ]

    def log_agent_chat(self, task_id: str, from_handle: str, from_name: str,
                       to_name: str, message: str):
        """Log a direct employee-to-employee message."""
        entry = {
            "task_id": task_id,
            "event": "agent_chat",
            "from_handle": from_handle,
            "from_name": from_name,
            "to_name": to_name,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        if task_id not in self._logs:
            self._logs[task_id] = []
        self._logs[task_id].append(entry)

    def get_agent_chats(self, task_id: str) -> list[dict]:
        """Return all employee chat messages for a task."""
        logs = self.get_task_execution(task_id)
        return [log for log in logs if log.get("event") == "agent_chat"]

# Global singleton
execution_tracker = ExecutionTracker()
