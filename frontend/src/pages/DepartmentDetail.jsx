import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import EmployeeRow from '../components/EmployeeRow';
import '../index.css';

export default function DepartmentDetail({ activeAgents = {} }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [dept, setDept] = useState(null);
  const [loading, setLoading] = useState(true);
  const [disabledEmployees, setDisabledEmployees] = useState(new Set());

  useEffect(() => {
    fetchOrg();
  }, [id]);

  const fetchOrg = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/org-chart');
      const data = await res.json();
      const targetDept = data.departments?.find(d => d.key.toLowerCase() === id.toLowerCase());
      setDept(targetDept);
      setLoading(false);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  const handleChangeLLM = async (handle, newModel) => {
    try {
      await fetch('/api/agents/preferences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ handle, model: newModel })
      });
      fetchOrg();
    } catch(err) {
      console.error('Failed to change LLM', err);
    }
  };

  const toggleEmployee = (handle) => {
    setDisabledEmployees(prev => {
      const next = new Set(prev);
      if (next.has(handle)) next.delete(handle);
      else next.add(handle);
      return next;
    });
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: 'var(--bg-app)' }}>
        <div style={{ width: 40, height: 40, borderRadius: '50%', border: '3px solid #1e293b', borderTopColor: '#6e56ff', animation: 'spin 1s linear infinite' }} />
      </div>
    );
  }

  if (!dept) {
    return (
      <div style={{ padding: '40px', color: 'var(--text-primary)', background: 'var(--bg-app)', height: '100vh' }}>
        <h2>Department not found</h2>
        <button onClick={() => navigate('/departments')} className="btn btn-secondary">Go Back</button>
      </div>
    );
  }

  // Derived metrics
  // Derived metrics
  const activeCount = dept.employees?.filter(e => {
    const status = activeAgents[e.handle] || activeAgents[e.handle.toLowerCase()];
    return status?.status === 'working';
  }).length || 0;
  
  const isDeptActive = activeCount > 0;

  return (
    <div className="departments-page" style={{ padding: '24px', minHeight: '100vh', background: 'var(--bg-primary)', color: 'var(--text-primary)', fontFamily: 'var(--font-body)' }}>
      {/* ── Header ── */}
      <div style={{ marginBottom: '40px', display: 'flex', alignItems: 'center', gap: '24px' }}>
        <div 
          onClick={() => navigate('/departments')}
          style={{ width: '42px', height: '42px', borderRadius: '50%', background: 'var(--bg-tertiary)', display: 'flex', justifyContent: 'center', alignItems: 'center', cursor: 'pointer', border: '1px solid var(--border-subtle)', transition: 'all 0.2s', fontSize: '18px', color: 'var(--text-secondary)' }}
          onMouseOver={e => {
            e.currentTarget.style.background = 'var(--bg-secondary)';
            e.currentTarget.style.borderColor = 'var(--border-active)';
            e.currentTarget.style.color = 'var(--color-ceo)';
          }}
          onMouseOut={e => {
            e.currentTarget.style.background = 'var(--bg-tertiary)';
            e.currentTarget.style.borderColor = 'var(--border-subtle)';
            e.currentTarget.style.color = 'var(--text-secondary)';
          }}
        >
          ←
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{ 
              width: '56px', 
              height: '56px', 
              borderRadius: 'var(--radius-lg)', 
              background: 'var(--bg-tertiary)', 
              display: 'flex', 
              justifyContent: 'center', 
              alignItems: 'center', 
              fontSize: '28px', 
              border: `1px solid ${isDeptActive ? 'var(--border-active)' : 'var(--border-subtle)'}`, 
              boxShadow: isDeptActive ? 'var(--shadow-glow)' : 'none',
              filter: isDeptActive ? `drop-shadow(0 0 10px ${dept.color}44)` : 'none'
            }}>
              {dept.icon || '🏢'}
            </div>
            <div>
              <h1 style={{ fontFamily: 'var(--font-sans)', fontSize: '32px', fontWeight: '800', background: 'var(--gradient-primary)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', margin: 0, letterSpacing: '0.02em' }}>
                {dept.key}
              </h1>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '6px' }}>
                <span className={`status-dot ${isDeptActive ? 'pulse-success' : ''}`} style={{ width: 6, height: 6, borderRadius: '50%', background: isDeptActive ? 'var(--color-success)' : 'var(--text-muted)', boxShadow: isDeptActive ? '0 0 10px var(--color-success)' : 'none' }} />
                <span style={{ fontSize: '11px', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.1em', color: isDeptActive ? 'var(--color-success)' : 'var(--text-muted)' }}>{isDeptActive ? 'Operational' : 'Standby'} Deployment</span>
              </div>
            </div>
          </div>
        </div>

        {/* Summary Stats */}
         <div style={{ display: 'flex', gap: '12px' }}>
           <div style={{ padding: '14px 24px', background: 'var(--bg-card)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-md)', backdropFilter: 'blur(12px)' }}>
             <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '800', letterSpacing: '0.1em', marginBottom: '6px' }}>Team Capacity</div>
             <div style={{ fontSize: '20px', fontWeight: '700', fontFamily: 'var(--font-mono)' }}>{dept.employees?.length || 0}</div>
           </div>
           <div style={{ padding: '14px 24px', background: 'var(--bg-card)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-md)', backdropFilter: 'blur(12px)' }}>
             <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '800', letterSpacing: '0.1em', marginBottom: '6px' }}>Active Agents</div>
             <div style={{ fontSize: '20px', fontWeight: '700', fontFamily: 'var(--font-mono)', color: isDeptActive ? 'var(--color-success)' : 'var(--text-secondary)' }}>{activeCount}</div>
           </div>
           <div 
             onClick={fetchOrg}
             style={{ padding: '14px', background: 'var(--bg-card)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: 'var(--text-muted)', transition: 'all 0.2s' }}
             onMouseOver={e => e.currentTarget.style.color = 'var(--color-ceo)'}
             onMouseOut={e => e.currentTarget.style.color = 'var(--text-muted)'}
           >
             🔄
           </div>
         </div>
       </div>
 
       {/* ── Employees Section ── */}
       <div className="section-container" style={{ position: 'relative' }}>
         <h2 style={{ fontFamily: 'var(--font-sans)', fontSize: '14px', fontWeight: '800', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.15em' }}>
           <span style={{ color: 'var(--color-ceo)', filter: 'drop-shadow(0 0 8px rgba(208, 149, 255, 0.4))' }}>⚡</span> Department Manifest
         </h2>
 
         <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* ── Table Header ── */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(180px, 1.2fr) 1.1fr 1.8fr 1.2fr 1.4fr 1fr 100px',
              padding: '0 24px 12px 24px',
              fontSize: '10px',
              fontWeight: '900',
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.15em',
              borderBottom: '1px solid rgba(255, 255, 255, 0.03)'
            }}>
              <div>Specialist</div>
              <div>Role</div>
              <div>Current Workflow</div>
              <div>Active Engine</div>
              <div>LLM Preference</div>
              <div>Status</div>
              <div style={{ textAlign: 'right' }}>Controls</div>
            </div>

           {dept.employees?.map((emp, idx) => {
             const empKey = Object.keys(activeAgents).find(k => k.toLowerCase().includes(emp.role.toLowerCase()) || k.toLowerCase().includes(emp.name.toLowerCase()));
             const isDisabled = disabledEmployees.has(emp.handle);

            return (
              <EmployeeRow 
                key={idx}
                emp={emp}
                isEmpActiveStr={empKey}
                activeAgents={activeAgents}
                isDisabled={isDisabled}
                onToggle={toggleEmployee}
                onChangeLLM={handleChangeLLM}
              />
            );
          })}
        </div>
        {dept.employees?.length === 0 && (
          <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)', background: 'var(--bg-tertiary)', border: '1px dashed var(--border-default)', borderRadius: 'var(--radius-lg)' }}>
            <div style={{ fontSize: '32px', marginBottom: '16px', opacity: 0.3 }}>📭</div>
            <div style={{ fontFamily: 'var(--font-sans)', fontWeight: '700', fontSize: '16px' }}>No employees found in this department.</div>
            <div style={{ fontSize: '13px', marginTop: '6px' }}>Deployment manifest is currently empty.</div>
          </div>
        )}
      </div>

    </div>
  );
}
