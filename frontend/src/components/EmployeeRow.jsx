import React, { useState } from 'react';

/**
 * EmployeeRow — A premium, high-fidelity table row component for the department manifest.
 * Integrated with LLM dynamic selection and operational status tracking.
 */
export default function EmployeeRow({ 
  emp, 
  isEmpActiveStr, 
  activeAgents, 
  isDisabled, 
  onToggle, 
  onChangeLLM 
}) {
  const [modelVal, setModelVal] = useState(emp.assigned_model || 'auto');
  const [isHovered, setIsHovered] = useState(false);

  // Determine if agent is currently working based on the global activeState
  const activeState = isEmpActiveStr ? activeAgents[isEmpActiveStr] : null;
  const isWorking = activeState?.status === 'working';

  // Handle model change locally then notify parent
  const handleModelChange = (e) => {
    const val = e.target.value;
    setModelVal(val);
    onChangeLLM(emp.handle, val);
  };

  const getStatusColor = () => {
    if (isDisabled) return '#64748b'; // Disabled
    if (isWorking) return '#10b981';  // Working
    return '#40cef3';                  // Available/Idle
  };

  return (
      <div 
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(180px, 1.2fr) 1.1fr 1.8fr 1.2fr 1.4fr 1fr 100px',
          alignItems: 'center',
          padding: '16px 24px',
          background: isHovered ? 'rgba(255, 255, 255, 0.03)' : 'transparent',
          border: `1px solid ${isHovered ? 'rgba(255, 255, 255, 0.08)' : 'rgba(255, 255, 255, 0.03)'}`,
          borderRadius: 'var(--radius-lg)',
          transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
          opacity: isDisabled ? 0.5 : 1,
          position: 'relative',
          overflow: 'hidden'
        }}
      >
        {/* ── Level Accent ── */}
        <div style={{
          position: 'absolute',
          left: 0,
          top: 0,
          bottom: 0,
          width: '3px',
          background: getStatusColor(),
          opacity: isWorking || isHovered ? 1 : 0.2,
          transition: 'all 0.2s'
        }} />
 
        {/* ── Employee Profile ── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ 
            width: '36px', 
            height: '36px', 
            borderRadius: '12px', 
            background: isWorking ? 'rgba(16, 185, 129, 0.1)' : 'rgba(255, 255, 255, 0.05)',
            border: `1px solid ${isWorking ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.1)'}`,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            fontSize: '14px',
            fontWeight: '800',
            color: isWorking ? '#10b981' : 'var(--text-secondary)'
          }}>
            {emp.name.charAt(0)}
          </div>
          <div>
            <div style={{ fontSize: '14px', fontWeight: '700', color: 'white' }}>{emp.name}</div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>{emp.handle}</div>
          </div>
        </div>
 
        {/* ── Role ── */}
        <div style={{ fontSize: '13px', color: 'var(--text-secondary)', fontWeight: '600' }}>
          {emp.role}
        </div>
 
        {/* ── Current Task ── */}
        <div style={{ paddingRight: '12px' }}>
          {isWorking ? (
            <div title={activeState?.task} style={{ fontSize: '11px', color: '#10b981', background: 'rgba(16, 185, 129, 0.05)', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(16, 185, 129, 0.1)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              <span style={{ fontWeight: 800, marginRight: '6px' }}>▶</span>
              {activeState?.task || 'Processing operation...'}
            </div>
          ) : (
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', padding: '6px 10px' }}>
              System idle
            </div>
          )}
        </div>

        {/* ── Active Engine (NEW) ── */}
        <div style={{ paddingRight: '12px' }}>
           {isWorking ? (
             <div style={{ 
               fontSize: '10px', 
               color: 'white', 
               fontFamily: 'var(--font-mono)', 
               background: 'var(--bg-tertiary)', 
               padding: '4px 8px', 
               borderRadius: '4px', 
               border: '1px solid var(--border-subtle)',
               display: 'inline-block',
               maxWidth: '120px',
               overflow: 'hidden',
               textOverflow: 'ellipsis',
               whiteSpace: 'nowrap'
             }}>
               {activeState?.model?.split('/').pop() || 'Processing...'}
             </div>
           ) : (
             <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>—</span>
           )}
        </div>
 
        {/* ── LLM Model Preference ── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <select 
            value={modelVal} 
            onChange={handleModelChange}
            disabled={isDisabled}
            style={{
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '6px 10px',
              fontSize: '11px',
              color: 'white',
              fontFamily: 'var(--font-mono)',
              outline: 'none',
              cursor: 'pointer',
              transition: 'border-color 0.2s',
              width: '100%',
              maxWidth: '160px'
            }}
            onFocus={e => e.target.style.borderColor = 'var(--color-ceo)'}
            onBlur={e => e.target.style.borderColor = 'var(--border-subtle)'}
          >
            <option value="auto">Auto (UCB-1)</option>
            <option value="meta-llama/llama-3.3-70b-instruct">Llama 3.3 70B</option>
            <option value="meta-llama/llama-3.2-3b-instruct">Llama 3.2 3B</option>
            <option value="qwen/qwen3-coder">Qwen 3 Coder</option>
            <option value="qwen/qwen3-next-80b-a3b-instruct">Qwen 3 Next 80B</option>
            <option value="google/gemma-3-27b-it">Gemma 3 27B</option>
            <option value="google/gemma-3-4b-it">Gemma 3 4B</option>
            <option value="nousresearch/hermes-3-llama-3.1-405b">Hermes 3 (405B)</option>
            <option value="nvidia/nemotron-nano-9b-v2">Nemotron 9B</option>
            <option value="nvidia/nemotron-3-super-120b-a12b">Nemotron 120B</option>
          </select>
        </div>
  
        {/* ── Operational Status ── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ 
            width: '6px', 
            height: '6px', 
            borderRadius: '50%', 
            background: getStatusColor(),
            boxShadow: isWorking ? '0 0 10px #10b981' : 'none'
          }} />
          <span style={{ 
            fontSize: '10px', 
            fontWeight: '900', 
            textTransform: 'uppercase', 
            letterSpacing: '0.1em', 
            color: getStatusColor() 
          }}>
            {isDisabled ? 'Off' : isWorking ? 'Working' : 'Idle'}
          </span>
        </div>


      {/* ── Action: Toggle ── */}
      <div style={{ textAlign: 'right' }}>
        <button 
          onClick={() => onToggle(emp.handle)}
          style={{
            background: isDisabled ? 'rgba(255, 255, 255, 0.05)' : 'rgba(208, 149, 255, 0.05)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            padding: '6px 12px',
            fontSize: '10px',
            fontWeight: '800',
            color: isDisabled ? 'var(--text-muted)' : 'var(--color-ceo)',
            cursor: 'pointer',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            transition: 'all 0.2s'
          }}
          onMouseOver={e => {
            if (!isDisabled) e.currentTarget.style.background = 'rgba(208, 149, 255, 0.15)';
          }}
          onMouseOut={e => {
            if (!isDisabled) e.currentTarget.style.background = 'rgba(208, 149, 255, 0.05)';
          }}
        >
          {isDisabled ? 'Enable' : 'Disable'}
        </button>
      </div>
    </div>
  );
}
