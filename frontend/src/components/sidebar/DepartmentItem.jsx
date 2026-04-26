import React, { useState, useRef, useEffect } from 'react';
import EmployeeCard from './EmployeeCard';
import DepartmentPanel from './DepartmentPanel';

export default function DepartmentItem({ dept, isActive, activeEmployees = [] }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const contentRef = useRef(null);
  const [contentHeight, setContentHeight] = useState(0);

  /* Measure content for smooth animation */
  useEffect(() => {
    if (contentRef.current) {
      setContentHeight(contentRef.current.scrollHeight);
    }
  }, [dept.employees, isExpanded]);

  /* Auto-expand when department becomes active */
  useEffect(() => {
    if (isActive && !isExpanded) setIsExpanded(true);
  }, [isActive]);

  const employeeCount = dept.employees?.length || 0;
  
  // activeEmployees is an object dictionary keyed by handle: { "@senior_eng": { status: 'working', task: '...' } }
  const activeHandles = Object.keys(activeEmployees || {});
  const activeCount = dept.employees?.filter(emp => activeHandles.includes(emp.handle))?.length || 0;

  return (
    <div style={{
      borderRadius: 12,
      overflow: 'hidden',
      transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
      background: isActive ? `${dept.color}06` : 'transparent',
      border: `1px solid ${isExpanded ? `${dept.color}15` : 'transparent'}`,
      marginBottom: 2,
    }}>
      {/* ── Department Header (clickable) ── */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '10px 12px',
          border: 'none',
          background: 'none',
          cursor: 'pointer',
          textAlign: 'left',
          borderRadius: 12,
          transition: 'all 0.2s ease',
          position: 'relative',
        }}
        className="dept-header-hover"
      >
        {/* Department icon */}
        <div style={{
          width: 32, height: 32, borderRadius: 10, flexShrink: 0,
          background: isActive
            ? `linear-gradient(135deg, ${dept.color}25, ${dept.color}10)`
            : 'rgba(255,255,255,0.03)',
          border: `1px solid ${isActive ? `${dept.color}30` : 'rgba(255,255,255,0.06)'}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 16,
          transition: 'all 0.3s ease',
          boxShadow: isActive ? `0 0 12px ${dept.color}15` : 'none',
        }}>
          {dept.icon}
        </div>

        {/* Dept name + head info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <span style={{
              fontSize: 13, fontWeight: 700,
              color: isActive ? '#e2e8f0' : '#94a3b8',
              transition: 'color 0.3s',
            }}>
              {dept.key}
            </span>
            {activeCount > 0 && (
              <span style={{
                fontSize: 8, fontWeight: 900, letterSpacing: '0.1em',
                padding: '1px 5px', borderRadius: 4,
                background: `${dept.color}15`,
                color: dept.color,
                border: `1px solid ${dept.color}20`,
              }}>
                {activeCount} ACTIVE
              </span>
            )}
          </div>
          <div style={{
            fontSize: 10, color: '#475569', marginTop: 1,
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            {dept.head_name} · {dept.head_title}
          </div>
        </div>

        {/* Status dot */}
        <div style={{
          width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
          background: isActive ? '#22c55e' : '#374151',
          boxShadow: isActive ? '0 0 8px rgba(34,197,94,0.4)' : 'none',
          transition: 'all 0.3s',
        }} />

        {/* Chevron */}
        <svg
          width="14" height="14" viewBox="0 0 24 24" fill="none"
          stroke={isExpanded ? dept.color : '#4b5563'}
          strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
          style={{
            transition: 'transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), stroke 0.3s',
            transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
            flexShrink: 0,
          }}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {/* ── Expandable employee list ── */}
      <div
        style={{
          height: isExpanded ? contentHeight : 0,
          overflow: 'hidden',
          transition: 'height 0.35s cubic-bezier(0.16, 1, 0.3, 1)',
        }}
      >
        <div ref={contentRef} style={{ padding: '0 6px 8px 6px' }}>
          {/* Manager badges */}
          {dept.managers?.length > 0 && (
            <div style={{
              display: 'flex', flexWrap: 'wrap', gap: 4,
              padding: '4px 8px 8px 8px',
            }}>
              {dept.managers.map(mgr => (
                <span key={mgr.id} style={{
                  fontSize: 9, fontWeight: 700,
                  padding: '2px 7px', borderRadius: 5,
                  background: `${dept.color}10`,
                  color: dept.color,
                  border: `1px solid ${dept.color}15`,
                  display: 'inline-flex', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontWeight: 900 }}>⬡</span>
                  {mgr.name}
                  <span style={{
                    opacity: 0.6, fontFamily: 'var(--font-mono, monospace)',
                    fontSize: 8,
                  }}>
                    {mgr.handle}
                  </span>
                </span>
              ))}
            </div>
          )}

          {/* Department Panel Metrics */}
          <div style={{ padding: '0px 8px 6px 8px' }}>
            <DepartmentPanel dept={dept} activeEmployees={activeEmployees} />
          </div>

          {/* Employee cards */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {dept.employees.map(emp => (
              <EmployeeCard
                key={emp.id}
                employee={emp}
                deptColor={dept.color}
                activeState={activeEmployees[emp.handle] || null} // pass the state dict to EmployeeCard
              />
            ))}
          </div>

          {employeeCount === 0 && (
            <div style={{
              padding: '12px 8px', textAlign: 'center',
              fontSize: 10, color: '#374151', fontStyle: 'italic',
            }}>
              No employees registered
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
