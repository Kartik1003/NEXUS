import React, { useState, useEffect, useRef } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './components/dashboard/Dashboard';
import LiveTracker from './components/dashboard/LiveTracker';
import DepartmentsPage from './pages/DepartmentsPage';
import DepartmentDetail from './pages/DepartmentDetail';
import HierarchyPage from './pages/HierarchyPage';
import TelemetryPage from './pages/TelemetryPage';
import OutputPage from './pages/OutputPage';

export default function App() {
  const [activeAgents, setActiveAgents] = useState({});
  const [executionLogs, setExecutionLogs] = useState([]);
  const [orgChart, setOrgChart] = useState({
    executives: [
      { name: "Strategos", handle: "@executive", role: "Executive Strategy Officer" },
      { name: "Axiom", handle: "@cto", role: "Chief Technology Officer" },
      { name: "Lyra", handle: "@cmo", role: "Chief Marketing Officer" },
      { name: "Atlas", handle: "@coo", role: "Chief Operating Officer" },
      { name: "Iron Man", handle: "@cfo", role: "Chief Financial Officer" },
      { name: "Marvel", handle: "@chro", role: "Chief Human Resources Officer" },
    ],
    departments: []
  });
  const [isRunning, setIsRunning] = useState(false);
  const [activeTaskId, setActiveTaskId] = useState(null);
  const [connected, setConnected] = useState(false);
  const [activeView, setActiveView] = useState('pipeline');
  const [taskHistory, setTaskHistory] = useState([]);
  
  const location = useLocation();
  const wsRef = useRef(null);

  // Sync activeView with route
  useEffect(() => {
    if (location.pathname === '/telemetry') setActiveView('telemetry');
    else if (location.pathname === '/output') setActiveView('output');
    else if (location.pathname === '/hierarchy') setActiveView('hierarchy');
    else if (location.pathname === '/departments') setActiveView('departments');
    else if (location.pathname === '/tracker') {
      setActiveView(prev => (prev === 'history' || prev === 'pipeline') ? prev : 'pipeline');
    }
    else if (location.pathname === '/') {
      setActiveView('dashboard');
    }
  }, [location.pathname]);

  // Centralized Org-Chart Loader
  useEffect(() => {
    let pollingInterval = null;
    const loadOrg = async () => {
      try {
        const res = await fetch('/api/org-chart');
        const data = await res.json();
        if (data && data.departments && data.departments.length > 0) {
          setOrgChart(data);
          if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
          }
        }
      } catch (e) {
        console.error("Org-Chart Sync Failure:", e);
      }
    };

    loadOrg(); 
    
    // Also fetch history on mount so Archive isn't empty on first click
    fetch('/api/history')
      .then(res => res.json())
      .then(data => setTaskHistory(data.tasks || []))
      .catch(err => console.error("Initial history fetch failed:", err));

    pollingInterval = setInterval(loadOrg, 5000);
    
    return () => { if (pollingInterval) clearInterval(pollingInterval); };
  }, []); // Mount only

  // Poll for active agents status — while running AND briefly after to catch completion
  useEffect(() => {
    if (!isRunning) {
      // Task just finished: do a final poll to get updated idle statuses
      const finalPoll = async () => {
        try {
          const res = await fetch('/api/agents/status');
          const polled = await res.json();
          if (polled && !polled.error) {
            setActiveAgents(polled); // full replace is fine when task is done
          }
        } catch (_) {}
      };
      finalPoll();
      // Clear all agents to idle after a short delay so the UI reverts
      const clearTimer = setTimeout(() => setActiveAgents({}), 3000);
      return () => clearTimeout(clearTimer);
    }
    const interval = setInterval(async () => {
      try {
        const res = await fetch('/api/agents/status');
        const polled = await res.json();
        if (polled && !polled.error) {
          // Merge: the WebSocket is the real-time source — don't downgrade an
          // agent already 'working' (set by WS) to 'idle' just because the
          // 3-second poll happened to catch it between log writes.
          setActiveAgents(prev => {
            const merged = { ...polled };
            for (const [name, info] of Object.entries(prev)) {
              if (info?.status === 'working' && merged[name]?.status !== 'working') {
                merged[name] = info; // keep WS-detected working state
              }
            }
            return merged;
          });
          setConnected(true);
        }
      } catch (e) {
        console.warn('Agent status poll failed:', e);
        setConnected(false);
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [isRunning]);

  // Fetch task history when switching to 'history' view
  useEffect(() => {
    if (activeView === 'history') {
      fetch('/api/history')
        .then(res => res.json())
        .then(data => setTaskHistory(data.tasks || []))
        .catch(err => console.error("Failed to fetch task history:", err));
    }
  }, [activeView]);

  const handleTaskSubmit = async (taskDescription) => {
    setIsRunning(true);
    setExecutionLogs([]);
    setActiveTaskId(null);
    
    try {
      const res = await fetch('/api/tasks/enqueue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: taskDescription }),
      });
      const data = await res.json();
      setActiveTaskId(data.task_id);
      connectToWebSocket(data.task_id);
    } catch (error) {
      console.error('Failed to enqueue task:', error);
      setIsRunning(false);
    }
  };

  const connectToWebSocket = (taskId) => {
    if (wsRef.current) wsRef.current.close();
    const secureStr = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${secureStr}//${window.location.host.split(':')[0]}:8001/ws/execution/${taskId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'execution_log') {
        const log = message.data;
        setExecutionLogs(prev => [...prev, log]);

        // Real-time hierarchy pulse logic: update active agents state based on logs
        if (log.agent_name && log.status) {
          setActiveAgents(prev => {
            const next = { ...prev };
            if (log.status === 'started' || log.status === 'in_progress') {
              next[log.agent_name] = { 
                status: 'working', 
                agent_level: log.agent,
                model: log.model 
              };
            } else if (log.status === 'completed' || log.status === 'failed') {
              // Mark agent as idle and remove from activeAgents after brief delay
              next[log.agent_name] = { status: 'idle' };
            }
            return next;
          });
        }

        // agent_chat and employee_output events are already captured in executionLogs
        // (they come through the same WebSocket channel as execution_log type messages).
        // OutputPage reads them directly from the logs prop. No separate state needed.
      }
    };

    ws.onclose = () => setIsRunning(false);
  };

  return (
    <div className="app-container" style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', background: 'var(--bg-primary)' }}>
      <Sidebar 
        activeView={activeView} 
        onViewChange={setActiveView} 
        connected={connected}
      />
      
      <main className="main-content" style={{ flex: 1, position: 'relative', overflowY: 'auto', height: '100vh' }}>
        <Routes>
          <Route path="/" element={
            <LiveTracker 
               logs={executionLogs} 
               setLogs={setExecutionLogs}
               history={taskHistory}
               isRunning={isRunning} 
               setIsRunning={setIsRunning}
               activeTaskId={activeTaskId}
               onSubmit={handleTaskSubmit}
               activeView={activeView}
               orgChart={orgChart}
               activeAgents={activeAgents}
            />
          } />
          <Route path="/tracker" element={
            <LiveTracker 
               logs={executionLogs} 
               setLogs={setExecutionLogs}
               history={taskHistory}
               isRunning={isRunning} 
               setIsRunning={setIsRunning}
               activeTaskId={activeTaskId}
               onSubmit={handleTaskSubmit}
               activeView={activeView}
               orgChart={orgChart}
               activeAgents={activeAgents}
            />
          } />
          <Route path="/departments" element={<DepartmentsPage activeAgents={activeAgents} orgChart={orgChart} />} />
          <Route path="/departments/:id" element={<DepartmentDetail activeAgents={activeAgents} orgChart={orgChart} />} />
          <Route path="/hierarchy" element={<HierarchyPage logs={executionLogs} orgChart={orgChart} activeAgents={activeAgents} />} />
          <Route path="/telemetry" element={<TelemetryPage logs={executionLogs} />} />
          <Route path="/output" element={<OutputPage logs={executionLogs} activeTaskId={activeTaskId} />} />
        </Routes>
      </main>
    </div>
  );
}
