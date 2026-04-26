import React, { useRef, useEffect } from 'react';

/* ── Agent hierarchy color palette ────────────────────────────── */
const AGENT_COLORS = {
  CEO: '#d095ff',
  Executive: '#40cef3',
  Department: '#ffa44c',
  Employee: '#10b981',
};

const STATUS_CONFIG = {
  started: { label: 'INITIATED', color: 'var(--text-muted)' },
  in_progress: { label: 'EXECUTING', color: 'var(--color-exec)', pulse: true },
  completed: { label: 'SUCCESS', color: 'var(--color-success)' },
  error: { label: 'CRITICAL', color: '#ff4c4c' },
};

export default function AgentStepCard({ log, isSelected, onClick }) {
  const { agent, agent_name, status, message, duration } = log;
  const agentColor = AGENT_COLORS[agent] || AGENT_COLORS.Employee;
  const statusCfg = STATUS_CONFIG[status] || STATUS_CONFIG.started;
  const cardRef = useRef(null);

  useEffect(() => {
    const el = cardRef.current;
    if (el) {
      el.style.opacity = '0';
      el.style.transform = 'translateY(10px)';
      requestAnimationFrame(() => {
        el.style.transition = 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)';
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
      });
    }
  }, []);

  return (
    <div
      ref={cardRef}
      onClick={onClick}
      className="card"
      style={{
        padding: '16px',
        cursor: 'pointer',
        borderLeft: `4px solid ${agentColor}`,
        background: isSelected ? 'rgba(255,255,255,0.05)' : 'rgba(255,255,255,0.02)',
        borderColor: isSelected ? agentColor : 'var(--border-subtle)',
        borderLeftColor: agentColor,
        transform: isSelected ? 'scale(1.02)' : 'none',
        boxShadow: isSelected ? `0 10px 30px -10px ${agentColor}40` : 'none',
        transition: 'all 0.2s ease-out',
        marginBottom: '12px'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontSize: '9px', fontWeight: '900', color: agentColor, letterSpacing: '0.15em', textTransform: 'uppercase' }}>
            {agent}
          </span>
          <span style={{ fontSize: '14px', fontWeight: '700', color: 'white' }}>
            {agent_name || agent}
          </span>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {duration && (
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{duration}</span>
          )}
          <span style={{ 
            fontSize: '9px', 
            fontWeight: '900', 
            color: statusCfg.color, 
            padding: '2px 8px', 
            borderRadius: '4px', 
            background: 'rgba(0,0,0,0.3)',
            border: `1px solid ${statusCfg.color}40`,
            animation: statusCfg.pulse ? 'pulse 2s infinite' : 'none'
          }}>
            {statusCfg.label}
          </span>
        </div>
      </div>

      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5', opacity: 0.8 }}>
        {message}
      </div>
    </div>
  );
}
