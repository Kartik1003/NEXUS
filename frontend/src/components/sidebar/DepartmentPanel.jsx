import React, { useState, useEffect } from 'react';

export default function DepartmentPanel({ dept, activeEmployees = {} }) {
  const [avgExecutionTime, setAvgExecutionTime] = useState(0);

  const employeeCount = dept.employees?.length || 0;
  
  // Active employees mapping
  const activeHandles = Object.keys(activeEmployees || {});
  const activeDeptEmployees = dept.employees?.filter(emp => activeHandles.includes(emp.handle)) || [];
  const activeCount = activeDeptEmployees.length;

  // Since 1 employee normally runs 1 task in parallel within a department locally, tasks running == activeCount
  const tasksRunning = activeCount;

  // Calculate average execution time
  useEffect(() => {
    let interval;
    if (activeCount > 0) {
      interval = setInterval(() => {
        let totalElapsed = 0;
        let count = 0;
        
        activeDeptEmployees.forEach(emp => {
          const state = activeEmployees[emp.handle];
          if (state && state.start_time) {
            totalElapsed += Math.floor((Date.now() - state.start_time) / 1000);
            count++;
          }
        });

        if (count > 0) {
          setAvgExecutionTime(Math.floor(totalElapsed / count));
        }
      }, 1000);
    } else {
      setAvgExecutionTime(0);
    }
    
    return () => clearInterval(interval);
  }, [activeDeptEmployees, activeEmployees, activeCount]);

  const formatTime = (seconds) => {
    if (seconds === 0) return '--:--';
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div style={{
      background: 'rgba(15, 23, 42, 0.4)',
      borderRadius: 10,
      padding: '12px 14px',
      marginBottom: 12,
      border: `1px solid ${dept.color}20`,
      boxShadow: `inset 0 2px 12px rgba(0,0,0,0.2), 0 2px 8px rgba(0,0,0,0.1)`,
      display: 'grid',
      gridTemplateColumns: 'repeat(4, 1fr)',
      gap: 8,
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Decorative gradient overlay */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 2,
        background: `linear-gradient(90deg, transparent, ${dept.color}80, transparent)`,
      }} />

      {/* Stat: Total Employees */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontSize: 9, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
          Total
        </span>
        <span style={{ fontSize: 16, fontWeight: 800, color: '#cbd5e1', fontFamily: 'var(--font-mono, monospace)' }}>
          {employeeCount}
        </span>
      </div>

      {/* Stat: Active Employees */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontSize: 9, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
          Active
        </span>
        <span style={{ 
          fontSize: 16, fontWeight: 800, 
          color: activeCount > 0 ? dept.color : '#e2e8f0', 
          fontFamily: 'var(--font-mono, monospace)',
          textShadow: activeCount > 0 ? `0 0 10px ${dept.color}60` : 'none',
          transition: 'all 0.3s'
        }}>
          {activeCount}
        </span>
      </div>

      {/* Stat: Tasks Running */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontSize: 9, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
          Tasks
        </span>
        <span style={{ 
          fontSize: 16, fontWeight: 800, 
          color: tasksRunning > 0 ? '#f8fafc' : '#e2e8f0', 
          fontFamily: 'var(--font-mono, monospace)' 
        }}>
          {tasksRunning}
        </span>
      </div>

      {/* Stat: Avg Time */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontSize: 9, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
          Avg Time
        </span>
        <span style={{ 
          fontSize: 14, fontWeight: 700, 
          color: activeCount > 0 ? '#4ade80' : '#cbd5e1', 
          fontFamily: 'var(--font-mono, monospace)' 
        }}>
          {formatTime(avgExecutionTime)}
        </span>
      </div>
    </div>
  );
}
