import asyncio
import json
import os
import sys

# Ensure backend is in path
sys.path.append(os.getcwd())

from backend.core.orchestrator import Orchestrator

async def run_test():
    print("Initializing Orchestrator...")
    o = Orchestrator()
    task = "Create a simple 2-day social media plan for a brand named 'Flash'."
    print(f"Running task: {task}")
    
    try:
        # We need to mock or ignore the callback since we're in a script
        async def dummy_callback(event):
            # print(f"Event: {event.event} | Agent: {event.data.get('agent')}")
            pass
            
        o.set_event_callback(dummy_callback)
        
        result = await o.solve(task)
        print("\n--- RESULT ---")
        print(json.dumps(result, indent=2))
        print("--------------\n")
        
        if result.get("status") == "success":
            print("SUCCESS: Task solved correctly.")
        else:
            print(f"FAILED: Task returned status {result.get('status')}")
            
    except Exception as e:
        print(f"CRASHED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_test())
