import React, { useState } from 'react';

export default function TelemetryPage({ logs = [] }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedLog, setSelectedLog] = useState(null);

  const filteredLogs = logs.filter(log => 
    log.agent_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    log.message?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    log.agent?.toLowerCase().includes(searchTerm.toLowerCase())
  ).reverse(); // Newest first

  const renderJSON = (obj) => {
    const str = JSON.stringify(obj, null, 2);
    return str.split('\n').map((line, i) => {
      const highlighted = line
        .replace(/"([^"]+)":/g, '<span style="color: #d095ff">"$1"</span>:')
        .replace(/: "([^"]*?)"/g, ': <span style="color: #10b981">"$1"</span>')
        .replace(/: (\d+\.?\d*)/g, ': <span style="color: #40cef3">$1</span>')
        .replace(/: (true|false)/g, ': <span style="color: #ffa44c">$1</span>')
        .replace(/: (null)/g, ': <span style="color: #6b7280">$1</span>');
      return (
        <div key={i} style={{ display: 'flex' }}>
          <span style={{ userSelect: 'none', color: '#4b5563', width: '32px', textAlign: 'right', marginRight: '12px', flexShrink: 0, fontSize: '10px' }}>
            {i + 1}
          </span>
          <span dangerouslySetInnerHTML={{ __html: highlighted }} />
        </div>
      );
    });
  };

  const getAgentColor = (agent) => {
    const map = {
      CEO: '#d095ff',
      Executive: '#40cef3',
      Department: '#ffa44c',
      Employee: '#10b981',
    };
    return map[agent] || '#a9abb3';
  };

  return (
    <div className="telemetry-page" style={{ 
      padding: '24px', 
      height: '100vh', 
      background: 'var(--bg-primary)', 
      color: 'var(--text-primary)',
      display: 'flex',
      flexDirection: 'column',
      gap: '24px'
    }}>
      {/* Header */}
      <div>
        <h1 style={{ 
          fontFamily: 'var(--font-sans)', 
          fontSize: '32px', 
          fontWeight: '800', 
          background: 'var(--gradient-primary)', 
          WebkitBackgroundClip: 'text', 
          WebkitTextFillColor: 'transparent', 
          margin: 0 
        }}>
          System Telemetry
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
          Global execution event stream and payload inspector.
        </p>
      </div>

      <div style={{ display: 'flex', gap: '24px', flex: 1, minHeight: 0 }}>
        {/* Log List */}
        <div style={{ 
          flex: '0 0 400px', 
          background: 'var(--bg-tertiary)', 
          borderRadius: 'var(--radius-lg)', 
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}>
          <div style={{ padding: '16px', borderBottom: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.2)' }}>
            <input 
              type="text" 
              placeholder="Filter logs by agent or message..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                width: '100%',
                background: 'var(--bg-primary)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '8px 12px',
                color: 'white',
                fontSize: '12px',
                fontFamily: 'var(--font-mono)'
              }}
            />
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
            {filteredLogs.map((log, i) => (
              <div 
                key={i}
                onClick={() => setSelectedLog(log)}
                style={{
                  padding: '12px',
                  borderRadius: 'var(--radius-md)',
                  background: selectedLog === log ? 'rgba(255,255,255,0.05)' : 'transparent',
                  border: `1px solid ${selectedLog === log ? 'rgba(255,255,255,0.1)' : 'transparent'}`,
                  cursor: 'pointer',
                  marginBottom: '8px',
                  transition: 'all 0.2s'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontSize: '10px', fontWeight: '900', color: getAgentColor(log.agent), textTransform: 'uppercase' }}>
                    {log.agent}
                  </span>
                  <span style={{ fontSize: '9px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {log.timestamp || '00:00:00'}
                  </span>
                </div>
                <div style={{ fontSize: '12px', fontWeight: '700', color: 'white' }}>{log.agent_name}</div>
                <div style={{ 
                  fontSize: '11px', 
                  color: 'var(--text-muted)', 
                  marginTop: '4px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap'
                }}>
                  {log.message}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Detailed Inspector */}
        <div style={{ 
          flex: 1, 
          background: 'var(--bg-tertiary)', 
          borderRadius: 'var(--radius-lg)', 
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}>
          {selectedLog ? (
            <>
              <div style={{ 
                padding: '16px 24px', 
                background: 'rgba(0,0,0,0.2)', 
                borderBottom: '1px solid var(--border-subtle)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div>
                  <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '800' }}>{selectedLog.agent_name}</h2>
                  <span style={{ fontSize: '10px', color: getAgentColor(selectedLog.agent), fontWeight: '900', textTransform: 'uppercase' }}>
                    {selectedLog.agent} Inspector
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '12px' }}>
                   <div style={{ 
                     padding: '4px 12px', 
                     borderRadius: '4px', 
                     background: 'rgba(255,255,255,0.05)', 
                     fontSize: '10px', 
                     fontWeight: '700',
                     border: '1px solid rgba(255,255,255,0.1)'
                   }}>
                     STATUS: {selectedLog.status?.toUpperCase()}
                   </div>
                </div>
              </div>
              <div style={{ flex: 1, overflowY: 'auto', padding: '32px' }}>
                 <div style={{ marginBottom: '32px' }}>
                    <div style={{ fontSize: '10px', fontWeight: '900', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>Log Message</div>
                    <p style={{ fontSize: '16px', lineHeight: '1.6', margin: 0 }}>{selectedLog.message}</p>
                 </div>
                 
                 <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <div style={{ fontSize: '10px', fontWeight: '900', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Raw Payload</div>
                      <button 
                        onClick={() => navigator.clipboard.writeText(JSON.stringify(selectedLog, null, 2))}
                        style={{ background: 'transparent', border: '1px solid var(--border-subtle)', color: 'var(--text-muted)', fontSize: '9px', padding: '4px 10px', borderRadius: '4px', cursor: 'pointer' }}
                      >
                        COPY JSON
                      </button>
                    </div>
                    <div style={{ 
                      background: 'rgba(0,0,0,0.3)', 
                      borderRadius: 'var(--radius-md)', 
                      padding: '20px',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '12px',
                      lineHeight: '1.6',
                      border: '1px solid rgba(255,255,255,0.05)'
                    }}>
                      {renderJSON(selectedLog)}
                    </div>
                 </div>
              </div>
            </>
          ) : (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', opacity: 0.3 }}>
               <span style={{ fontSize: '48px', marginBottom: '16px' }}>📡</span>
               <div style={{ fontWeight: '800', letterSpacing: '0.1em' }}>AWAITING SIGNAL</div>
               <div style={{ fontSize: '11px', marginTop: '8px' }}>Select an event from the stream to inspect its telemetry data.</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
