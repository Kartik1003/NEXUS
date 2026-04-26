import React, { useState, useEffect, useRef } from 'react';
import DashboardTaskInput from './DashboardTaskInput';
import Timeline from './Timeline';
import AgentFlowGraph from './AgentFlowGraph';
import PlaybackControls from './PlaybackControls';

/* ═══════════════════════════════════════════════════════════════
   EXECUTION DASHBOARD — Integrated Operational View
   ─────────────────────────────────────────────────────────────
   This component is rendered inside App.jsx's .main-content.
   It should not define its own sidebar margin or full-page fixed sizing.
   ═══════════════════════════════════════════════════════════════ */

export default function LiveTracker({ logs = [], setLogs, history = [], isRunning, setIsRunning, activeTaskId, onSubmit, activeView, orgChart, activeAgents }) {
  const [selectedLogIndex, setSelectedLogIndex] = useState(null);

  /* Playback state */
  const [playbackIndex, setPlaybackIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const isLiveTracking = useRef(true);
  const [trackerSubView, setTrackerSubView] = useState('timeline'); // 'timeline' or 'flow'

  // Sync playback index with logs when live tracking
  useEffect(() => {
    if (isLiveTracking.current) {
      setPlaybackIndex(logs.length);
    }
  }, [logs.length]);

  const handleManualPlaybackChange = (newIndex) => {
    setPlaybackIndex(newIndex);
    isLiveTracking.current = newIndex >= logs.length;
  };

  /* Playback engine */
  useEffect(() => {
    let intervalId;
    if (isPlaying && playbackIndex < logs.length) {
      const ms = 1000 / playbackSpeed;
      intervalId = setInterval(() => {
        setPlaybackIndex((prev) => {
          const next = prev + 1;
          if (next >= logs.length) {
            setIsPlaying(false);
            isLiveTracking.current = true;
            return logs.length;
          }
          return next;
        });
      }, ms);
    }
    return () => clearInterval(intervalId);
  }, [isPlaying, playbackIndex, logs.length, playbackSpeed]);

  const visibleLogs = logs.slice(0, playbackIndex);

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      minHeight: '100%',
      width: '100%',
      gap: '24px',
      paddingBottom: '40px'
    }}>
      {/* ── HEADER ── */}
      <div style={{ 
        flex: '0 0 auto', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        paddingBottom: '16px',
        borderBottom: '1px solid var(--border-subtle)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ 
            width: '32px', height: '32px', 
            background: 'var(--gradient-primary)', 
            borderRadius: '6px', 
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '16px'
          }}>🧬</div>
          <h1 style={{ 
            margin: 0, 
            fontSize: '16px', 
            fontWeight: '800', 
            fontFamily: 'var(--font-sans)',
            letterSpacing: '0.1em',
            background: 'var(--gradient-primary)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>
            {activeView === 'history' ? 'ARCHIVE VAULT' : 'EXECUTION DASHBOARD'}
          </h1>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', fontWeight: '800', color: isRunning ? 'var(--color-success)' : 'var(--text-muted)' }}>
             <span className="status-dot" style={{ width: '8px', height: '8px', borderRadius: '50%', background: isRunning ? 'var(--color-success)' : 'var(--text-muted)', animation: isRunning ? 'pulse 2s infinite' : 'none' }} />
             {isRunning ? 'PIPELINE_ACTIVE' : 'NOMINAL_STANDBY'}
          </div>
          {activeTaskId && (
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', background: 'rgba(255,255,255,0.03)', padding: '4px 8px', borderRadius: '4px' }}>
              TSK: {activeTaskId.substring(0, 8)}
            </div>
          )}
        </div>
      </div>

      {/* ── TOP SECTION: TASK OBJECTIVE ── */}
      {activeView === 'pipeline' && (
        <div style={{ flex: '0 0 auto' }}>
          <DashboardTaskInput onLogsUpdate={setLogs} setIsRunning={setIsRunning} isRunning={isRunning} />
        </div>
      )}

      {/* ── AGENT PULSE SECTION (HORIZONTAL) ── */}
      {activeView === 'pipeline' && (
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
          gap: '16px' 
        }}>
          {[
            { name: 'Executive', color: '#40cef3', icon: '🎯' },
            { name: 'Department', color: '#ffa44c', icon: '🏢' },
            { name: 'Employee', color: '#10b981', icon: '⚙️' },
          ].map((agent) => {
            const count = visibleLogs.filter((l) => l.agent === agent.name).length;
            return (
              <div key={agent.name} className="card" style={{ 
                padding: '16px', 
                background: 'rgba(0,0,0,0.2)', 
                border: '1px solid var(--border-subtle)', 
                display: 'flex', 
                alignItems: 'center', 
                gap: '16px',
                borderLeft: `3px solid ${agent.color}`,
                transition: 'all 0.3s'
              }}>
                <div style={{ fontSize: '20px' }}>{agent.icon}</div>
                <div>
                  <div style={{ fontSize: '20px', fontWeight: '900', color: 'white', lineHeight: 1 }}>{count}</div>
                  <div style={{ fontSize: '9px', color: 'var(--text-muted)', fontWeight: '800', textTransform: 'uppercase', marginTop: '4px' }}>{agent.name} INTERACTIONS</div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── MAIN CONTENT AREA ── */}
      <div style={{ 
        flex: '1 0 auto', 
        display: 'flex', 
        flexDirection: 'column', 
        gap: '20px', 
        minHeight: '600px'
      }}>
        
        {/* Navigation & Controls */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px'
        }}>
          {activeView === 'pipeline' ? (
            <div style={{ display: 'flex', background: 'var(--bg-tertiary)', padding: '4px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
              <button 
                onClick={() => setTrackerSubView('timeline')}
                style={{
                  background: trackerSubView === 'timeline' ? 'var(--bg-active)' : 'transparent',
                  color: trackerSubView === 'timeline' ? 'white' : 'var(--text-muted)',
                  border: 'none', padding: '6px 16px', borderRadius: '6px', fontSize: '11px', fontWeight: '800', cursor: 'pointer', transition: 'all 0.2s'
                }}
              >
                TIMELINE
              </button>
              <button 
                onClick={() => setTrackerSubView('flow')}
                style={{
                  background: trackerSubView === 'flow' ? 'var(--bg-active)' : 'transparent',
                  color: trackerSubView === 'flow' ? 'white' : 'var(--text-muted)',
                  border: 'none', padding: '6px 16px', borderRadius: '6px', fontSize: '11px', fontWeight: '800', cursor: 'pointer', transition: 'all 0.2s'
                }}
              >
                HIERARCHY FLOW
              </button>
            </div>
          ) : <div />}

          {activeView === 'pipeline' && (
            <div style={{ flex: '0 0 auto' }}>
              <PlaybackControls
                totalLogs={logs.length}
                playbackIndex={playbackIndex}
                setPlaybackIndex={handleManualPlaybackChange}
                isPlaying={isPlaying}
                setIsPlaying={(val) => {
                  setIsPlaying(val);
                  if (val) isLiveTracking.current = false;
                }}
                speed={playbackSpeed}
                setSpeed={setPlaybackSpeed}
              />
            </div>
          )}
        </div>

        {/* Trace Card (Visualization) */}
        <div className="card" style={{ 
          flex: '1 0 600px',
          display: 'flex', 
          flexDirection: 'column', 
          overflow: 'hidden', 
          border: '1px solid var(--border-active)', 
          boxShadow: 'var(--shadow-glow)',
          background: 'rgba(11, 14, 20, 0.4)',
          minHeight: '600px',
          position: 'relative'
        }}>
          <div style={{ 
            padding: '12px 24px', 
            background: 'rgba(0,0,0,0.2)', 
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            zIndex: 10
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '14px' }}>
                {trackerSubView === 'flow' ? '🕸️' : '🚥'}
              </span>
              <h2 style={{ fontSize: '10px', fontWeight: '900', color: 'white', textTransform: 'uppercase', letterSpacing: '0.1em', margin: 0 }}>
                {activeView === 'history' ? 'Execution Archive' : (trackerSubView === 'flow' ? 'Neural Network Path' : 'Real-Time Operational Trace')}
              </h2>
            </div>
            
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              {visibleLogs.length} SIGNALS
            </div>
          </div>

          <div style={{ flex: 1, position: 'relative', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            {activeView === 'history' ? (
              <div style={{ padding: '24px', overflowY: 'auto', height: '100%' }}>
                {history.length === 0 ? (
                  <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', opacity: 0.3 }}>
                    <span style={{ fontSize: '40px', marginBottom: '12px' }}>🗄️</span>
                    <div style={{ fontSize: '12px', fontWeight: '800' }}>ARCHIVE VAULT EMPTY</div>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    {history.map((task, i) => (
                      <div key={task.task_id || i} className="card" style={{ padding: '16px', background: 'rgba(255,255,255,0.02)', cursor: 'default' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                          <span style={{ fontSize: '10px', fontWeight: '900', color: 'var(--color-ceo)', fontFamily: 'var(--font-mono)' }}>TSK-{task.task_id?.substring(0, 8).toUpperCase()}</span>
                          <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{new Date(task.created_at * 1000).toLocaleString()}</span>
                        </div>
                        <div style={{ fontSize: '13px', fontWeight: '600', color: 'white', marginBottom: '8px' }}>{task.description}</div>
                        <div style={{ display: 'flex', gap: '12px', fontSize: '10px', color: 'var(--text-muted)' }}>
                          <span>Status: <span style={{ color: task.status === 'success' ? 'var(--color-success)' : 'var(--color-error)' }}>{task.status?.toUpperCase() || 'UNKNOWN'}</span></span>
                          {task.cost && <span>Cost: ${typeof task.cost === 'number' ? task.cost.toFixed(4) : task.cost}</span>}
                          {task.tokens && <span>Tokens: {task.tokens}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              trackerSubView === 'flow' ? (
                <AgentFlowGraph logs={visibleLogs} staticTree={orgChart} activeAgents={activeAgents} />
              ) : (
                <Timeline
                  logs={visibleLogs}
                  selectedLogIndex={selectedLogIndex}
                  onSelectLog={setSelectedLogIndex}
                />
              )
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
