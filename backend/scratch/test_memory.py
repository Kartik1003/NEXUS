"""Test script for the Memory System."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import os
import asyncio
from core.orchestrator import memory_agent
from agents.base import BaseAgent
from core.models import AgentResult, AgentType

class DummyAgent(BaseAgent):
    agent_type = AgentType.ENGINEERING
    
    async def execute(self, context: dict) -> AgentResult:
        # 1. Short-term memory
        self.set_short_term_memory("task_123", "current_hypothesis", "API is down")
        short_val = self.get_short_term_memory("task_123", "current_hypothesis")
        print(f"Short-term memory retrieved: {short_val}")
        
        # 2. Long-term memory retrieve
        past_results = self.recall_long_term_memory("database migration")
        print(f"Long-term memory retrieved across tasks: {len(past_results)} records")
        
        return AgentResult(agent=self.agent_type, success=True, output="Memory tested")

async def main():
    # 1. Store a fake task
    memory_agent.store_task(
        task_id="task_past_88",
        description="Fix database migration script",
        status="success",
        cost=0.01,
        tokens=100,
        inputs={"task_description": "Fix database migration script"},
        outputs={"final_text": "ALTER TABLE users ADD COLUMN age INT;", "aggregator_model": "gpt-4"}
    )
    
    agent = DummyAgent()
    await agent.execute({})
    
    print("Memory Agent short-term state:", memory_agent.get_all_short_term("task_123"))
    memory_agent.clear_short_term("task_123")
    print("After task completion clearing:", memory_agent.get_all_short_term("task_123"))

if __name__ == "__main__":
    asyncio.run(main())
