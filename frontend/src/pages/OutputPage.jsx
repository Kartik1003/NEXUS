/**
 * OutputPage — Fix #6: replaced 280-line hand-rolled Markdown parser
 * with react-markdown + react-syntax-highlighter.
 * All data-fetching logic, chat, deliverables, and file tree preserved intact.
 */
import React, { useMemo, useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

const DEPT_COLORS = {
  IT: '#3b82f6',
  Marketing: '#f59e0b',
  Finance: '#10b981',
  HR: '#a855f7',
  Operations: '#6b7280',
  'Customer Service': '#14b8a6',
};

function getDeptColor(dept) {
  return DEPT_COLORS[dept] || '#6b7280';
}

function formatTime(ts) {
  if (!ts) return '';
  try {
    return new Date(ts).toLocaleTimeString('en-US', { hour12: false });
  } catch {
    return ts;
  }
}

// react-markdown component overrides — matches the project's dark theme
const mdComponents = {
  code({ node, inline, className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || '');
    return !inline && match ? (
      <SyntaxHighlighter
        style={oneDark}
        language={match[1]}
        PreTag="div"
        customStyle={{
          borderRadius: '8px', fontSize: '12px', margin: '12px 0',
          border: '1px solid rgba(139,92,246,0.2)',
        }}
        {...props}
      >
        {String(children).replace(/\n$/, '')}
      </SyntaxHighlighter>
    ) : (
      <code
        style={{
          background: 'rgba(139,92,246,0.2)', color: '#c084fc',
          padding: '1px 5px', borderRadius: '4px',
          fontSize: '0.9em', fontFamily: 'var(--font-mono)',
        }}
        {...props}
      >
        {children}
      </code>
    );
  },
  p: ({ children }) => (
    <p style={{ margin: '4px 0', fontSize: '13px', lineHeight: '1.7', color: '#e2e8f0' }}>
      {children}
    </p>
  ),
  h1: ({ children }) => (
    <h1 style={{ fontSize: '20px', fontWeight: '800', color: 'white', margin: '16px 0 8px 0' }}>{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 style={{ fontSize: '16px', fontWeight: '700', color: '#c4b5fd', margin: '14px 0 6px 0' }}>{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 style={{ fontSize: '14px', fontWeight: '700', color: '#a5b4fc', margin: '12px 0 4px 0' }}>{children}</h3>
  ),
  ul: ({ children }) => (
    <ul style={{ margin: '8px 0', paddingLeft: '0', listStyle: 'none' }}>{children}</ul>
  ),
  ol: ({ children }) => (
    <ol style={{ margin: '8px 0', paddingLeft: '0', listStyle: 'none', counterReset: 'li' }}>{children}</ol>
  ),
  li: ({ children }) => (
    <li style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginBottom: '4px', fontSize: '13px', lineHeight: '1.6', color: '#e2e8f0' }}>
      <span style={{ color: '#40cef3', fontWeight: '800', minWidth: '14px', marginTop: '2px' }}>•</span>
      <span>{children}</span>
    </li>
  ),
  hr: () => (
    <hr style={{ border: 'none', borderTop: '1px solid rgba(255,255,255,0.08)', margin: '16px 0' }} />
  ),
  blockquote: ({ children }) => (
    <blockquote style={{
      borderLeft: '3px solid #6366f1', paddingLeft: '12px',
      color: '#94a3b8', fontStyle: 'italic', margin: '8px 0',
    }}>
      {children}
    </blockquote>
  ),
};

export default function OutputPage({ logs = [], activeTaskId }) {
  const [expandedFiles, setExpandedFiles] = useState({});
  const [fetchedFiles, setFetchedFiles]   = useState([]);
  const [fetchedChats, setFetchedChats]   = useState([]);
  const [copiedKey, setCopiedKey]         = useState(null);
  const chatEndRef = useRef(null);

  const finalResult = useMemo(() => (
    logs.find(l => l.event === 'task_complete') || null
  ), [logs]);

  const steps   = useMemo(() => finalResult?.steps   || [], [finalResult]);
  const metrics = useMemo(() => finalResult?.metrics  || {}, [finalResult]);

  const liveChats   = useMemo(() => logs.filter(l => l.event === 'agent_chat'),     [logs]);
  const liveOutputs = useMemo(() => logs.filter(l => l.event === 'employee_output'), [logs]);

  const allChats = useMemo(() => {
    const seen = new Set();
    const merged = [];
    for (const c of [...liveChats, ...fetchedChats]) {
      const key = `${c.from_handle}-${c.timestamp}-${(c.message || '').slice(0, 30)}`;
      if (!seen.has(key)) { seen.add(key); merged.push(c); }
    }
    merged.sort((a, b) => (a.timestamp || '').localeCompare(b.timestamp || ''));
    return merged;
  }, [liveChats, fetchedChats]);

  const deliverables = useMemo(() => {
    const byEmployee = {};
    for (const out of liveOutputs) {
      const key = out.handle || out.employee_name;
      if (!byEmployee[key]) {
        byEmployee[key] = { employee_name: out.employee_name, handle: out.handle, department: out.department, files: [] };
      }
      for (const f of (out.files_produced || [])) {
        byEmployee[key].files.push({ filename: f.filename, size: f.size, content: null });
      }
    }
    for (const f of fetchedFiles) {
      const key = f.employee_handle || 'unknown';
      if (!byEmployee[key]) {
        byEmployee[key] = { employee_name: key, handle: key, department: '', files: [] };
      }
      const existing = byEmployee[key].files.find(ef => ef.filename === f.filename);
      if (existing) { existing.content = f.content; existing.size = f.size || (f.content ? f.content.length : 0); }
      else { byEmployee[key].files.push({ filename: f.filename, size: f.size, content: f.content }); }
    }
    return Object.values(byEmployee);
  }, [liveOutputs, fetchedFiles]);

  useEffect(() => {
    if (finalResult && activeTaskId) {
      fetch(`/api/tasks/${activeTaskId}/files`)
        .then(r => r.json()).then(d => setFetchedFiles(d.files || [])).catch(() => {});
      fetch(`/api/tasks/${activeTaskId}/chat`)
        .then(r => r.json()).then(d => setFetchedChats(d.messages || [])).catch(() => {});
    }
  }, [finalResult, activeTaskId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [allChats.length]);

  const toggleFile = (empHandle, filename) => {
    const key = `${empHandle}_${filename}`;
    setExpandedFiles(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const copyToClipboard = (content, key) => {
    navigator.clipboard.writeText(content).then(() => {
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    });
  };

  const handleDownloadAll = () => {
    let blob = '';
    for (const emp of deliverables) {
      for (const f of emp.files) {
        if (f.content) blob += `=== FILE: ${f.filename} ===\n${f.content}\n\n`;
      }
    }
    if (!blob) {
      for (const f of fetchedFiles) blob += `=== FILE: ${f.filename} ===\n${f.content || ''}\n\n`;
    }
    if (!blob) return;
    const url = URL.createObjectURL(new Blob([blob], { type: 'text/plain' }));
    const a = Object.assign(document.createElement('a'), { href: url, download: 'deliverables.txt' });
    a.click();
    URL.revokeObjectURL(url);
  };

  const wrap = { padding: '24px', height: '100%', background: 'var(--bg-primary)', color: 'var(--text-primary)', display: 'flex', flexDirection: 'column', gap: '24px', overflow: 'hidden' };
  const sectionHead = { fontSize: '13px', fontWeight: '900', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', margin: '0 0 12px 0' };
  const card = { background: 'var(--bg-tertiary)', borderRadius: '12px', border: '1px solid var(--border-subtle)', padding: '20px' };

  if (!finalResult) {
    return (
      <div style={wrap}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-sans)', fontSize: '32px', fontWeight: '800', background: 'var(--gradient-primary)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', margin: 0 }}>
            Execution Report
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
            Final output, deliverables, agent communications, and produced files.
          </p>
        </div>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', opacity: 0.3 }}>
          <span style={{ fontSize: '48px', marginBottom: '16px' }}>⚙️</span>
          <div style={{ fontWeight: '800', letterSpacing: '0.1em' }}>AWAITING FINAL OUTPUT</div>
          <div style={{ fontSize: '11px', marginTop: '8px' }}>The task is still processing or hasn't started yet.</div>
        </div>
      </div>
    );
  }

  const totalEmployees = steps.length;
  const deptSet = new Set(steps.map(s => s.department));
  const statusBadge = finalResult?.status || 'in_progress';

  return (
    <div style={wrap}>
      <div>
        <h1 style={{ fontFamily: 'var(--font-sans)', fontSize: '32px', fontWeight: '800', background: 'var(--gradient-primary)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', margin: 0 }}>
          Execution Report
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
          Final output, deliverables, agent communications, and produced files.
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', flex: 1, overflowY: 'auto' }}>

        {/* Pipeline Summary */}
        <div>
          <h2 style={sectionHead}>Pipeline Summary</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px' }}>
            {[
              { label: 'Employees',  value: totalEmployees, color: 'white' },
              { label: 'Departments',value: deptSet.size,   color: 'white' },
              { label: 'Tokens',     value: (metrics?.total_tokens || 0).toLocaleString(), color: 'white' },
              { label: 'Cost (USD)', value: `$${(metrics?.total_cost_usd || 0).toFixed(6)}`, color: 'var(--color-success)' },
            ].map(({ label, value, color }) => (
              <div key={label} style={{ background: 'var(--bg-tertiary)', borderRadius: '12px', border: '1px solid var(--border-subtle)', padding: '16px' }}>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '800', letterSpacing: '0.1em' }}>{label}</div>
                <div style={{ fontSize: '24px', fontWeight: '900', color, marginTop: '6px' }}>{value}</div>
              </div>
            ))}
            <div style={{ background: 'var(--bg-tertiary)', borderRadius: '12px', border: '1px solid var(--border-subtle)', padding: '16px' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '800', letterSpacing: '0.1em' }}>Status</div>
              <div style={{ marginTop: '6px' }}>
                <span style={{
                  background: statusBadge === 'success' ? 'rgba(16,185,129,0.15)' : statusBadge === 'partial_success' ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)',
                  color: statusBadge === 'success' ? '#10b981' : statusBadge === 'partial_success' ? '#f59e0b' : '#ef4444',
                  padding: '4px 12px', borderRadius: '6px', fontSize: '11px', fontWeight: '800', textTransform: 'uppercase',
                }}>
                  {statusBadge.replace('_', ' ')}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Agent Chat Log */}
        <div style={{ ...card, maxHeight: '500px', display: 'flex', flexDirection: 'column' }}>
          <h2 style={sectionHead}>💬 Agent Chat Log ({allChats.length})</h2>
          {allChats.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontSize: '12px', fontStyle: 'italic' }}>
              {finalResult ? 'No direct agent-to-agent messages in this run.' : 'Waiting for agent communications...'}
            </div>
          ) : (
            <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {allChats.map((chat, idx) => {
                const dept = liveOutputs.find(o => o.handle === chat.from_handle)?.department || '';
                return (
                  <div key={idx} style={{ background: 'rgba(0,0,0,0.25)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '10px', padding: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                      <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: getDeptColor(dept), display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: '900', fontSize: '14px', color: '#fff', flexShrink: 0 }}>
                        {(chat.from_name || '?')[0].toUpperCase()}
                      </div>
                      <div style={{ flex: 1, fontSize: '12px', fontWeight: '700' }}>
                        <span style={{ color: 'white' }}>{chat.from_name}</span>
                        <span style={{ color: 'var(--text-muted)', fontSize: '10px', marginLeft: '4px' }}>({chat.from_handle})</span>
                        <span style={{ color: 'var(--text-muted)', margin: '0 6px', fontSize: '10px' }}>→</span>
                        <span style={{ color: '#a5b4fc' }}>{chat.to_name}</span>
                      </div>
                      <div style={{ fontSize: '9px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{formatTime(chat.timestamp)}</div>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.6', paddingLeft: '42px' }}>
                      {chat.message}
                    </div>
                  </div>
                );
              })}
              <div ref={chatEndRef} />
            </div>
          )}
        </div>

        {/* Deliverables */}
        <div style={{ ...card, maxHeight: '500px', display: 'flex', flexDirection: 'column' }}>
          <h2 style={sectionHead}>📦 Deliverables ({deliverables.length} employees)</h2>
          {deliverables.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontSize: '12px', fontStyle: 'italic' }}>
              {finalResult ? 'No file deliverables recorded.' : 'Waiting for employee outputs...'}
            </div>
          ) : (
            <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {deliverables.map((emp, empIdx) => (
                <div key={empIdx} style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '10px', padding: '14px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: getDeptColor(emp.department) }} />
                    <span style={{ fontSize: '12px', fontWeight: '700', color: 'white' }}>{emp.employee_name}</span>
                    <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{emp.handle}</span>
                    {emp.department && (
                      <span style={{ fontSize: '9px', padding: '2px 6px', borderRadius: '4px', background: `${getDeptColor(emp.department)}22`, color: getDeptColor(emp.department), fontWeight: '700', marginLeft: 'auto' }}>
                        {emp.department}
                      </span>
                    )}
                  </div>
                  {emp.files.map((file, fIdx) => {
                    const fileKey = `${emp.handle}_${file.filename}`;
                    const isExpanded = expandedFiles[fileKey];
                    return (
                      <div key={fIdx} style={{ marginBottom: '6px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', borderRadius: '6px', background: 'rgba(255,255,255,0.03)' }}>
                          <span style={{ fontSize: '12px', color: '#94a3b8' }}>📄</span>
                          <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', flex: 1 }}>{file.filename}</span>
                          <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{(file.size || 0).toLocaleString()} chars</span>
                          {file.content && (
                            <>
                              <button onClick={() => toggleFile(emp.handle, file.filename)}
                                style={{ background: 'rgba(59,130,246,0.15)', color: '#60a5fa', border: 'none', borderRadius: '4px', padding: '3px 10px', fontSize: '10px', fontWeight: '700', cursor: 'pointer' }}>
                                {isExpanded ? 'Hide' : 'View'}
                              </button>
                              <button onClick={() => copyToClipboard(file.content, fileKey)}
                                style={{ background: copiedKey === fileKey ? 'rgba(16,185,129,0.15)' : 'rgba(255,255,255,0.06)', color: copiedKey === fileKey ? '#10b981' : 'var(--text-muted)', border: 'none', borderRadius: '4px', padding: '3px 10px', fontSize: '10px', fontWeight: '700', cursor: 'pointer' }}>
                                {copiedKey === fileKey ? '✓ Copied' : 'Copy'}
                              </button>
                            </>
                          )}
                        </div>
                        {isExpanded && file.content && (
                          <pre style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', overflowX: 'auto', whiteSpace: 'pre', background: 'rgba(0,0,0,0.4)', padding: '16px', borderRadius: '8px', maxHeight: '400px', overflowY: 'auto', color: '#e2e8f0', margin: '6px 0 0 0', border: '1px solid rgba(255,255,255,0.05)' }}>
                            {file.content}
                          </pre>
                        )}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* File Tree + Download */}
        <div style={card}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <h2 style={{ ...sectionHead, margin: 0 }}>🗂️ All Produced Files</h2>
            <button onClick={handleDownloadAll}
              style={{ background: 'linear-gradient(135deg, #3b82f6, #6366f1)', color: 'white', border: 'none', borderRadius: '8px', padding: '8px 20px', fontSize: '12px', fontWeight: '700', cursor: 'pointer' }}>
              ⬇ Download All
            </button>
          </div>
          {deliverables.map((emp, empIdx) => (
            <div key={empIdx} style={{ marginBottom: '8px' }}>
              <div style={{ fontSize: '11px', fontWeight: '700', color: getDeptColor(emp.department), marginBottom: '4px' }}>
                {emp.employee_name} ({emp.handle})
              </div>
              {emp.files.map((file, fIdx) => (
                <div key={fIdx} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 0 4px 16px' }}>
                  <span style={{ color: '#94a3b8', fontSize: '11px' }}>└</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)' }}>{file.filename}</span>
                  <span style={{ fontSize: '9px', color: 'var(--text-muted)' }}>({(file.size || 0).toLocaleString()} chars)</span>
                </div>
              ))}
            </div>
          ))}
        </div>

        {/* Aggregated Output — now using react-markdown (Fix #6) */}
        {finalResult?.result && (
          <div style={card}>
            <h2 style={sectionHead}>📝 Aggregated Output</h2>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '20px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)', maxHeight: '500px', overflowY: 'auto' }}>
              <ReactMarkdown components={mdComponents}>
                {finalResult.result}
              </ReactMarkdown>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
