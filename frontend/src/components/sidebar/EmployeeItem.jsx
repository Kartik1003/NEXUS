import React, { useState } from 'react';

/* ── Status badge config ─────────────────────────────────── */
const STATUS_CONFIG = {
  working: {
    label: 'WORKING',
    bg: 'rgba(34,197,94,0.12)',
    color: '#22c55e',
    border: 'rgba(34,197,94,0.25)',
    dot: '#22c55e',
    glow: '0 0 8px rgba(34,197,94,0.35)',
  },
  idle: {
    label: 'IDLE',
    bg: 'rgba(100,116,139,0.08)',
    color: '#64748b',
    border: 'rgba(100,116,139,0.15)',
    dot: '#475569',
    glow: 'none',
  },
};

export default function EmployeeItem({ employee, deptColor, activeState }) {
  const [modelPref, setModelPref] = useState(employee.assigned_model || 'auto');
  const isActive = activeState && activeState.status === 'working';
  const status = isActive ? 'working' : 'idle';
  const cfg = STATUS_CONFIG[status];

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

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 10,
        padding: '8px 10px 8px 12px',
        borderRadius: 10,
        background: isActive ? `${deptColor}08` : 'transparent',
        border: `1px solid ${isActive ? `${deptColor}20` : 'transparent'}`,
        transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        cursor: 'default',
        position: 'relative',
        overflow: 'hidden',
      }}
      className="employee-item-hover"
    >
      {/* Active left accent */}
      {isActive && (
        <div style={{
          position: 'absolute', left: 0, top: '20%', bottom: '20%', width: 2,
          background: deptColor, borderRadius: 1,
          boxShadow: `0 0 6px ${deptColor}60`,
        }} />
      )}

      {/* Avatar circle */}
      <div style={{
        width: 28, height: 28, borderRadius: 8, flexShrink: 0,
        background: isActive
          ? `linear-gradient(135deg, ${deptColor}30, ${deptColor}15)`
          : 'rgba(255,255,255,0.04)',
        border: `1px solid ${isActive ? `${deptColor}35` : 'rgba(255,255,255,0.06)'}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 11, fontWeight: 800, color: isActive ? deptColor : '#4b5563',
        transition: 'all 0.3s ease',
      }}>
        {employee.name.charAt(0)}
      </div>

      {/* Info column */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Name + handle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{
            fontSize: 12, fontWeight: 700,
            color: isActive ? '#e2e8f0' : '#94a3b8',
            transition: 'color 0.3s',
          }}>
            {employee.name}
          </span>
          <span style={{
            fontSize: 9, fontFamily: 'var(--font-mono, monospace)',
            color: isActive ? deptColor : '#475569',
            opacity: 0.8,
          }}>
            {employee.handle}
          </span>
        </div>

        {/* Role */}
        <div style={{
          fontSize: 10, color: '#64748b', marginTop: 1,
          lineHeight: 1.3,
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>
          {employee.role}
        </div>

        {/* Model Preference Dropdown */}
        <div style={{ marginTop: 6 }}>
          <select 
            value={modelPref} 
            onChange={handleModelChange}
            style={{
              background: 'rgba(15, 23, 42, 0.4)',
              border: `1px solid ${deptColor}30`,
              color: '#94a3b8',
              fontSize: 9,
              borderRadius: 4,
              padding: '2px 4px',
              cursor: 'pointer',
              outline: 'none',
              width: '100%',
              maxWidth: '140px',
              fontFamily: 'var(--font-mono, monospace)'
            }}
          >
            <option value="auto">Auto (Intelligent)</option>
            <option value="meta-llama/llama-3.3-70b-instruct">Llama 3.3 70B</option>
            <option value="meta-llama/llama-3.2-3b-instruct">Llama 3.2 3B</option>
            <option value="qwen/qwen3-coder">Qwen 3 Coder</option>
            <option value="qwen/qwen3-next-80b-a3b-instruct">Qwen 3 Next 80B</option>
            <option value="google/gemma-3-27b-it">Gemma 3 27B</option>
            <option value="google/gemma-3-4b-it">Gemma 3 4B</option>
            <option value="nousresearch/hermes-3-llama-3.1-405b">Hermes 3 (405B)</option>
            <option value="nvidia/nemotron-nano-9b-v2">Nemotron 9B</option>
            <option value="nvidia/nemotron-3-super-120b-a12b">Nemotron 120B</option>
          </select>
        </div>

        {/* Task badge (only if working) */}
        {isActive && activeState?.task && (
          <div style={{
            fontSize: 9, color: deptColor, marginTop: 4,
            padding: '2px 6px', borderRadius: 4,
            background: `${deptColor}10`,
            border: `1px solid ${deptColor}15`,
            display: 'inline-block',
            maxWidth: '100%',
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            fontFamily: 'var(--font-mono, monospace)',
          }}>
            ▸ {activeState.task}
          </div>
        )}
      </div>

      {/* Status dot + label */}
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'flex-end',
        gap: 2, flexShrink: 0,
      }}>
        <div style={{
          width: 7, height: 7, borderRadius: '50%',
          background: cfg.dot,
          boxShadow: cfg.glow,
          transition: 'all 0.3s',
        }} />
        <span style={{
          fontSize: 7, fontWeight: 900, letterSpacing: '0.1em',
          textTransform: 'uppercase', color: cfg.color,
        }}>
          {cfg.label}
        </span>
      </div>
    </div>
  );
}
