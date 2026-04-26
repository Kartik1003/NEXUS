import React, { useState, useEffect } from 'react';

/* ── Status badge config ─────────────────────────────────── */
const STATUS_CONFIG = {
  working: {
    label: 'WORKING',
    bg: 'rgba(34,197,94,0.15)',
    color: '#4ade80', // Brighter green for dark mode
    border: 'rgba(34,197,94,0.3)',
    dot: '#4ade80',
    glow: '0 0 12px rgba(34,197,94,0.5)',
  },
  idle: {
    label: 'IDLE',
    bg: 'rgba(100,116,139,0.1)',
    color: '#94a3b8',
    border: 'rgba(100,116,139,0.2)',
    dot: '#64748b',
    glow: 'none',
  },
};

export default function EmployeeCard({ employee, deptColor, activeState }) {
  const [modelPref, setModelPref] = useState(employee.assigned_model || 'auto');
  const [elapsed, setElapsed] = useState(0);

  const isActive = activeState && activeState.status === 'working';
  const status = isActive ? 'working' : 'idle';
  const cfg = STATUS_CONFIG[status];

  // Execution Timer
  useEffect(() => {
    let interval;
    if (isActive && activeState?.start_time) {
      interval = setInterval(() => {
        setElapsed(Math.floor((Date.now() - activeState.start_time) / 1000));
      }, 1000);
    } else {
      setElapsed(0);
    }
    return () => clearInterval(interval);
  }, [isActive, activeState?.start_time]);

  const handleModelChange = async (e) => {
    const newModel = e.target.value;
    setModelPref(newModel);
    try {
      await fetch('/api/agents/preferences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ handle: employee.handle, model: newModel })
      });
    } catch (err) {
      console.error("Failed to save preference", err);
    }
  };

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        padding: '14px',
        borderRadius: 12,
        // Premium glassmorphism effect
        background: isActive 
          ? `linear-gradient(145deg, rgba(30,41,59,0.7), rgba(15,23,42,0.9))` 
          : 'rgba(30,41,59,0.4)',
        backdropFilter: 'blur(10px)',
        border: `1px solid ${isActive ? `${deptColor}50` : 'rgba(255,255,255,0.05)'}`,
        boxShadow: isActive ? `0 8px 32px -4px ${deptColor}20` : '0 4px 12px rgba(0,0,0,0.1)',
        transition: 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
        cursor: 'default',
        position: 'relative',
        overflow: 'hidden',
        marginBottom: 8,
      }}
    >
      {/* Active left accent glow line */}
      {isActive && (
        <div style={{
          position: 'absolute', left: 0, top: 0, bottom: 0, width: 3,
          background: `linear-gradient(to bottom, transparent, ${deptColor}, transparent)`,
          boxShadow: `0 0 10px ${deptColor}80`,
        }} />
      )}

      {/* Top Header Row (Avatar, Name, Status) */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {/* Avatar circle */}
        <div style={{
          width: 36, height: 36, borderRadius: 10, flexShrink: 0,
          background: isActive
            ? `linear-gradient(135deg, ${deptColor}40, ${deptColor}15)`
            : 'rgba(255,255,255,0.03)',
          border: `1px solid ${isActive ? `${deptColor}60` : 'rgba(255,255,255,0.08)'}`,
          boxShadow: isActive ? `inset 0 0 12px ${deptColor}20, 0 0 12px ${deptColor}40` : 'none',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 14, fontWeight: 800, color: isActive ? '#fff' : '#64748b',
          transition: 'all 0.4s ease',
          zIndex: 1,
        }}>
          {employee.name.charAt(0)}
        </div>

        {/* Identity block */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <span style={{
              fontSize: 14, fontWeight: 600,
              color: isActive ? '#f8fafc' : '#cbd5e1',
              transition: 'color 0.3s',
            }}>
              {employee.name}
            </span>
            <span style={{
              fontSize: 10, fontFamily: 'var(--font-mono, monospace)',
              color: isActive ? deptColor : '#64748b',
              opacity: 0.9,
            }}>
              {employee.handle}
            </span>
          </div>
          <div style={{
            fontSize: 11, color: '#94a3b8', marginTop: 2,
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            {employee.role}
          </div>
        </div>

        {/* Status Badge */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          background: cfg.bg, border: `1px solid ${cfg.border}`,
          padding: '4px 8px', borderRadius: 20, flexShrink: 0,
        }}>
          <div style={{
            width: 6, height: 6, borderRadius: '50%',
            background: cfg.dot,
            boxShadow: cfg.glow,
            transition: 'all 0.3s',
          }} />
          <span style={{
            fontSize: 9, fontWeight: 800, letterSpacing: '0.05em',
            color: cfg.color, textTransform: 'uppercase',
          }}>
            {cfg.label}
          </span>
        </div>
      </div>

      {/* Middle Content: Task & Timer (Visible when working) */}
      <div style={{ 
        display: 'grid', 
        gridTemplateRows: isActive ? '1fr' : '0fr',
        transition: 'grid-template-rows 0.4s ease',
      }}>
        <div style={{ overflow: 'hidden' }}>
          {activeState?.task && (
            <div style={{ 
              marginTop: 4, padding: '8px 10px', 
              background: 'rgba(0,0,0,0.2)', borderRadius: 6,
              borderLeft: `2px solid ${deptColor}`,
              display: 'flex', flexDirection: 'column', gap: 6
            }}>
              <div style={{
                fontSize: 11, color: '#e2e8f0',
                display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
                overflow: 'hidden', lineHeight: 1.4, fontFamily: 'var(--font-mono, monospace)'
              }}>
                <span style={{ color: deptColor, marginRight: 6 }}>▸</span>
                {activeState.task}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#94a3b8', fontSize: 10 }}>
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <path d="M12 6v6l4 2"></path>
                </svg>
                <span>Dur: {formatTime(elapsed)}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer: Model Dropdown */}
      <div style={{
        display: 'flex', flexDirection: 'column', gap: 4,
        marginTop: 4, paddingTop: isActive ? 10 : 4,
        borderTop: isActive ? '1px solid rgba(255,255,255,0.05)' : '1px solid transparent',
        transition: 'all 0.4s ease'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 9, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Model Selection
          </span>
        </div>
        <select 
          value={modelPref} 
          onChange={handleModelChange}
          style={{
            background: 'rgba(15, 23, 42, 0.6)',
            border: `1px solid ${deptColor}40`,
            color: '#f8fafc',
            fontSize: 11,
            borderRadius: 6,
            padding: '6px 8px',
            cursor: 'pointer',
            outline: 'none',
            width: '100%',
            fontFamily: 'var(--font-mono, monospace)',
            appearance: 'none',
            boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.2)',
            transition: 'border-color 0.2s',
          }}
          onFocus={(e) => e.target.style.borderColor = deptColor}
          onBlur={(e) => e.target.style.borderColor = `${deptColor}40`}
        >
          <option value="auto">⚡ Auto (Intelligent Default)</option>
          <option disabled>──────────</option>
          <option value="meta-llama/llama-3.3-70b-instruct">Llama 3.3 70B</option>
          <option value="meta-llama/llama-3.2-3b-instruct">Llama 3.2 3B</option>
          <option value="qwen/qwen3-coder">Qwen 3 Coder</option>
          <option value="google/gemma-3-27b-it">Gemma 3 27B</option>
          <option value="google/gemma-3-4b-it">Gemma 3 4B</option>
          <option value="nousresearch/hermes-3-llama-3.1-405b">Hermes 3 (405B)</option>
          <option value="qwen/qwen3-next-80b-a3b-instruct">Qwen Next 80B</option>
          <option value="nvidia/nemotron-nano-9b-v2">Nemotron 9B</option>
        </select>
      </div>
    </div>
  );
}
