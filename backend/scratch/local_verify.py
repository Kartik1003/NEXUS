import asyncio
import logging
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.orchestrator import Orchestrator

# Configure logging to see the multi-call logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

async def run_diagnostic():
    orchestrator = Orchestrator()
    task = "Calculate the first 5 prime numbers using a list comprehension."
    
    print(f"Executing Task: {task}")
    print("-" * 50)
    
    result = await orchestrator.solve(task)
    
    print("-" * 50)
    print(f"Status: {result.get('status', 'Done')}")
    print(f"Final Code:\n{result.get('final_code')}")
    print(f"Final Output: {result.get('final_output')}")
    print(f"Total Cost: ${result.get('cost', {}).get('total_cost_usd', 0)}")
    print(f"Total Tokens: {result.get('cost', {}).get('total_tokens', 0)}")

if __name__ == "__main__":
    asyncio.run(run_diagnostic())
