import React from 'react';
import AgentFlowGraph from '../components/dashboard/AgentFlowGraph';

export default function HierarchyPage({ logs = [], orgChart = null, activeAgents = {} }) {
  return (
    <div className="hierarchy-page" style={{ 
      padding: '24px', 
      minHeight: '100vh', 
      background: 'var(--bg-primary)', 
      color: 'var(--text-primary)',
      fontFamily: 'var(--font-body)',
      display: 'flex',
      flexDirection: 'column'
    }}>
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ 
          fontFamily: 'var(--font-sans)', 
          fontSize: '32px', 
          fontWeight: '800', 
          background: 'var(--gradient-primary)', 
          WebkitBackgroundClip: 'text', 
          WebkitTextFillColor: 'transparent', 
          margin: 0,
          letterSpacing: '0.02em'
        }}>
          Project Hierarchy
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '8px' }}>
          Real-time organizational architecture and agent presence monitoring.
        </p>
      </div>

      <div style={{ 
        flex: 1, 
        background: 'var(--bg-tertiary)', 
        border: '1px solid var(--border-subtle)', 
        borderRadius: 'var(--radius-lg)',
        overflow: 'hidden',
        position: 'relative',
        boxShadow: 'var(--shadow-lg)',
        height: '900px',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Header decoration */}
        <div style={{ 
          position: 'absolute', 
          top: 0, 
          left: 0, 
          right: 0, 
          padding: '12px 20px', 
          background: 'rgba(16, 19, 26, 0.8)', 
          backdropFilter: 'blur(8px)',
          borderBottom: '1px solid var(--border-subtle)',
          zIndex: 10,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div style={{ display: 'flex', gap: '16px', fontSize: '10px', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            <span style={{ color: '#d095ff' }}>● Strategy Planner</span>
            <span style={{ color: '#40cef3' }}>● Executive</span>
            <span style={{ color: '#ffa44c' }}>● Department</span>
            <span style={{ color: '#10b981' }}>● Employee</span>
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            System Presence: {orgChart ? (orgChart.departments.reduce((acc, d) => acc + (d.employees?.length || 0), 0) + (orgChart.executives?.length || 0)) : '...'} agents
          </div>
        </div>

        <AgentFlowGraph logs={logs} staticTree={orgChart} activeAgents={activeAgents} />
      </div>
    </div>
  );
}
