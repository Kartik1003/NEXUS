import React, { useState } from 'react';
import api from '../../services/api';

export default function DashboardTaskInput({ onLogsUpdate, setIsRunning, isRunning }) {
  const [task, setTask] = useState('');
  const [taskId, setTaskId] = useState(null);
  const [isRunningLocal, setIsRunningLocal] = useState(false);
  const wsRef = React.useRef(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!task.trim() || isRunningLocal) return;
    try {
      const result = await api.enqueueTask(task.trim());
      if (result.error) {
        alert(`Error: ${result.error}`);
        return;
      }
      if (result.task_id) {
        setTaskId(result.task_id);
        setIsRunning(true);
        setIsRunningLocal(true);
        // Open WebSocket for execution logs
        const wsUrl = `ws://${window.location.hostname}:8001/ws/execution/${result.task_id}`;
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;
        ws.onmessage = (event) => {
          const msg = JSON.parse(event.data);
          
          if (msg.type === 'execution_log') {
            // Propagate to parent immediately
            onLogsUpdate((prev) => [...prev, msg.data]);
          }
          
          // Check for completion in the data payload or the top-level event field
          if (msg.event === 'task_complete' || msg.data?.event === 'task_complete') {
            setIsRunning(false);
            setIsRunningLocal(false);
            ws.close();
          }
        };
        ws.onclose = () => {
          setIsRunning(false);
          setIsRunningLocal(false);
        };
      }
    } catch (e) {
      alert(`Error: ${e.message}`);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleStop = async () => {
    if (!taskId) return;
    try {
      await api.stopTask(taskId);
      setIsRunning(false);
      setIsRunningLocal(false);
      if (wsRef.current) {
        wsRef.current.close();
      }
    } catch (e) {
      console.error("Failed to stop task:", e);
    }
  };

  return (
    <div className="task-input-card card" style={{ padding: '24px', position: 'relative', overflow: 'hidden', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ 
        position: 'absolute', top: 0, left: 0, right: 0, height: '1px', 
        background: 'var(--gradient-primary)', opacity: 0.3 
      }} />
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{ 
          width: '32px', height: '32px', 
          background: 'rgba(208, 149, 255, 0.1)', 
          borderRadius: '6px', 
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '16px', border: '1px solid rgba(208, 149, 255, 0.2)'
        }}>⚡</div>
        <h2 style={{ fontSize: '13px', fontWeight: '800', color: 'white', letterSpacing: '0.1em', margin: 0 }}>COMMAND CENTER</h2>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <label style={{ fontSize: '10px', fontWeight: '900', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Task Objective</label>
        <textarea
          className="task-input"
          style={{ 
            width: '100%', 
            minHeight: '100px', 
            background: 'rgba(0,0,0,0.4)', 
            border: '1px solid var(--border-subtle)',
            color: 'white',
            padding: '16px',
            fontSize: '13px',
            fontFamily: 'var(--font-mono)',
            borderRadius: '8px',
            outline: 'none',
            resize: 'none',
            lineHeight: '1.6'
          }}
          placeholder="Describe your task objective in detail..."
          value={task}
          onChange={(e) => setTask(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isRunning}
        />
        
        <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
          Shift+Enter for newline
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px' }}>
        <div style={{ fontSize: '9px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          MODE: AUTONOMOUS_ORCHESTRATION
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {isRunningLocal && (
            <button
              onClick={handleStop}
              className="btn-stop"
              style={{ 
                padding: '10px 24px', 
                fontSize: '11px', 
                letterSpacing: '0.1em',
                background: 'rgba(239, 68, 68, 0.2)',
                color: '#ef4444',
                border: '1px solid rgba(239, 68, 68, 0.5)',
                borderRadius: '6px',
                cursor: 'pointer'
              }}
            >
              STOP / RESET
            </button>
          )}
          <button
            onClick={handleSubmit}
            disabled={!task.trim() || isRunningLocal}
            className="btn-solve"
            style={{ 
              padding: '10px 24px', 
              fontSize: '11px', 
              letterSpacing: '0.1em',
              opacity: (!task.trim() || isRunning) ? 0.3 : 1
            }}
          >
            {isRunningLocal ? 'PIPELINE_ACTIVE' : 'INITIALIZE_MISSION'}
          </button>
        </div>
      </div>
    </div>
  );
}
