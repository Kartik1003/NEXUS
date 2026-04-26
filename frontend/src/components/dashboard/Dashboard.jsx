import AgentFlowGraph from './AgentFlowGraph';

export default function Dashboard({ activeAgents, orgChart, isRunning }) {
  const totalAgents = orgChart ? (orgChart.departments?.reduce((acc, d) => acc + d.employees.length, 0) + (orgChart.executives?.length || 0)) : 0;
  const workingCount = Object.values(activeAgents).filter(a => a.status === 'working').length;

  return (
    <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '32px', height: '100%', overflowY: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h1 style={{ 
            margin: 0, fontSize: '32px', fontWeight: '800', fontFamily: 'var(--font-sans)',
            background: 'var(--gradient-primary)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'
          }}>
            System Dashboard
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '8px' }}>
            Operational overview and system health monitoring.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <div style={{ padding: '8px 16px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="status-dot" style={{ background: isRunning ? 'var(--color-success)' : 'var(--text-muted)' }} />
            <span style={{ fontSize: '11px', fontWeight: '800', color: isRunning ? 'var(--color-success)' : 'var(--text-muted)' }}>{isRunning ? 'PIPELINE_ACTIVE' : 'STANDBY'}</span>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '24px' }}>
        <div className="card" style={{ padding: '24px', borderLeft: '4px solid var(--color-ceo)', background: 'rgba(208, 149, 255, 0.03)' }}>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: '900', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Deployed Infrastructure</div>
          <div style={{ fontSize: '32px', fontWeight: '900', color: 'white', marginTop: '8px' }}>{totalAgents} Agents</div>
        </div>
        <div className="card" style={{ padding: '24px', borderLeft: '4px solid var(--color-exec)', background: 'rgba(64, 206, 243, 0.03)' }}>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: '900', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Operational Status</div>
          <div style={{ fontSize: '32px', fontWeight: '900', color: isRunning ? 'var(--color-success)' : 'white', marginTop: '8px' }}>
            {isRunning ? 'Running' : 'Ready'}
          </div>
        </div>
        <div className="card" style={{ padding: '24px', borderLeft: '4px solid var(--color-dept)', background: 'rgba(255, 164, 76, 0.03)' }}>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: '900', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Active Compute</div>
          <div style={{ fontSize: '32px', fontWeight: '900', color: workingCount > 0 ? 'var(--color-exec)' : 'white', marginTop: '8px' }}>
            {workingCount} Workers
          </div>
        </div>
      </div>
    </div>
  );
}
