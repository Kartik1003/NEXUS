"""Integration test for the asynchronous 24x7 task queue system."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import asyncio
from core.task_queue import task_queue
from dataclasses import dataclass

# Mock the orchestrator to prevent actual LLM API calls during tests
@dataclass
class MockOrchestrator:
    async def solve(self, task: str):
        print(f"[MockOrchestrator] Simulating task execution for: '{task}'")
        await asyncio.sleep(0.5)  # Simulate processing time
        print(f"[MockOrchestrator] Completed task: '{task}'")
        return {"status": "success", "task_type": "testing"}

async def main():
    print("=" * 60)
    print(" CONTINUOUS TASK EXECUTION QUEUE TESTS")
    print("=" * 60)
    
    # 1. Setup
    mock_orch = MockOrchestrator()
    task_queue.set_orchestrator(mock_orch)
    
    # 2. Start the worker loop in the background
    print("\n[+] Starting continuous worker loop...")
    task_queue.start_worker()
    
    # 3. Burst traffic (Enqueuing 3 tasks instantly without blocking)
    print("\n[+] Enqueuing 3 background tasks rapidly...")
    await task_queue.enqueue_task("task_001", "Compile weekly sales report")
    await task_queue.enqueue_task("task_002", "Debug API latency")
    await task_queue.enqueue_task("task_003", "Draft marketing email")
    
    print("\n[+] Main thread is free immediately. Doing other work...")
    for i in range(3):
        print(f"    Main thread simulating HTTP response handling (Tick {i})")
        await asyncio.sleep(0.2)
        
    # Wait for the queue to drain (Wait until worker processes everything)
    print("\n[+] Waiting for background worker to consume the queue...")
    await task_queue.queue.join()
    
    # 4. Graceful Shutdown
    print("\n[+] Stopping background worker gracefully...")
    task_queue.stop_worker()
    print("\nQueue test completed successfully! System handles background execution natively.")

if __name__ == "__main__":
    asyncio.run(main())
