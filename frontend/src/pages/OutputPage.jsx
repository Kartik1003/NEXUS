import React, { useMemo, useState, useEffect, useRef } from 'react';

/* ── Inline Markdown Renderer ───────────────────────────────────── */
function MarkdownRenderer({ content }) {
  const lines = (content || '').split('\n');
  const elements = [];
  let i = 0;

  const parseInline = (text) => {
    // Bold+Italic, Bold, Italic, Inline Code
    const parts = [];
    const regex = /(\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)/g;
    let last = 0, m;
    while ((m = regex.exec(text)) !== null) {
      if (m.index > last) parts.push(text.slice(last, m.index));
      if (m[2]) parts.push(<strong key={m.index}><em>{m[2]}</em></strong>);
      else if (m[3]) parts.push(<strong key={m.index}>{m[3]}</strong>);
      else if (m[4]) parts.push(<em key={m.index}>{m[4]}</em>);
      else if (m[5]) parts.push(
        <code key={m.index} style={{ background: 'rgba(139,92,246,0.2)', color: '#c084fc', padding: '1px 5px', borderRadius: '4px', fontSize: '0.9em', fontFamily: 'var(--font-mono)' }}>{m[5]}</code>
      );
      last = m.index + m[0].length;
    }
    if (last < text.length) parts.push(text.slice(last));
    return parts.length === 1 && typeof parts[0] === 'string' ? parts[0] : parts;
  };

  while (i < lines.length) {
    const line = lines[i];

    // Fenced code block
    if (line.startsWith('```')) {
      const lang = line.slice(3).trim();
      const codeLines = [];
      i++;
      while (i < lines.length && !lines[i].startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      elements.push(
        <pre key={i} style={{ background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(139,92,246,0.2)', borderRadius: '8px', padding: '16px', overflowX: 'auto', margin: '12px 0', fontSize: '12px', fontFamily: 'var(--font-mono)', color: '#e2e8f0', lineHeight: '1.6' }}>
          {lang && <div style={{ fontSize: '9px', color: '#6b7280', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.1em' }}>{lang}</div>}
          <code>{codeLines.join('\n')}</code>
        </pre>
      );
      i++;
      continue;
    }

    // HR
    if (/^---+$/.test(line.trim())) {
      elements.push(<hr key={i} style={{ border: 'none', borderTop: '1px solid rgba(255,255,255,0.08)', margin: '16px 0' }} />);
      i++; continue;
    }

    // Headings
    const h = line.match(/^(#{1,6})\s+(.*)/);
    if (h) {
      const level = h[1].length;
      const sizes = { 1: '22px', 2: '18px', 3: '15px', 4: '13px', 5: '12px', 6: '11px' };
      const colors = { 1: '#d095ff', 2: '#40cef3', 3: '#ffa44c', 4: '#10b981', 5: '#e2e8f0', 6: '#94a3b8' };
      elements.push(
        <div key={i} style={{ fontSize: sizes[level], fontWeight: '800', color: colors[level], margin: level <= 2 ? '20px 0 8px' : '14px 0 6px', lineHeight: '1.3', borderBottom: level === 1 ? '1px solid rgba(208,149,255,0.2)' : 'none', paddingBottom: level === 1 ? '8px' : '0' }}>
          {parseInline(h[2])}
        </div>
      );
      i++; continue;
    }

    // Blockquote
    if (line.startsWith('> ')) {
      const bqLines = [];
      while (i < lines.length && lines[i].startsWith('> ')) {
        bqLines.push(lines[i].slice(2));
        i++;
      }
      elements.push(
        <div key={i} style={{ borderLeft: '3px solid #6366f1', paddingLeft: '14px', margin: '10px 0', color: '#94a3b8', fontStyle: 'italic', background: 'rgba(99,102,241,0.06)', borderRadius: '0 6px 6px 0', padding: '10px 14px' }}>
          {bqLines.map((bl, bi) => <div key={bi}>{parseInline(bl)}</div>)}
        </div>
      );
      continue;
    }

    // Unordered list
    if (/^(\s*)[*\-+]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^(\s*)[*\-+]\s+/.test(lines[i])) {
        const indent = lines[i].match(/^(\s*)/)[1].length;
        items.push({ text: lines[i].replace(/^\s*[*\-+]\s+/, ''), indent });
        i++;
      }
      elements.push(
        <ul key={i} style={{ margin: '8px 0', paddingLeft: '0', listStyle: 'none' }}>
          {items.map((it, ii) => (
            <li key={ii} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginBottom: '4px', paddingLeft: `${it.indent * 12}px`, fontSize: '13px', lineHeight: '1.6', color: '#e2e8f0' }}>
              <span style={{ color: '#6366f1', marginTop: '6px', flexShrink: 0, fontSize: '8px' }}>◆</span>
              <span>{parseInline(it.text)}</span>
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // Ordered list
    if (/^\d+\.\s+/.test(line)) {
      const items = [];
      let num = 1;
      while (i < lines.length && /^\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\.\s+/, ''));
        i++;
      }
      elements.push(
        <ol key={i} style={{ margin: '8px 0', paddingLeft: '0', listStyle: 'none', counterReset: 'li' }}>
          {items.map((it, ii) => (
            <li key={ii} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', marginBottom: '4px', fontSize: '13px', lineHeight: '1.6', color: '#e2e8f0' }}>
              <span style={{ color: '#40cef3', fontWeight: '800', fontSize: '11px', minWidth: '18px', textAlign: 'right', marginTop: '2px' }}>{ii + 1}.</span>
              <span>{parseInline(it)}</span>
            </li>
          ))}
        </ol>
      );
      continue;
    }

    // Empty line = spacing
    if (line.trim() === '') {
      elements.push(<div key={i} style={{ height: '6px' }} />);
      i++; continue;
    }

    // Normal paragraph
    elements.push(
      <p key={i} style={{ margin: '4px 0', fontSize: '13px', lineHeight: '1.7', color: '#e2e8f0' }}>
        {parseInline(line)}
      </p>
    );
    i++;
  }

  return <div style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>{elements}</div>;
}

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
    const d = new Date(ts);
    return d.toLocaleTimeString('en-US', { hour12: false });
  } catch {
    return ts;
  }
}

export default function OutputPage({ logs = [], activeTaskId }) {
  const [expandedFiles, setExpandedFiles] = useState({});
  const [fetchedFiles, setFetchedFiles] = useState([]);
  const [fetchedChats, setFetchedChats] = useState([]);
  const [copiedKey, setCopiedKey] = useState(null);
  const chatEndRef = useRef(null);

  // Find the task completion event
  const finalResult = useMemo(() => {
    return logs.find(l => l.event === 'task_complete') || null;
  }, [logs]);

  const steps = useMemo(() => finalResult?.steps || [], [finalResult]);
  const metrics = useMemo(() => finalResult?.metrics || {}, [finalResult]);

  // Extract agent_chat events from live logs
  const liveChats = useMemo(() => {
    return logs.filter(l => l.event === 'agent_chat');
  }, [logs]);

  // Extract employee_output events from live logs
  const liveOutputs = useMemo(() => {
    return logs.filter(l => l.event === 'employee_output');
  }, [logs]);

  // Merged chats: live + fetched (deduplicated by timestamp)
  const allChats = useMemo(() => {
    const seen = new Set();
    const merged = [];
    for (const c of [...liveChats, ...fetchedChats]) {
      const key = `${c.from_handle}-${c.timestamp}-${c.message?.slice(0, 30)}`;
      if (!seen.has(key)) {
        seen.add(key);
        merged.push(c);
      }
    }
    merged.sort((a, b) => (a.timestamp || '').localeCompare(b.timestamp || ''));
    return merged;
  }, [liveChats, fetchedChats]);

  // Build deliverables from live outputs + fetched files
  const deliverables = useMemo(() => {
    const byEmployee = {};

    // From live employee_output events
    for (const out of liveOutputs) {
      const key = out.handle || out.employee_name;
      if (!byEmployee[key]) {
        byEmployee[key] = {
          employee_name: out.employee_name,
          handle: out.handle,
          department: out.department,
          files: [],
        };
      }
      if (out.files_produced) {
        for (const f of out.files_produced) {
          byEmployee[key].files.push({ filename: f.filename, size: f.size, content: null });
        }
      }
    }

    // From fetched files (these have content)
    for (const f of fetchedFiles) {
      const key = f.employee_handle || 'unknown';
      if (!byEmployee[key]) {
        byEmployee[key] = {
          employee_name: key,
          handle: key,
          department: '',
          files: [],
        };
      }
      // Check if file already exists (from live event), update with content
      const existing = byEmployee[key].files.find(ef => ef.filename === f.filename);
      if (existing) {
        existing.content = f.content;
        existing.size = f.size || (f.content ? f.content.length : 0);
      } else {
        byEmployee[key].files.push({ filename: f.filename, size: f.size, content: f.content });
      }
    }

    return Object.values(byEmployee);
  }, [liveOutputs, fetchedFiles]);

  // Fetch files and chats when task completes
  useEffect(() => {
    if (finalResult && activeTaskId) {
      fetch(`/api/tasks/${activeTaskId}/files`)
        .then(r => r.json())
        .then(data => setFetchedFiles(data.files || []))
        .catch(() => {});

      fetch(`/api/tasks/${activeTaskId}/chat`)
        .then(r => r.json())
        .then(data => setFetchedChats(data.messages || []))
        .catch(() => {});
    }
  }, [finalResult, activeTaskId]);

  // Auto-scroll chat
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
        if (f.content) {
          blob += `=== FILE: ${f.filename} ===\n${f.content}\n\n`;
        }
      }
    }
    // Also from fetchedFiles directly
    if (!blob) {
      for (const f of fetchedFiles) {
        blob += `=== FILE: ${f.filename} ===\n${f.content || ''}\n\n`;
      }
    }
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([blob], { type: 'text/plain' }));
    a.download = 'project_output.txt';
    a.click();
  };

  // ------- RENDER --------

  if (!finalResult && liveOutputs.length === 0 && allChats.length === 0) {
    return (
      <div style={{ padding: '24px', height: '100%', background: 'var(--bg-primary)', color: 'var(--text-primary)', display: 'flex', flexDirection: 'column', gap: '24px', overflow: 'hidden' }}>
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
    <div style={{ padding: '24px', height: '100%', background: 'var(--bg-primary)', color: 'var(--text-primary)', display: 'flex', flexDirection: 'column', gap: '24px', overflow: 'hidden' }}>
      {/* Header */}
      <div>
        <h1 style={{ fontFamily: 'var(--font-sans)', fontSize: '32px', fontWeight: '800', background: 'var(--gradient-primary)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', margin: 0 }}>
          Execution Report
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
          Final output, deliverables, agent communications, and produced files.
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', flex: 1, overflowY: 'auto' }}>

        {/* SECTION 1 — PIPELINE SUMMARY */}
        {finalResult && (
          <div>
            <h2 style={{ fontSize: '13px', fontWeight: '900', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', margin: '0 0 12px 0' }}>Pipeline Summary</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px' }}>
              <div style={{ background: 'var(--bg-tertiary)', borderRadius: '12px', border: '1px solid var(--border-subtle)', padding: '16px' }}>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '800', letterSpacing: '0.1em' }}>Employees</div>
                <div style={{ fontSize: '24px', fontWeight: '900', color: 'white', marginTop: '6px' }}>{totalEmployees}</div>
              </div>
              <div style={{ background: 'var(--bg-tertiary)', borderRadius: '12px', border: '1px solid var(--border-subtle)', padding: '16px' }}>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '800', letterSpacing: '0.1em' }}>Departments</div>
                <div style={{ fontSize: '24px', fontWeight: '900', color: 'white', marginTop: '6px' }}>{deptSet.size}</div>
              </div>
              <div style={{ background: 'var(--bg-tertiary)', borderRadius: '12px', border: '1px solid var(--border-subtle)', padding: '16px' }}>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '800', letterSpacing: '0.1em' }}>Tokens Used</div>
                <div style={{ fontSize: '24px', fontWeight: '900', color: 'white', marginTop: '6px' }}>{(metrics?.total_tokens || 0).toLocaleString()}</div>
              </div>
              <div style={{ background: 'var(--bg-tertiary)', borderRadius: '12px', border: '1px solid var(--border-subtle)', padding: '16px' }}>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '800', letterSpacing: '0.1em' }}>Cost (USD)</div>
                <div style={{ fontSize: '24px', fontWeight: '900', color: 'var(--color-success)', marginTop: '6px' }}>${(metrics?.total_cost_usd || 0).toFixed(6)}</div>
              </div>
              <div style={{ background: 'var(--bg-tertiary)', borderRadius: '12px', border: '1px solid var(--border-subtle)', padding: '16px' }}>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '800', letterSpacing: '0.1em' }}>Status</div>
                <div style={{ marginTop: '6px' }}>
                  <span style={{
                    background: statusBadge === 'success' ? 'rgba(16,185,129,0.15)' : statusBadge === 'partial_success' ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)',
                    color: statusBadge === 'success' ? '#10b981' : statusBadge === 'partial_success' ? '#f59e0b' : '#ef4444',
                    padding: '4px 12px', borderRadius: '6px', fontSize: '11px', fontWeight: '800', textTransform: 'uppercase'
                  }}>
                    {statusBadge.replace('_', ' ')}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* SECTION 2 — AGENT CHAT LOG */}
        <div style={{ background: 'var(--bg-tertiary)', borderRadius: '12px', border: '1px solid var(--border-subtle)', padding: '20px', maxHeight: '500px', display: 'flex', flexDirection: 'column' }}>
          <h2 style={{ fontSize: '13px', fontWeight: '900', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', margin: '0 0 12px 0' }}>
            💬 Agent Chat Log ({allChats.length})
          </h2>
          {allChats.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontSize: '12px', fontStyle: 'italic' }}>
              {finalResult ? 'No direct agent-to-agent messages in this run.' : 'Waiting for agent communications...'}
            </div>
          ) : (
            <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {allChats.map((chat, idx) => {
                const dept = liveOutputs.find(o => o.handle === chat.from_handle)?.department || '';
                const avatarColor = getDeptColor(dept);
                const initial = (chat.from_name || '?')[0].toUpperCase();
                return (
                  <div key={idx} style={{ background: 'rgba(0,0,0,0.25)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '10px', padding: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                      <div style={{
                        width: '32px', height: '32px', borderRadius: '50%', background: avatarColor,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontWeight: '900', fontSize: '14px', color: '#fff', flexShrink: 0
                      }}>
                        {initial}
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: '12px', fontWeight: '700' }}>
                          <span style={{ color: 'white' }}>{chat.from_name}</span>
                          <span style={{ color: 'var(--text-muted)', fontSize: '10px', marginLeft: '4px' }}>({chat.from_handle})</span>
                          <span style={{ color: 'var(--text-muted)', margin: '0 6px', fontSize: '10px' }}>→</span>
                          <span style={{ color: '#a5b4fc' }}>{chat.to_name}</span>
                        </div>
                      </div>
                      <div style={{ fontSize: '9px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                        {formatTime(chat.timestamp)}
                      </div>
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

        {/* SECTION 3 — DELIVERABLES (per-employee cards) */}
        <div style={{ background: 'var(--bg-tertiary)', borderRadius: '12px', border: '1px solid var(--border-subtle)', padding: '20px', maxHeight: '500px', display: 'flex', flexDirection: 'column' }}>
          <h2 style={{ fontSize: '13px', fontWeight: '900', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', margin: '0 0 12px 0' }}>
            📦 Deliverables ({deliverables.length} employees)
          </h2>
          {deliverables.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontSize: '12px', fontStyle: 'italic' }}>
              {finalResult ? 'No file deliverables recorded.' : 'Waiting for employee outputs...'}
            </div>
          ) : (
            <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {deliverables.map((emp, empIdx) => {
                const deptColor = getDeptColor(emp.department);
                return (
                  <div key={empIdx} style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '10px', padding: '14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                      <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: deptColor }} />
                      <span style={{ fontSize: '12px', fontWeight: '700', color: 'white' }}>{emp.employee_name}</span>
                      <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{emp.handle}</span>
                      {emp.department && (
                        <span style={{ fontSize: '9px', padding: '2px 6px', borderRadius: '4px', background: `${deptColor}22`, color: deptColor, fontWeight: '700', marginLeft: 'auto' }}>
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
                                <button
                                  onClick={() => toggleFile(emp.handle, file.filename)}
                                  style={{
                                    background: 'rgba(59,130,246,0.15)', color: '#60a5fa', border: 'none', borderRadius: '4px',
                                    padding: '3px 10px', fontSize: '10px', fontWeight: '700', cursor: 'pointer'
                                  }}
                                >
                                  {isExpanded ? 'Hide' : 'View'}
                                </button>
                                <button
                                  onClick={() => copyToClipboard(file.content, fileKey)}
                                  style={{
                                    background: copiedKey === fileKey ? 'rgba(16,185,129,0.15)' : 'rgba(255,255,255,0.06)',
                                    color: copiedKey === fileKey ? '#10b981' : 'var(--text-muted)',
                                    border: 'none', borderRadius: '4px', padding: '3px 10px', fontSize: '10px', fontWeight: '700', cursor: 'pointer'
                                  }}
                                >
                                  {copiedKey === fileKey ? '✓ Copied' : 'Copy'}
                                </button>
                              </>
                            )}
                          </div>
                          {isExpanded && file.content && (
                            <pre style={{
                              fontFamily: 'var(--font-mono)', fontSize: '12px', overflowX: 'auto', whiteSpace: 'pre',
                              background: 'rgba(0,0,0,0.4)', padding: '16px', borderRadius: '8px', maxHeight: '400px',
                              overflowY: 'auto', color: '#e2e8f0', margin: '6px 0 0 0', border: '1px solid rgba(255,255,255,0.05)'
                            }}>
                              {file.content}
                            </pre>
                          )}
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* SECTION 4 — FILE TREE + DOWNLOAD ALL */}
        {finalResult && (
          <div style={{ background: 'var(--bg-tertiary)', borderRadius: '12px', border: '1px solid var(--border-subtle)', padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <h2 style={{ fontSize: '13px', fontWeight: '900', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', margin: 0 }}>
                🗂️ All Produced Files
              </h2>
              <button
                onClick={handleDownloadAll}
                style={{
                  background: 'linear-gradient(135deg, #3b82f6, #6366f1)', color: 'white', border: 'none',
                  borderRadius: '8px', padding: '8px 20px', fontSize: '12px', fontWeight: '700', cursor: 'pointer',
                  boxShadow: '0 2px 8px rgba(59,130,246,0.3)', transition: 'transform 0.15s',
                }}
                onMouseEnter={e => e.target.style.transform = 'scale(1.03)'}
                onMouseLeave={e => e.target.style.transform = 'scale(1)'}
              >
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
        )}

        {/* Final Output Text */}
        {finalResult?.result && (
          <div style={{ background: 'var(--bg-tertiary)', borderRadius: '12px', border: '1px solid var(--border-subtle)', padding: '24px' }}>
            <h2 style={{ fontSize: '13px', fontWeight: '900', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', margin: '0 0 12px 0' }}>📝 Aggregated Output</h2>
            <div style={{
              background: 'rgba(0,0,0,0.3)', padding: '20px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)',
              maxHeight: '500px', overflowY: 'auto'
            }}>
              <MarkdownRenderer content={finalResult.result} />
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
