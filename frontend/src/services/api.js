/**
 * WebSocket + REST API service for the Multi-Agent System
 * Fix #7: all REST endpoints now centralized here. No more direct fetch()
 * calls scattered across components.
 */

const WS_URL  = `ws://${window.location.hostname}:8001/ws`;
const API_URL = import.meta.env.VITE_API_URL ?? `http://${window.location.hostname}:8001/api`;

class AgentAPI {
  constructor() {
    this.ws             = null;
    this.listeners      = new Map();
    this.connected      = false;
    this.reconnectTimer = null;
    this.reconnectDelay = 2000;
  }

  // ─── WebSocket ────────────────────────────────────────────────────────────

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    try {
      this.ws = new WebSocket(WS_URL);

      this.ws.onopen = () => {
        this.connected      = true;
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

  // ─── Event System ─────────────────────────────────────────────────────────

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

  // ─── Internal fetch helper ────────────────────────────────────────────────

  async _fetch(path, options = {}) {
    try {
      const res = await fetch(`${API_URL}${path}`, options);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error(`[API] ${options.method || 'GET'} ${path} failed:`, e);
      return { error: e.message };
    }
  }

  // ─── Task Commands ────────────────────────────────────────────────────────

  /** Enqueue a new task and return { task_id, status } */
  async enqueueTask(taskDescription) {
    return this._fetch('/tasks/enqueue', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ task: taskDescription }),
    });
  }

  /** Stop/cancel a running task */
  async stopTask(taskId) {
    return this._fetch(`/tasks/${taskId}/stop`, { method: 'POST' });
  }

  /** Run a task synchronously (test/debug endpoint) */
  async runTask(taskDescription) {
    return this._fetch('/test', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ task: taskDescription }),
    });
  }

  // ─── Agent & System Status ────────────────────────────────────────────────

  async getHealth()       { return this._fetch('/health'); }
  async getAgentStatus()  { return this._fetch('/agents/status'); }
  async getAgentDirectory() { return this._fetch('/agents/directory'); }
  async getOrgChart()     { return this._fetch('/org-chart'); }
  async getQueueStatus()  { return this._fetch('/queue/status'); }

  /** Update an employee's preferred LLM model */
  async setAgentModel(handle, model) {
    return this._fetch('/agents/preferences', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ handle, model }),
    });
  }

  // ─── Task History & Logs ──────────────────────────────────────────────────

  async getHistory()         { return this._fetch('/history'); }
  async getLearnings()       { return this._fetch('/learnings'); }
  async getTaskLogs(taskId)  { return this._fetch(`/tracker/${taskId}`); }

  /** Files produced by a completed task */
  async getTaskFiles(taskId) { return this._fetch(`/tasks/${taskId}/files`); }

  /** Agent-to-agent chat messages for a completed task */
  async getTaskChat(taskId)  { return this._fetch(`/tasks/${taskId}/chat`); }

  // ─── Metrics ─────────────────────────────────────────────────────────────

  async getCost()            { return this._fetch('/cost'); }
  async getMessageStats()    { return this._fetch('/messages/stats'); }
  async getMessages(taskId)  { return this._fetch(`/messages/${taskId}`); }
}

export const api = new AgentAPI();
export default api;
