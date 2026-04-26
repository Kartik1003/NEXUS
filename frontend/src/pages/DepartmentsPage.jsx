import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DepartmentCard from '../components/DepartmentCard';
import '../index.css';

export default function DepartmentsPage({ activeAgents = {}, orgChart = null }) {
  const navigate = useNavigate();
  const loading = !orgChart;
  const orgData = orgChart;
  const [expandedDept, setExpandedDept] = useState(null);

  const agentKeys = Object.keys(activeAgents).map(k => k.toLowerCase());

  return (
    <div className="departments-page" style={{ padding: '24px', minHeight: '100vh', background: 'var(--bg-primary)', color: 'var(--text-primary)' }}>
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontFamily: 'var(--font-sans)', fontSize: '28px', fontWeight: '800', background: 'var(--gradient-primary)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', marginBottom: '8px', letterSpacing: '0.05em' }}>
          Organization overview
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '15px' }}>
          Explore your organization's departmental structure and access specific team controls.
        </p>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '300px' }}>
          <div style={{ width: 40, height: 40, borderRadius: '50%', border: '3px solid var(--border-default)', borderTopColor: 'var(--color-ceo)', animation: 'spin 1s linear infinite' }} />
        </div>
      ) : (
        <>
          {/* Global Leadership Section */}
          <div style={{ marginBottom: '40px' }}>
            <h2 style={{ fontSize: '12px', fontWeight: '900', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.15em', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ color: '#40cef3' }}>◈</span> Executive Leadership
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
              {(orgData?.executives || []).map((exec, idx) => {
                const handleKey = exec.handle?.replace('@', '').toLowerCase() || '';
                const isActive = agentKeys.some(k => k.includes(handleKey) || k.includes(exec.name?.toLowerCase()));
                return (
                  <div key={idx} style={{ padding: '20px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'rgba(64, 206, 243, 0.1)', display: 'flex', justifyContent: 'center', alignItems: 'center', fontSize: '24px', border: '1px solid rgba(64, 206, 243, 0.2)' }}>🎯</div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '16px', fontWeight: '800', color: '#40cef3', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{exec.name}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '700' }}>{exec.role || exec.handle}</div>
                    </div>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: isActive ? 'var(--color-success)' : 'rgba(255,255,255,0.1)', flexShrink: 0 }} />
                  </div>
                );
              })}
            </div>
          </div>
 
          <h2 style={{ fontSize: '12px', fontWeight: '900', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.15em', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: '#ffa44c' }}>◈</span> Departments Directory
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: '32px', alignItems: 'start' }}>
            {orgData?.departments?.map((dept, idx) => {
              const deptEmployees = dept.employees || [];
              const isExpanded = expandedDept === idx;
              
              return (
                <div key={idx} style={{ 
                  gridRow: isExpanded ? 'span 2' : 'auto',
                  transition: 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)'
                }}>
                  <div onClick={() => setExpandedDept(isExpanded ? null : idx)} style={{ cursor: 'pointer' }}>
                    <DepartmentCard 
                      dept={{
                        ...dept, 
                        activeEmployees: deptEmployees.filter(e => activeAgents[e.handle]?.status === 'working').length,
                        totalEmployees: deptEmployees.length,
                      }} 
                    >
                      {/* Expandable Employee List passed as Child */}
                      {isExpanded && (
                        <div style={{ 
                          padding: '16px',
                          background: 'rgba(0, 0, 0, 0.2)',
                          borderRadius: '12px',
                          border: '1px solid rgba(255, 255, 255, 0.05)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '10px',
                          marginTop: '4px',
                          animation: 'slideDown 0.3s ease-out'
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <h4 style={{ fontSize: '10px', fontWeight: '900', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                              Personnel assigned
                            </h4>
                            <div style={{ fontSize: '9px', color: 'var(--color-ceo)', fontWeight: '800' }}>{deptEmployees.length} AGENTS</div>
                          </div>
                          
                          {deptEmployees.length === 0 ? (
                            <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic', textAlign: 'center', padding: '10px' }}>No employees assigned.</div>
                          ) : (
                            deptEmployees.map((emp, eIdx) => {
                              const status = activeAgents[emp.handle] || { status: 'idle' };
                              const isWorking = status.status === 'working';
                              
                              return (
                                <div key={eIdx} style={{ 
                                  padding: '10px 12px', 
                                  background: 'var(--bg-tertiary)', 
                                  borderRadius: '8px', 
                                  border: '1px solid var(--border-subtle)',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'space-between',
                                  gap: '8px'
                                }}>
                                    <div>
                                      <div style={{ fontSize: '12px', fontWeight: '800', color: 'var(--text-primary)' }}>{emp.name}</div>
                                      <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: '600' }}>{emp.role}</div>
                                    </div>
                                    <div style={{ 
                                      padding: '2px 6px', 
                                      borderRadius: '4px', 
                                      background: isWorking ? 'rgba(16, 185, 129, 0.1)' : 'rgba(255,255,255,0.03)',
                                      fontSize: '8px',
                                      fontWeight: '900',
                                      color: isWorking ? 'var(--color-success)' : 'var(--text-muted)'
                                    }}>
                                      {isWorking ? 'WORKING' : 'IDLE'}
                                    </div>
                                </div>
                              );
                            })
                          )}
                          
                          <button 
                             onClick={(e) => { e.stopPropagation(); navigate(`/departments/${dept.key}`); }}
                             style={{ 
                               marginTop: '6px', 
                               padding: '8px', 
                               background: 'var(--bg-accent)', 
                               border: 'none', 
                               borderRadius: '6px', 
                               color: 'white', 
                               fontSize: '10px', 
                               fontWeight: '900', 
                               cursor: 'pointer', 
                               transition: 'all 0.2s',
                               textTransform: 'uppercase'
                             }}
                             onMouseOver={e => e.currentTarget.style.filter = 'brightness(1.2)'}
                             onMouseOut={e => e.currentTarget.style.filter = 'none'}
                          >
                             Manage Team Details
                          </button>
                        </div>
                      )}
                    </DepartmentCard>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
      
      <style>{`
        @keyframes slideDown {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
