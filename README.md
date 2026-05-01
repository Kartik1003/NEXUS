# AegisOps — Multi-Agent AI Organization

A production-grade multi-agent AI system that simulates a corporate org chart. Every task flows through a strict **CEO → Executive → Department → Employee** pipeline, with LLM calls happening only at the Employee level.

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- An [OpenRouter](https://openrouter.ai/) API key

### 1. Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY

# Start the server
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** to access the dashboard.

---

## Architecture

```
User Task
   │
   ▼
CEO Agent (Nova)          — Rule-based keyword classifier, zero LLM cost
   │
   ▼
Executive Agent            — Deterministic plan builder, zero LLM cost
   │
   ├──[parallel if different depts]──┐
   ▼                                 ▼
Department Agent(s)        Department Agent(s)
   │                                 │
   ▼                                 ▼
Employee Agent(s)  ◄── ONLY LLM CALLS HAPPEN HERE ──►  Employee Agent(s)
   │
   ▼
ResultAggregator → Final Markdown Report
```

### Departments & Agents
| Department       | VP Head          | Employees                          |
|-----------------|------------------|------------------------------------|
| IT              | Thor (CTO)       | Volt, Byte, Scope, Nimbus, Swift   |
| Finance         | Capt. America    | Mint, Vault, Ledger, Equity        |
| HR              | Loki (CHRO)      | Talent, Compliance, Mentor         |
| Marketing       | Peter (CMO)      | Quill, Flux, Wave, Viral, Vocal    |
| Operations      | Fury (COO)       | Chrono, Prism, Echo, Oracle, Drive |
| Customer Service| Nick (COO)       | Echo, Trainer                      |

---

## Key Features

- **UCB Bandit model selection** — learns which models perform best per task type
- **Parallel department execution** — independent departments run concurrently
- **SQLite FTS5 memory** — full-text search over past task history and learnings
- **Real-time token streaming** — tokens streamed live to the frontend via WebSocket
- **Live org chart** — ReactFlow graph that lights up as agents work
- **Execution playback** — replay any past task step-by-step

---

## Environment Variables

| Variable            | Required | Description                          |
|--------------------|----------|--------------------------------------|
| `OPENROUTER_API_KEY`| ✅ Yes   | Your OpenRouter API key              |
| `ALLOWED_ORIGINS`   | No       | Comma-separated CORS origins         |

All runtime data files (SQLite DB, model stats JSON) are stored in `backend/data/`.

---

## Project Structure

```
agent/
├── backend/
│   ├── agents/
│   │   ├── base.py               # BaseAgent with call_llm helper
│   │   ├── ceo.py                # Nova CEO — keyword classifier
│   │   ├── executive_agent.py    # Deterministic plan builder
│   │   ├── department_agents.py  # Department VP routing
│   │   ├── employee_agents.py    # LLM workers (the only LLM callers)
│   │   ├── memory.py             # SQLite + FTS5 persistence
│   │   └── prompt_templates.py
│   ├── core/
│   │   ├── orchestrator.py       # Pipeline coordinator (parallel support)
│   │   ├── llm.py                # OpenRouter client with streaming
│   │   ├── websocket_handler.py  # WebSocket broadcast manager
│   │   ├── execution_tracker.py  # Per-task log persistence
│   │   ├── result_aggregator.py  # Markdown report builder
│   │   ├── dag.py                # DAG execution engine
│   │   └── models.py             # Pydantic data models
│   ├── data/                     # Auto-created: DB, model stats (gitignored)
│   ├── config.py                 # All settings & data paths
│   ├── main.py                   # FastAPI app
│   ├── requirements.txt
│   ├── .env.example              # Copy to .env
│   └── .env                      # Your secrets (gitignored)
└── frontend/
    ├── src/
    │   ├── pages/
    │   │   ├── OutputPage.jsx    # Report viewer (react-markdown)
    │   │   └── TelemetryPage.jsx
    │   ├── components/dashboard/
    │   │   ├── AgentFlowGraph.jsx  # ReactFlow org chart (optimized)
    │   │   ├── LiveTracker.jsx
    │   │   └── Dashboard.jsx
    │   └── services/api.js        # Centralized REST + WebSocket client
    └── package.json
```
