import asyncio
import logging
import time
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TaskItem:
    task_id: str
    description: str
    priority: int = 1  # Lower number = higher priority if we use PriorityQueue later
    enqueued_at: float = 0.0

class TaskQueueSystem:
    def __init__(self, max_concurrent: int = 3):
        # We use asyncio.Queue to handle tasks asynchronously 24x7
        self.queue: asyncio.Queue[TaskItem] = asyncio.Queue()
        self.worker_task: Optional[asyncio.Task] = None
        self._orchestrator = None  # Will be injected
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        self.active_tasks: set[str] = set()
        self.running_tasks: dict[str, asyncio.Task] = {}

    def set_orchestrator(self, orchestrator):
        self._orchestrator = orchestrator

    async def enqueue_task(self, task_id: str, description: str, priority: int = 1):
        """Add a new task to the continuous execution system."""
        item = TaskItem(task_id=task_id, description=description, priority=priority, enqueued_at=time.time())
        await self.queue.put(item)
        logger.info(f"[TaskQueue] Enqueued task {task_id} (Queue size: {self.queue.qsize()})")

    async def worker_loop(self):
        """The 24x7 background worker loop that automatically handles tasks."""
        logger.info("[TaskQueue] Worker loop started. Monitoring for incoming tasks...")
        
        while True:
            try:
                # Wait for the next task
                item: TaskItem = await self.queue.get()
                logger.info(f"[TaskQueue] Picked up task {item.task_id} from queue.")
                
                if not self._orchestrator:
                    logger.error("[TaskQueue] Orchestrator not configured! Cannot execute task.")
                    self.queue.task_done()
                    continue

                # Execute the task via orchestrator in background
                logger.info(f"[TaskQueue] Spawning background task for {item.task_id}.")
                task = asyncio.create_task(self._run_task(item))
                self.running_tasks[item.task_id] = task
                    
            except asyncio.CancelledError:
                logger.info("[TaskQueue] Worker loop cancelled.")
                break
            except Exception as e:
                logger.error(f"[TaskQueue] Unexpected error in worker loop: {e}", exc_info=True)
                await asyncio.sleep(1)  # Prevent tight failure loop

    async def _run_task(self, item: TaskItem):
        """Execute a task respecting concurrency limits.
        Acquires the semaphore, runs the orchestrator, updates active task set, and marks completion.
        """
        async with self.semaphore:
            self.active_tasks.add(item.task_id)
            logger.info(f"[TaskQueue] Starting task {item.task_id}. Active count: {len(self.active_tasks)}")
            try:
                result = await self._orchestrator.solve(item.description, task_id=item.task_id)
                logger.info(f"[TaskQueue] Task {item.task_id} completed. Status: {result.get('status')}")
            except asyncio.CancelledError:
                logger.warning(f"[TaskQueue] Task {item.task_id} was manually cancelled.")
                if self._orchestrator:
                    try:
                        await self._orchestrator._emit("task_complete", "system", {
                            "status": "cancelled",
                            "result": "Task was manually stopped by user.",
                            "task_id": item.task_id
                        }, task_id=item.task_id)
                    except Exception:
                        pass
                raise
            except Exception as e:
                logger.error(f"[TaskQueue] Error orchestrating task {item.task_id}: {e}", exc_info=True)
            finally:
                self.active_tasks.discard(item.task_id)
                self.running_tasks.pop(item.task_id, None)
                self.queue.task_done()
                logger.info(f"[TaskQueue] Finished task {item.task_id}. Active count: {len(self.active_tasks)}")

    async def stop_task(self, task_id: str):
        """Stop a specific task and remove from queue if not started."""
        if task_id in self.running_tasks:
            logger.info(f"[TaskQueue] Cancelling running task {task_id}")
            self.running_tasks[task_id].cancel()
            return {"status": "cancelled", "task_id": task_id}
            
        # Check if in queue
        items = []
        found = False
        while not self.queue.empty():
            item = self.queue.get_nowait()
            if item.task_id == task_id:
                found = True
                self.queue.task_done()
            else:
                items.append(item)
        for i in items:
            self.queue.put_nowait(i)
            
        if found:
            logger.info(f"[TaskQueue] Removed task {task_id} from queue")
            if self._orchestrator:
                try:
                    # Async task in background to emit so we don't block
                    asyncio.create_task(self._orchestrator._emit("task_complete", "system", {
                        "status": "cancelled",
                        "result": "Task was removed from queue before starting.",
                        "task_id": task_id
                    }, task_id=task_id))
                except Exception:
                    pass
            return {"status": "removed_from_queue", "task_id": task_id}
            
        return {"status": "not_found", "task_id": task_id}

    def start_worker(self):
        """Spawn the worker loop as an asyncio background task."""
        if self.worker_task is None or self.worker_task.done():
            self.worker_task = asyncio.create_task(self.worker_loop())
            logger.info("[TaskQueue] Background worker spawned.")

    def stop_worker(self):
        """Gracefully stop the background worker."""
        if self.worker_task and not self.worker_task.done():
            self.worker_task.cancel()

    def get_queue_status(self):
        """Return current queue metrics.
        Returns dict with queue size, active task count, and max concurrency.
        """
        return {
            "queue_size": self.queue.qsize(),
            "active_count": len(self.active_tasks),
            "max_concurrent": self.max_concurrent,
        }

# Global task queue singleton
task_queue = TaskQueueSystem()
