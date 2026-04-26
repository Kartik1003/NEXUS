import React, { useEffect, useRef } from 'react';
import AgentStepCard from './AgentStepCard';

/* ── Connector dot color per-agent ────────────────────────────── */
const DOT_COLORS = {
  CEO: '#d095ff',
  Executive: '#40cef3',
  Department: '#ffa44c',
  Employee: '#10b981',
};

export default function Timeline({ logs, selectedLogIndex, onSelectLog }) {
  const containerRef = useRef(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [logs]);

  if (!logs || logs.length === 0) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', opacity: 0.5 }}>
          <div style={{ fontSize: '40px' }}>⏳</div>
          <div style={{ textAlign: 'center' }}>
            <p style={{ fontSize: '14px', fontWeight: '800', margin: 0 }}>AWAITING PIPELINE</p>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Initialize orchestration to view trace</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      style={{ height: '100%', overflowY: 'auto' }}
    >
      <div style={{ position: 'relative', marginLeft: '32px', paddingLeft: '32px', paddingTop: '16px', paddingBottom: '32px' }}>
        {/* ── Vertical timeline wire ── */}
        <div style={{ 
          position: 'absolute', left: 0, top: 0, bottom: 0, width: '2px', 
          background: 'linear-gradient(to bottom, #d095ff 0%, #40cef3 50%, #10b981 100%)', 
          opacity: 0.2, borderRadius: '4px' 
        }} />

        {logs.map((log, index) => {
          const color = DOT_COLORS[log.agent] || '#a9abb3';
          const isLatest = index === logs.length - 1;

          return (
            <div key={index} style={{ position: 'relative', marginBottom: '16px' }}>
              {/* ── DOT ── */}
              <div
                style={{
                  position: 'absolute', left: '-37px', top: '24px', width: '10px', height: '10px', 
                  borderRadius: '50%', background: color, zIndex: 10,
                  boxShadow: `0 0 10px ${color}`,
                  transform: isLatest ? 'scale(1.3)' : 'scale(1)',
                  transition: 'transform 0.3s ease'
                }}
              />

              <AgentStepCard
                log={log}
                isSelected={selectedLogIndex === index}
                onClick={() => onSelectLog(index)}
              />
            </div>
          );
        })}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
