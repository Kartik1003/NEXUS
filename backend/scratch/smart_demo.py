import asyncio
import logging
import sys
import os
import json

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.orchestrator import Orchestrator

# Configure logging to see the SMART CALL logs
logging.basicConfig(level=logging.INFO, format="%(message)s")

async def run_smart_demo():
    orchestrator = Orchestrator()
    
    tasks = [
        ("Calculate 2+2", "simple"),
        ("Write a Python script to scrape news headlines using BeautifulSoup.", "complex")
    ]
    
    for task_desc, expected_complexity in tasks:
        print(f"\n{'='*60}")
        print(f"TASK: {task_desc}")
        print(f"EXPECTED COMPLEXITY: {expected_complexity}")
        print(f"{'='*60}")
        
        # We manually set complexity for the demo to show the model scaling
        # In reality, the RouterAgent determines this.
        result = await orchestrator.solve(task_desc)
        
        print("\n--- PERFORMANCE SUMMARY ---")
        print(f"Final Model Choice: {result.get('execution_log')[-2].get('model_used', 'N/A') if len(result.get('execution_log')) > 1 else 'N/A'}")
        print(f"Total Task Cost: ${result.get('cost', {}).get('total_cost_usd', 0)}")

if __name__ == "__main__":
    asyncio.run(run_smart_demo())
