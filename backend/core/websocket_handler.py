import asyncio
import logging
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class WebSocketExecutionManager:
    def __init__(self):
        # Map task_id -> set of active WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Global connections (listening to all tasks, if needed)
        self.global_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, task_id: str = None):
        """Accept a websocket connection, optionally binding to a specific task_id."""
        await websocket.accept()
        
        if task_id:
            # 1. Register connection
            if task_id not in self.active_connections:
                self.active_connections[task_id] = set()
            self.active_connections[task_id].add(websocket)
            logger.info(f"[WS] Client connected to task {task_id}")
            
            # 2. REPLAY: Fetch and send historical logs for this task
            from core.execution_tracker import execution_tracker
            import json
            
            historical_logs = execution_tracker.get_task_execution(task_id)
            if historical_logs:
                logger.info(f"[WS] Replaying {len(historical_logs)} logs for task {task_id}")
                for entry in historical_logs:
                    message = json.dumps({
                        "type": "execution_log",
                        "data": entry
                    })
                    try:
                        await websocket.send_text(message)
                    except Exception as e:
                        logger.warning(f"[WS] Failed to replay log to socket: {e}")
                        break
        else:
            self.global_connections.add(websocket)
            logger.info("[WS] Global client connected")

    def disconnect(self, websocket: WebSocket, task_id: str = None):
        """Cleanly remove a websocket connection stringly bound to memory pools."""
        if task_id and task_id in self.active_connections:
            self.active_connections[task_id].discard(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
            logger.info(f"[WS] Client disconnected from task {task_id}")
        elif websocket in self.global_connections:
            self.global_connections.discard(websocket)
            logger.info("[WS] Global client disconnected")

    async def broadcast_log(self, task_id: str, log_entry: dict):
        """Push a newly generated log entry immediately to any listening frontends."""
        import json
        message = json.dumps({
            "type": "execution_log",
            "data": log_entry
        })
        
        dead_sockets = set()
        
        # Dispatch to specific task listeners
        if task_id in self.active_connections:
            for ws in self.active_connections[task_id]:
                try:
                    await ws.send_text(message)
                except Exception as e:
                    logger.warning(f"[WS] Failed to send to socket: {e}")
                    dead_sockets.add((task_id, ws))
                    
        # Dispatch to global listeners
        for ws in self.global_connections:
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.warning(f"[WS] Failed to send to global socket: {e}")
                dead_sockets.add((None, ws))

        # Cleanup severed connections locally explicitly
        for t_id, ws in dead_sockets:
            self.disconnect(ws, task_id=t_id)

    def trigger_log_broadcast_sync(self, task_id: str, log_entry: dict):
        """Safely trigger an async broadcast from a synchronous block using the current event loop."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast_log(task_id, log_entry))
        except RuntimeError:
            logger.error("[WS] Failed to dispatch broadcast: No active asyncio loop.")

# Singleton manager
ws_manager = WebSocketExecutionManager()
