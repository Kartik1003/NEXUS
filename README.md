# AgentForge: Self-Learning Multi-Agent Organization

AgentForge is a production-grade multi-agent AI framework designed to orchestrate complex tasks through a dynamically optimized, self-learning pipeline. It transforms a single LLM call into a collaborative organization of specialized agents (CEO, Engineering, Data, Marketing, Finance, QA).

## 🚀 Key Features

### 1. Self-Learning Pipeline Optimization
The system doesn't just run agents; it learns which sequence works best for specific task types.
- **UCB-based Selection**: Uses an 80/20 Exploit/Explore strategy to select the most efficient agent sequence.
- **Cost vs. Quality Balance**: Automatically chooses cheaper models for simple tasks and high-tier models for complex ones.
- **Dynamic Skipping**: Automatically skips QA and Evaluation steps if the primary agent's confidence score exceeds `0.85`, saving cost and time.

### 2. Parallel Multi-Agent Debate
For high-complexity tasks (Coding, Analysis, Planning), the CEO triggers a formal debate.
- **Multi-Model Synthesis**: Runs 3 distinct models in parallel to solve the same problem.
- **The Judge**: A dedicated evaluator model analyzes all candidate responses, selects a winner, and explains its reasoning.
- **Visibility**: Real-time logging of model participation and winning selection with specific icons (⚖️).

### 3. Integrated Feedback Loop
- **Task Classification**: Automatically maps tasks into departments (e.g., "coding" -> engineering, qa, evaluator).
- **Post-Execution Learning**: After every run, the system reflects on its performance and updates a persistent `pipeline_memory.json` to inform future runs.
- **Real-time Analytics**: Tracks tokens, USD cost, and agent contributions with a modern glassmorphism UI.

## 🛠️ Tech Stack
- **Backend**: FastAPI, Async Python, OpenRouter API.
- **Frontend**: React (Vite), CSS3 (Custom Design System).
- **Architecture**: DAG-based Execution Engine with Reinforcement Learning loops.

## 🚦 Getting Started

### Prerequisites
- Python 3.9+
- Node.js 18+
- OpenRouter API Key

### Installation

1. **Backend Setup**
   ```bash
   cd backend
   pip install -r requirements.txt
   # Set your OPENROUTER_API_KEY in .env
   python -m uvicorn main:app --reload
   ```

2. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## 📊 Monitoring
Navigate to `http://localhost:5173` to view the **Agent Intelligence Dashboard**:
- **Agent Pipeline**: Visual visualization of the dynamic DAG.
- **Cost Tracker**: Breakdown of spending by agent and model.
- **Self-Reflection**: AI-generated analysis of its own successes and failures.
- **Execution Log**: Real-time stream of agent thoughts and debate results.

---
*Built with ❤️ for Autonomous Intelligence.*
