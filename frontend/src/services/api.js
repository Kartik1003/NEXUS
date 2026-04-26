/**
 * WebSocket + REST API service for the Multi-Agent System
 */

const WS_URL = 'ws://localhost:8001/ws';
const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8001/api';

class AgentAPI {
  constructor() {
    this.ws = null;
    this.listeners = new Map();
    this.connected = false;
    this.reconnectTimer = null;
    this.reconnectDelay = 2000;
  }

  // ─── WebSocket ──────────────────────────────────

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    try {
      this.ws = new WebSocket(WS_URL);

      this.ws.onopen = () => {
        this.connected = true;
        this.reconnectDelay = 2000;
        this._emit('connection', { connected: true });
        console.log('[WS] Connected');
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          this._emit(msg.event, msg.data);
          this._emit('any', msg);
        } catch (e) {
          console.warn('[WS] Parse error:', e);
        }
      };

      this.ws.onclose = () => {
        this.connected = false;
        this._emit('connection', { connected: false });
        console.log('[WS] Disconnected, retrying...');
        this._scheduleReconnect();
      };

      this.ws.onerror = (err) => {
        console.warn('[WS] Error:', err);
      };
    } catch (e) {
      console.warn('[WS] Connect failed:', e);
      this._scheduleReconnect();
    }
  }

  _scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, this.reconnectDelay);
    this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 15000);
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.ws) this.ws.close();
    this.connected = false;
  }

  // ─── Event System ──────────────────────────────

  on(event, callback) {
    if (!this.listeners.has(event)) this.listeners.set(event, new Set());
    this.listeners.get(event).add(callback);
    return () => this.listeners.get(event)?.delete(callback);
  }

  _emit(event, data) {
    this.listeners.get(event)?.forEach(cb => {
      try { cb(data); } catch (e) { console.error('Listener error:', e); }
    });
  }

  // ─── Commands ──────────────────────────────────



  // ─── REST Endpoints ────────────────────────────



  async getHistory() {
    try {
      const res = await fetch(`${API_URL}/history`);
      return await res.json();
    } catch (e) {
      return { error: e.message };
    }
  }

  async getLearnings() {
    try {
      const res = await fetch(`${API_URL}/learnings`);
      return await res.json();
    } catch (e) {
      return { error: e.message };
    }
  }

  async getCost() {
    try {
      const res = await fetch(`${API_URL}/cost`);
      return await res.json();
    } catch (e) {
      return { error: e.message };
    }
  }

  async getHealth() {
    try {
      const res = await fetch(`${API_URL}/health`);
      return await res.json();
    } catch (e) {
      return { error: e.message };
    }
  }

  async getOrgChart() {
    try {
      const res = await fetch(`${API_URL}/org-chart`);
      return await res.json();
    } catch (e) {
      return { error: e.message };
    }
  }
  // ─── New Commands ─────────────────────────────────-

  // Enqueue a new task
  async enqueueTask(taskDescription) {
    try {
      const res = await fetch(`${API_URL}/tasks/enqueue`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: taskDescription })
      });
      return await res.json();
    } catch (e) {
      return { error: e.message };
    }
  }

  // Stop/reset a specific task
  async stopTask(taskId) {
    try {
      const res = await fetch(`${API_URL}/tasks/${taskId}/stop`, {
        method: 'POST'
      });
      return await res.json();
    } catch (e) {
      return { error: e.message };
    }
  }

  // Get logs for a specific task
  async getTaskLogs(taskId) {
    try {
      const res = await fetch(`${API_URL}/tracker/${taskId}`);
      return await res.json();
    } catch (e) {
      return { error: e.message };
    }
  }

  // Get overall agent status
  async getAgentStatus() {
    try {
      const res = await fetch(`${API_URL}/agents/status`);
      return await res.json();
    } catch (e) {
      return { error: e.message };
    }
  }

  // Update employee model
  async updateEmployeeModel(empId, model) {
    try {
      const res = await fetch(`${API_URL}/employees/${empId}/model`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model })
      });
      return await res.json();
    } catch (e) {
      return { error: e.message };
    }
  }
}

export const api = new AgentAPI();
export default api;
