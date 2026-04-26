import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

/* ── Pipeline hierarchy (the ONLY agent levels) ── */
const PIPELINE_LEVELS = [
  { name: 'Executive',  icon: '🎯', color: '#40cef3' },
  { name: 'Department', icon: '🏢', color: '#ffa44c' },
  { name: 'Employee',   icon: '⚙️', color: '#10b981' },
];

export default function Sidebar({ activeView, onViewChange, connected, activeDepartments = [], activeAgents = [] }) {
  const navigate = useNavigate();
  const location = useLocation();

  const handleNav = (targetView, path) => {
    if (path) navigate(path);
    if (targetView) onViewChange(targetView);
  };

  return (
    <aside className="sidebar" style={{ background: 'var(--bg-secondary)', borderRight: '1px solid var(--border-subtle)', fontFamily: 'var(--font-body)' }}>
      {/* ── Logo ── */}
      <div className="sidebar-logo" style={{ borderBottom: '1px solid var(--border-subtle)', marginBottom: '24px' }}>
        <div className="logo-icon" style={{ background: 'rgba(208, 149, 255, 0.1)', border: '1px solid rgba(208, 149, 255, 0.2)' }}>
           <img src="/nexus-logo.png" alt="" style={{ width: '80%', height: '80%', opacity: 0.8 }} />
        </div>
        <div>
          <h1 style={{ fontFamily: 'var(--font-sans)', fontSize: '18px', fontWeight: '800', letterSpacing: '0.15em', background: 'var(--gradient-primary)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>NEXUS</h1>
          <div className="version" style={{ fontSize: '9px', fontWeight: '800', opacity: 0.4, letterSpacing: '0.1em' }}>OS REDLINE v4.0</div>
        </div>
      </div>

      {/* ── Workspace ── */}
      <div className="sidebar-section">
        <div className="sidebar-section-title" style={{ fontSize: '10px', fontWeight: '900', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.15em', marginBottom: '16px', paddingLeft: '8px' }}>Environment</div>
        <div
          className={`sidebar-item ${location.pathname === '/' || location.pathname === '/tracker' ? 'active' : ''}`}
          onClick={() => handleNav('pipeline', '/tracker')}
          style={{ borderRadius: 'var(--radius-sm)', transition: 'all 0.2s' }}
        >
          <span className="item-icon">⚡</span>
          <span style={{ fontSize: '13px', fontWeight: '600' }}>Live Tracker</span>
          <span style={{
            marginLeft: 'auto', fontSize: '8px', fontWeight: '900',
            letterSpacing: '0.1em', padding: '2px 6px', borderRadius: '4px',
            background: 'rgba(208, 149, 255, 0.1)', color: 'var(--color-ceo)',
            border: '1px solid rgba(208, 149, 255, 0.15)',
          }}>LIVE</span>
        </div>
        <div
          className={`sidebar-item ${location.pathname === '/hierarchy' ? 'active' : ''}`}
          onClick={() => handleNav(null, '/hierarchy')}
          style={{ borderRadius: 'var(--radius-sm)', transition: 'all 0.2s' }}
        >
          <span className="item-icon">🕸️</span>
          <span style={{ fontSize: '13px', fontWeight: '600' }}>Project Hierarchy</span>
        </div>
        <div
          className={`sidebar-item ${location.pathname.startsWith('/departments') ? 'active' : ''}`}
          onClick={() => handleNav(null, '/departments')}
          style={{ borderRadius: 'var(--radius-sm)', transition: 'all 0.2s' }}
        >
          <span className="item-icon">🏢</span>
          <span style={{ fontSize: '13px', fontWeight: '600' }}>Organization</span>
        </div>
        <div
          className={`sidebar-item ${activeView === 'history' && location.pathname === '/tracker' ? 'active' : ''}`}
          onClick={() => handleNav('history', '/tracker')}
          style={{ borderRadius: 'var(--radius-sm)', transition: 'all 0.2s' }}
        >
          <span className="item-icon">📜</span>
          <span style={{ fontSize: '13px', fontWeight: '600' }}>Archive</span>
        </div>
        <div
          className={`sidebar-item ${location.pathname === '/telemetry' ? 'active' : ''}`}
          onClick={() => handleNav(null, '/telemetry')}
          style={{ borderRadius: 'var(--radius-sm)', transition: 'all 0.2s' }}
        >
          <span className="item-icon">📡</span>
          <span style={{ fontSize: '13px', fontWeight: '600' }}>Telemetry</span>
        </div>
        <div
          className={`sidebar-item ${location.pathname === '/output' ? 'active' : ''}`}
          onClick={() => handleNav(null, '/output')}
          style={{ borderRadius: 'var(--radius-sm)', transition: 'all 0.2s' }}
        >
          <span className="item-icon">📝</span>
          <span style={{ fontSize: '13px', fontWeight: '600' }}>Execution Report</span>
        </div>
      </div>

      {/* ── Pipeline Visual ── */}
      <div className="sidebar-section" style={{ marginTop: 'auto', marginBottom: '24px' }}>
        <div className="sidebar-section-title" style={{ fontSize: '10px', fontWeight: '900', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.15em', marginBottom: '12px', paddingLeft: '8px' }}>Nexus Chain</div>
        <div style={{
          display: 'flex', flexDirection: 'column', gap: '8px', padding: '12px',
          background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)'
        }}>
          {PIPELINE_LEVELS.map((level, i) => (
            <div key={level.name} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '4px', height: '4px', borderRadius: '50%', background: level.color, boxShadow: `0 0 6px ${level.color}` }} />
              <span style={{ fontSize: '10px', fontWeight: '800', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{level.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Status ── */}
      <div className="sidebar-status" style={{ background: 'var(--bg-tertiary)', borderTop: '1px solid var(--border-subtle)', padding: '16px' }}>
        <div className="status-indicator" style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '11px', fontWeight: '700', color: 'var(--text-secondary)' }}>
          <span className={`status-dot ${connected ? '' : 'disconnected'}`} style={{ width: '8px', height: '8px', borderRadius: '50%', background: connected ? 'var(--color-success)' : 'var(--color-error)', boxShadow: connected ? '0 0 10px var(--color-success)' : 'none' }} />
          {connected ? 'LINK ESTABLISHED' : 'LINK SEVERED'}
        </div>
      </div>
    </aside>
  );
}
