import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * DepartmentCard — A high-fidelity, interactive card representing a functional department.
 * Provides quick stats and deep-link access to department management.
 */
export default function DepartmentCard({ dept, children }) {
  const navigate = useNavigate();
  const [isHovered, setIsHovered] = useState(false);

  const isActive = dept.activeEmployees > 0;

  return (
    <div 
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        background: 'var(--bg-card)',
        border: `1px solid ${isHovered ? 'rgba(208, 149, 255, 0.3)' : 'var(--border-default)'}`,
        borderRadius: 'var(--radius-lg)',
        padding: '28px',
        transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        transform: isHovered ? 'translateY(-4px)' : 'none',
        boxShadow: isHovered ? 'var(--shadow-glow)' : 'var(--shadow-sm)',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        position: 'relative',
        overflow: 'hidden'
      }}
    >
      {/* ── Background Glow ── */}
      {isActive && (
        <div style={{
          position: 'absolute',
          top: '-50px',
          right: '-50px',
          width: '150px',
          height: '150px',
          background: 'radial-gradient(circle, rgba(16, 185, 129, 0.08) 0%, transparent 70%)',
          pointerEvents: 'none'
        }} />
      )}

      {/* ── Icon & Title ── */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div style={{ 
          width: '48px', 
          height: '48px', 
          borderRadius: '14px', 
          background: 'var(--bg-tertiary)',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          fontSize: '24px',
          transition: 'all 0.3s'
        }}>
          {dept.icon || '🏢'}
        </div>
        <div style={{ 
          padding: '4px 10px', 
          borderRadius: '6px', 
          background: isActive ? 'rgba(16, 185, 129, 0.1)' : 'rgba(255, 255, 255, 0.05)',
          border: `1px solid ${isActive ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.1)'}`,
          fontSize: '9px',
          fontWeight: '900',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          color: isActive ? 'var(--color-success)' : 'var(--text-muted)'
        }}>
          {isActive ? 'Active' : 'Standby'}
        </div>
      </div>

      <div>
        <h3 style={{ 
          margin: 0, 
          fontFamily: 'var(--font-sans)', 
          fontSize: '20px', 
          fontWeight: '800', 
          color: 'var(--text-primary)',
          textTransform: 'capitalize'
        }}>
          {dept.key.replace(/_/g, ' ')}
        </h3>
        <p style={{ 
          margin: '6px 0 0 0', 
          fontSize: '13px', 
          color: 'var(--text-muted)',
          lineHeight: '1.5'
        }}>
          {dept.description || 'Specialized agent department for mission-critical orchestration.'}
        </p>
      </div>

      {/* ── Stats ── */}
      <div style={{ 
        display: 'flex', 
        gap: '24px', 
        paddingTop: '16px', 
        borderTop: '1px solid var(--border-subtle)' 
      }}>
        <div>
          <div style={{ fontSize: '9px', fontWeight: '900', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>Capacity</div>
          <div style={{ fontSize: '16px', fontWeight: '800', fontFamily: 'var(--font-mono)' }}>{dept.employees?.length || 0}</div>
        </div>
        <div>
          <div style={{ fontSize: '9px', fontWeight: '900', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>Running</div>
          <div style={{ fontSize: '16px', fontWeight: '800', fontFamily: 'var(--font-mono)', color: isActive ? 'var(--color-success)' : 'var(--text-secondary)' }}>{dept.activeEmployees}</div>
        </div>
      </div>

      {/* ── Personnel / Children Content ── */}
      {children && (
        <div onClick={(e) => e.stopPropagation()} style={{ marginTop: '4px' }}>
          {children}
        </div>
      )}

      {/* ── Footer ── */}
      <div 
        onClick={() => navigate(`/departments/${dept.key}`)}
        style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '8px', 
          fontSize: '11px', 
          fontWeight: '700', 
          color: isHovered ? 'var(--color-ceo)' : 'var(--text-secondary)',
          transition: 'color 0.2s',
          cursor: 'pointer',
          marginTop: 'auto'
        }}
      >
        Access Management <span>→</span>
      </div>
    </div>
  );
}

