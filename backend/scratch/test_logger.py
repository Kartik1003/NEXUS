import asyncio
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from core.models import AgentResult, AgentType
from agents.base import BaseAgent
from core.logger import global_agent_logger

class FakeEmployee(BaseAgent):
    agent_type = AgentType.ENGINEERING
    
    async def execute(self, context: dict) -> AgentResult:
        await asyncio.sleep(0.1)
        if context.get("crash"):
            raise ValueError("Employee crashed!")
        return AgentResult(agent=self.agent_type, success=True, output="Did some work")

async def test_logger():
    agent = FakeEmployee()
    ctx = {"task_id": "test_log_001"}
    
    print("[+] Running successful execution...")
    await agent.execute(ctx)
    
    print("[+] Running failing execution...")
    try:
        ctx["crash"] = True
        await agent.execute(ctx)
    except Exception as e:
        print(f"Caught expected crash: {e}")
        
    print("\n[+] Reading from sqlite DB to verify telemetry...")
    import sqlite3
    from config import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT agent_name, task_id, execution_time_s, status, error_msg FROM agent_metrics")
    rows = c.fetchall()
    
    for r in rows:
        print(f"Recorded DB Log: {r}")
        
    conn.close()

if __name__ == "__main__":
    asyncio.run(test_logger())
