"""FastAPI application — HTTP + WebSocket entry point."""
import json
import logging
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from config import ALLOWED_ORIGINS
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from core.orchestrator import Orchestrator
from core.llm import llm_client
from core.models import WSEvent
from agents.memory import MemoryAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager
from core.task_queue import task_queue

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pass the global orchestrator to the task queue
    task_queue.set_orchestrator(orchestrator)
    # Start the continuous worker loop
    task_queue.start_worker()
    yield
    # Graceful shutdown
    task_queue.stop_worker()

app = FastAPI(
    title="AegisOps AI — Multi-Department Orchestration System", 
    version="2.0.0",
    lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connected WebSocket clients
ws_clients: set[WebSocket] = set()
orchestrator = Orchestrator()
memory = MemoryAgent()


# ─── WebSocket Broadcasting ──────────────────────────────────────

async def broadcast_event(event: WSEvent):
    """Send event to all connected WebSocket clients."""
    global ws_clients
    data = json.dumps({"event": event.event, "data": event.data})
    dead = set()
    for ws in ws_clients:
        try:
            await ws.send_text(data)
        except Exception:
            dead.add(ws)
    ws_clients -= dead


# Wire up orchestrator events
orchestrator.set_event_callback(broadcast_event)


# ─── WebSocket Endpoint ──────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.add(ws)
    logger.info(f"WebSocket connected. Total: {len(ws_clients)}")
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            # Command dispatcher
            msg_type = msg.get('type')
            match msg_type:
                case 'ping':
                    await ws.send_text(json.dumps({'type': 'pong'}))
                case 'enqueue':
                    # Expect 'task' field
                    task_desc = msg.get('task')
                    if not task_desc:
                        await ws.send_text(json.dumps({'type': 'error', 'error': 'Missing task description'}))
                    else:
                        import uuid
                        task_id = f'task_queue_{uuid.uuid4().hex[:8]}'
                        # Use default priority 1
                        await task_queue.enqueue_task(task_id, task_desc, 1)
                        await ws.send_text(json.dumps({'type': 'enqueued', 'task_id': task_id}))
                case 'get_status':
                    from core.execution_tracker import execution_tracker
                    status = execution_tracker.get_all()
                    await ws.send_text(json.dumps({'type': 'status', 'data': status}))
                case _:
                    logger.warning(f'Unknown WebSocket message type: {msg_type}')

    except WebSocketDisconnect:
        ws_clients.discard(ws)
        logger.info(f"WebSocket disconnected. Total: {len(ws_clients)}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_clients.discard(ws)


@app.websocket("/ws/execution/{task_id}")
async def websocket_execution_tracker(ws: WebSocket, task_id: str):
    """
    Dedicated bidirectional WebSocket endpoint for streaming live tracking arrays
    to the frontend strictly scoped by an active task_id.
    """
    from core.websocket_handler import ws_manager
    from core.execution_tracker import execution_tracker
    import json
    
    await ws_manager.connect(ws, task_id=task_id)
    
    # Upon connection natively sync them with any existing backlog buffer
    existing_logs = execution_tracker.get_task_execution(task_id)
    for log in existing_logs:
        await ws.send_text(json.dumps({
            "type": "execution_log",
            "data": log
        }))
        
    try:
        while True:
            # Keep connection alive silently, relying completely on pushes
            data = await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws, task_id=task_id)
    except Exception as e:
        logger.error(f"[WS] Execution Tracker error: {e}")
        ws_manager.disconnect(ws, task_id=task_id)


@app.websocket("/ws/execution_monitor")
async def websocket_global_monitor(ws: WebSocket):
    """Global listener for all execution logs across the system."""
    from core.websocket_handler import ws_manager
    await ws_manager.connect(ws)  # task_id=None adds to global_connections
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
    except Exception as e:
        logger.error(f"[WS] Global Monitor error: {e}")
        ws_manager.disconnect(ws)


# ─── REST Endpoints ──────────────────────────────────────────────

class TaskRequest(BaseModel):
    task: str




@app.post("/api/tasks/enqueue")
async def enqueue_task(req: TaskRequest, priority: int = 1):
    """Enqueue a task to the 24x7 asynchronous background execution system."""
    import uuid
    task_id = f"task_queue_{uuid.uuid4().hex[:8]}"
    await task_queue.enqueue_task(task_id, req.task, priority)
    return {"status": "enqueued", "task_id": task_id, "priority": priority}

@app.post("/api/tasks/{task_id}/stop")
async def stop_task_endpoint(task_id: str):
    """Stop or cancel a specific task."""
    result = await task_queue.stop_task(task_id)
    return result


@app.get("/api/history")
async def get_history():
    """Get task execution history."""
    return {
        "tasks": memory.get_task_history(),
        "reflections": memory.get_reflections(),
    }


@app.get("/api/tracker/{task_id}")
async def get_task_tracker(task_id: str):
    """Retrieve detailed real-time tracking array for a specific task."""
    from core.execution_tracker import execution_tracker
    return {
        "task_id": task_id,
        "logs": execution_tracker.get_task_execution(task_id)
    }


@app.get("/api/learnings")
async def get_learnings():
    """Get all stored learnings."""
    return {
        "learnings": [l.model_dump() for l in memory.get_all_learnings()],
    }


@app.get("/api/cost")
async def get_cost():
    """Get current cost summary."""
    return llm_client.get_cost_summary()


@app.post("/api/test")
async def test_pipeline(req: TaskRequest):
    """Test the full parallel pipeline with any task."""
    logger.info(f"--- STARTING TEST PIPELINE for task: {req.task} ---")
    try:
        result = await orchestrator.solve(req.task)
        logger.info("--- TEST PIPELINE COMPLETED SUCCESSFULLY ---")
        return result
    except Exception as e:
        logger.error(f"--- TEST PIPELINE FAILED: {str(e)} ---", exc_info=True)
        return {"error": str(e), "status": "failed"}


@app.get("/api/health")
async def health():
    from config import OPENROUTER_API_KEY
    return {
        "status": "ok",
        "version": "3.0.0",
        "mode": "linear-pipeline",
        "pipeline": "CEO → Executive → Department → Employee",
        "departments": 6,
        "api_key_configured": bool(OPENROUTER_API_KEY),
        "api_key_prefix": OPENROUTER_API_KEY[:10] + "..." if OPENROUTER_API_KEY else None,
    }


# ─── Communication System Endpoints ─────────────────────────────

from core.communication import message_bus


@app.get("/api/messages/stats")
async def get_message_stats():
    """Get aggregate communication statistics."""
    return message_bus.get_stats()

@app.get("/api/queue/status")
async def get_queue_status():
    """Return current task queue metrics."""
    return task_queue.get_queue_status()


@app.get("/api/messages/{task_id}")
async def get_messages(task_id: str):
    """Get all inter-agent messages for a task."""
    return {
        "task_id": task_id,
        "messages": message_bus.get_task_history(task_id),
    }





@app.get("/api/agents/directory")
async def get_agent_directory():
    """Get the full agent directory (all handles, roles, departments)."""
    handles = message_bus.directory.all_handles()
    return {
        "total_agents": len(handles),
        "agents": [message_bus.directory.lookup(h) for h in handles],
    }


@app.get("/api/agents/status")
async def get_agents_status():
    """Get the current operational status of all agents based on the ACTIVE task only."""
    from core.execution_tracker import execution_tracker

    agent_status_map = {}
    all_logs = execution_tracker.get_all()

    if not all_logs:
        return agent_status_map

    # Only look at the MOST RECENTLY STARTED task to avoid stale completed-status
    # entries from old tasks overwriting fresh "started" entries of the current task.
    latest_task_id = max(
        all_logs.keys(),
        key=lambda tid: next(
            (e.get("timestamp", "") for e in reversed(all_logs[tid]) if e.get("status") == "started"),
            ""
        )
    )

    for log in all_logs.get(latest_task_id, []):
        name = log.get("agent_name")
        if not name:
            continue
        status = log.get("status")
        if status in ["started", "in_progress"]:
            agent_status_map[name] = {
                "status": "working",
                "task": log.get("message"),
                "task_id": latest_task_id,
                "model": log.get("model")
            }
        elif status in ["completed", "failed"]:
            agent_status_map[name] = {
                "status": "idle",
                "last_model": log.get("model")
            }

    return agent_status_map


class PreferenceRequest(BaseModel):
    handle: str
    model: str

class EmployeeModelRequest(BaseModel):
    model: str

@app.post("/api/agents/preferences")
async def update_agent_preference(req: PreferenceRequest):
    """Update manual LLM preference for an employee."""
    from core.model_selector import set_manual_override
    set_manual_override(req.handle, req.model)
    return {"status": "success", "handle": req.handle, "model": req.model}


@app.get("/api/org-chart")
async def get_org_chart():
    """Return the full org chart grouped by department with employees."""
    try:
        from agents.department_agents import DEPARTMENT_REGISTRY
        from agents.employee_agents import EMPLOYEE_REGISTRY

        departments = []
        for dept_key, dept in DEPARTMENT_REGISTRY.items():
            employees = []
            for emp_id, emp in EMPLOYEE_REGISTRY.items():
                if emp.get("department") == dept_key:
                    from core.model_selector import get_manual_override
                    employees.append({
                        "id":     emp_id,
                        "name":   emp.get("name", ""),
                        "role":   emp.get("role", ""),
                        "handle": emp.get("handle", ""),
                        "team":   emp.get("team", ""),
                        "specialty": emp.get("specialty", ""),
                        "assigned_model": get_manual_override(emp.get("handle")) or "auto",
                    })

            departments.append({
                "key":        dept_key,
                "head_name":  dept.get("head_name", "Unknown"),
                "head_title": dept.get("head_title", "Head"),
                "icon":       dept.get("icon", "🏢"),
                "color":      dept.get("color", "#ffffff"),
                "employees":  employees,
            })

        return {
            "executives": [
                {"name": "Strategos", "handle": "@executive", "role": "Executive Strategy Officer"},
                {"name": "Axiom", "handle": "@cto", "role": "Chief Technology Officer"},
                {"name": "Lyra", "handle": "@cmo", "role": "Chief Marketing Officer"},
                {"name": "Atlas", "handle": "@coo", "role": "Chief Operating Officer"},
                {"name": "Iron Man", "handle": "@cfo", "role": "Chief Financial Officer"},
                {"name": "Marvel", "handle": "@chro", "role": "Chief Human Resources Officer"},
            ],
            "departments": departments
        }
    except Exception as e:
        logger.error(f"Error generating org chart: {e}")
        return {"error": str(e), "departments": []}


@app.get("/api/departments")
async def list_departments():
    """List all departments."""
    from agents.department_agents import DEPARTMENT_REGISTRY
    departments = []
    for dept_key, dept in DEPARTMENT_REGISTRY.items():
        departments.append({
            "id": dept_key,
            "name": dept.get("head_name"),
            "title": dept.get("head_title"),
            "icon": dept.get("icon"),
            "color": dept.get("color"),
        })
    return {"departments": departments}


@app.get("/api/departments/{dept_id}")
async def get_department(dept_id: str):
    """Get a specific department's details including employees and status."""
    from agents.department_agents import DEPARTMENT_REGISTRY
    from agents.employee_agents import EMPLOYEE_REGISTRY
    from core.model_selector import get_manual_override
    
    if dept_id not in DEPARTMENT_REGISTRY:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Department not found")
        
    dept = DEPARTMENT_REGISTRY[dept_id]
    employees = []
    
    for emp_id, emp in EMPLOYEE_REGISTRY.items():
        if emp.get("department") == dept_id:
            employees.append({
                "id": emp_id,
                "name": emp.get("name", ""),
                "role": emp.get("role", ""),
                "handle": emp.get("handle", ""),
                "specialty": emp.get("specialty", ""),
                "assigned_model": get_manual_override(emp.get("handle")) or "auto",
            })
            
    return {
        "id": dept_id,
        "name": dept.get("head_name"),
        "title": dept.get("head_title"),
        "icon": dept.get("icon"),
        "color": dept.get("color"),
        "employees": employees
    }


@app.post("/api/employees/{emp_id}/model")
async def update_employee_model(emp_id: str, req: EmployeeModelRequest):
    """Update manual LLM preference using employee ID."""
    from agents.employee_agents import EMPLOYEE_REGISTRY
    from core.model_selector import set_manual_override
    
    if emp_id not in EMPLOYEE_REGISTRY:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Employee not found")
        
    emp = EMPLOYEE_REGISTRY[emp_id]
    handle = emp.get("handle")
    if not handle:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Employee has no valid handle")
        
    set_manual_override(handle, req.model)
    return {"status": "success", "employee_id": emp_id, "handle": handle, "model": req.model}


@app.get("/api/tasks/{task_id}/files")
async def get_task_files(task_id: str):
    """Return all files produced during a task execution."""
    from core.execution_tracker import execution_tracker
    files = execution_tracker.get_files(task_id)
    return {
        "task_id": task_id,
        "total_files": len(files),
        "files": files,
    }


@app.get("/api/tasks/{task_id}/chat")
async def get_task_chat(task_id: str):
    """Return all employee-to-employee messages for a task."""
    from core.execution_tracker import execution_tracker
    chats = execution_tracker.get_agent_chats(task_id)
    return {
        "task_id": task_id,
        "total_messages": len(chats),
        "messages": chats,
    }
