/**
 * AgentFlowGraph
 * Fix #8: Node/edge layout computed ONCE from staticTree (useMemo).
 *         Only node data.status is patched on each activeAgents change,
 *         preventing a full re-layout on every incoming token.
 */
import React, { useMemo, useEffect, useCallback } from 'react';
import { ReactFlow, useNodesState, useEdgesState, Background, Controls, Handle, Position } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

const COLOR_MAP = {
  CEO:        { bg: '#d095ff', border: '#b26ef7', text: '#f3e8ff', glow: 'rgba(178,110,247,0.6)' },
  Executive:  { bg: '#40cef3', border: '#25b6e0', text: '#e0f7fe', glow: 'rgba(37,182,224,0.6)' },
  Department: { bg: '#ffa44c', border: '#f59e0b', text: '#fff7ed', glow: 'rgba(245,158,11,0.6)' },
  Employee:   { bg: '#10b981', border: '#059669', text: '#ecfdf5', glow: 'rgba(16,185,129,0.4)' },
};
const ICONS = { CEO: '👑', Executive: '🎯', Department: '🏢', Employee: '⚙️' };

const AgentNode = ({ data }) => {
  const isActive = data.status === 'in_progress' || data.status === 'working';
  const colors   = COLOR_MAP[data.agentType] || COLOR_MAP.Employee;
  return (
    <div style={{
      background:   isActive ? colors.bg : 'rgba(30,35,45,0.4)',
      borderColor:  isActive ? colors.border : 'rgba(255,255,255,0.1)',
      color:        isActive ? '#fff' : 'rgba(255,255,255,0.6)',
      boxShadow:    isActive ? `0 0 30px ${colors.glow}, 0 10px 20px rgba(0,0,0,0.5)` : 'none',
      transition:   'all 0.5s cubic-bezier(0.16,1,0.3,1)',
      borderWidth: '2px', borderStyle: 'solid',
      width: '200px', padding: '16px', borderRadius: '16px',
      backdropFilter: 'blur(10px)', textAlign: 'center',
      position: 'relative', display: 'flex', flexDirection: 'column',
      alignItems: 'center', gap: '8px',
    }}>
      <Handle type="target" position={Position.Top}    style={{ background: 'transparent', border: 'none' }} />
      <Handle type="source" position={Position.Bottom} style={{ background: 'transparent', border: 'none' }} />
      <div style={{
        position: 'absolute', top: '-10px', left: '50%', transform: 'translateX(-50%)',
        background: isActive ? '#fff' : colors.bg,
        color:      isActive ? colors.bg : '#fff',
        padding: '2px 8px', borderRadius: '4px', fontSize: '8px', fontWeight: '900',
        letterSpacing: '0.1em', boxShadow: isActive ? `0 2px 8px ${colors.glow}` : 'none',
      }}>
        {data.agentType}
      </div>
      <div style={{ fontSize: '24px' }}>{ICONS[data.agentType] || '🔹'}</div>
      <div style={{ fontSize: '13px', fontWeight: '800', width: '100%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {data.agentName}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <div style={{
          width: '6px', height: '6px', borderRadius: '50%',
          background: isActive ? '#fff' : colors.border,
          animation: isActive ? 'pulse 2s infinite' : 'none',
        }} />
        <div style={{ fontSize: '9px', fontWeight: '900', opacity: 0.8, letterSpacing: '0.05em' }}>
          {isActive ? 'WORKING' : 'AVAILABLE'}
        </div>
      </div>
    </div>
  );
};

const nodeTypes = { agentNode: AgentNode };

const DEPT_EXEC_MAP = {
  'IT': '@cto', 'Marketing': '@cmo', 'Operations': '@coo',
  'Finance': '@cfo', 'HR': '@chro', 'Customer Service': '@coo',
};

// ── Fix #8: build layout ONCE from staticTree ─────────────────────────────
function buildStaticLayout(staticTree) {
  if (!staticTree?.executives) return { nodes: [], edges: [] };

  const nodes = [];
  const edges = [];

  const STRATEGOS_Y  = 0;
  const EXEC_Y       = 250;
  const DEPT_Y       = 530;
  const EMP_Y        = 750;
  const DEPT_SPACING = 600;
  const EXEC_SPACING = 250;

  const allExecs     = staticTree.executives || [];
  const strategos    = allExecs.find(e => e.handle === '@executive' || e.name === 'Strategos');
  const opExecs      = allExecs.filter(e => e !== strategos);

  if (strategos) {
    nodes.push({
      id: `exec_${strategos.handle}`, type: 'agentNode',
      data: { agentType: 'CEO', agentName: strategos.name, status: 'idle' },
      position: { x: 0, y: STRATEGOS_Y },
    });
    opExecs.forEach(exec => {
      edges.push({
        id: `e-strat-exec_${exec.handle}`,
        source: `exec_${strategos.handle}`, target: `exec_${exec.handle}`,
        animated: false,
        style: { stroke: 'rgba(255,255,255,0.08)', strokeWidth: 1.5 },
      });
    });
  }

  const execStartX = -((opExecs.length - 1) * EXEC_SPACING) / 2;
  opExecs.forEach((exec, idx) => {
    nodes.push({
      id: `exec_${exec.handle}`, type: 'agentNode',
      data: { agentType: 'Executive', agentName: exec.name, status: 'idle' },
      position: { x: execStartX + idx * EXEC_SPACING, y: EXEC_Y },
    });
  });

  let deptX = -((staticTree.departments.length - 1) * DEPT_SPACING) / 2;
  (staticTree.departments || []).forEach(dept => {
    const deptId = `dept_${dept.key}`;
    nodes.push({
      id: deptId, type: 'agentNode',
      data: { agentType: 'Department', agentName: dept.head_name, status: 'idle' },
      position: { x: deptX, y: DEPT_Y },
    });
    const execId = `exec_${DEPT_EXEC_MAP[dept.key] || '@coo'}`;
    edges.push({
      id: `e-exec-${deptId}`, source: execId, target: deptId,
      animated: false,
      style: { stroke: 'rgba(255,255,255,0.05)', strokeWidth: 1.5 },
    });

    (dept.employees || []).forEach((emp, empIdx) => {
      const empId = `emp_${emp.handle}`;
      const col   = empIdx % 2;
      const row   = Math.floor(empIdx / 2);
      nodes.push({
        id: empId, type: 'agentNode',
        data: { agentType: 'Employee', agentName: emp.name, status: 'idle' },
        position: { x: deptX + (col - 0.5) * 220, y: EMP_Y + row * 150 },
      });
      edges.push({
        id: `e-${deptId}-${empId}`, source: deptId, target: empId,
        animated: false,
        style: { stroke: 'rgba(255,255,255,0.03)', strokeWidth: 1, opacity: 0.4 },
      });
    });
    deptX += DEPT_SPACING;
  });

  return { nodes, edges };
}

export default function AgentFlowGraph({ logs, staticTree, activeAgents = {} }) {
  // ── Fix #8: layout computed once ────────────────────────────────────────
  const { nodes: layoutNodes, edges: layoutEdges } = useMemo(
    () => buildStaticLayout(staticTree),
    [staticTree]   // only recompute if the org-chart structure changes
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(layoutNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutEdges);

  // Sync layout when staticTree first loads
  useEffect(() => {
    if (layoutNodes.length > 0) {
      setNodes(layoutNodes);
      setEdges(layoutEdges);
    }
  }, [layoutNodes, layoutEdges, setNodes, setEdges]);

  // Helper: is agent currently working?
  const isWorking = useCallback((identifiers) => {
    for (const [key, value] of Object.entries(activeAgents)) {
      if (value?.status !== 'working') continue;
      const kl = key.toLowerCase();
      if (identifiers.some(id => id.toLowerCase() === kl)) return true;
    }
    return false;
  }, [activeAgents]);

  // ── Fix #8: only patch data.status, never rebuild layout ────────────────
  useEffect(() => {
    if (!staticTree?.executives || layoutNodes.length === 0) return;

    const activeDepts      = new Set();
    const activeExecHandles = new Set();

    (staticTree.departments || []).forEach(dept => {
      const deptActive = isWorking([dept.key, dept.head_name]);
      const empActive  = (dept.employees || []).some(e => isWorking([e.handle, e.name]));
      if (deptActive || empActive) {
        activeDepts.add(dept.key);
        activeExecHandles.add(DEPT_EXEC_MAP[dept.key] || '@coo');
      }
    });

    const anyActive = activeDepts.size > 0
      || isWorking(['CEO', 'Nova CEO', 'Strategy Planner', 'strategy_planner']);

    setNodes(prev => prev.map(node => {
      let status = 'idle';

      if (node.data.agentType === 'CEO') {
        status = anyActive ? 'in_progress' : 'idle';
      } else if (node.data.agentType === 'Executive') {
        const handle = node.id.replace('exec_', '');
        status = (anyActive || activeExecHandles.has(handle) || isWorking([handle, node.data.agentName]))
          ? 'in_progress' : 'idle';
      } else if (node.data.agentType === 'Department') {
        const deptKey = node.id.replace('dept_', '');
        status = activeDepts.has(deptKey) ? 'in_progress' : 'idle';
      } else if (node.data.agentType === 'Employee') {
        status = isWorking([node.id.replace('emp_', ''), node.data.agentName])
          ? 'in_progress' : 'idle';
      }

      // Only return a new object if status actually changed (avoids React re-renders)
      if (node.data.status === status) return node;
      return { ...node, data: { ...node.data, status } };
    }));

    // Patch edge animation to match active nodes
    setEdges(prev => prev.map(edge => {
      const targetNode = layoutNodes.find(n => n.id === edge.target);
      if (!targetNode) return edge;

      const tDept = targetNode.id.startsWith('dept_') && activeDepts.has(targetNode.id.replace('dept_', ''));
      const tEmp  = targetNode.id.startsWith('emp_')  && isWorking([targetNode.id.replace('emp_', ''), targetNode.data?.agentName]);
      const active = tDept || tEmp || anyActive;

      const newStyle = active
        ? { stroke: '#c782ff', strokeWidth: tEmp ? 2.5 : 3, filter: 'drop-shadow(0 0 5px #c782ff)' }
        : { stroke: 'rgba(255,255,255,0.05)', strokeWidth: 1.5 };

      if (edge.animated === active && JSON.stringify(edge.style) === JSON.stringify(newStyle)) return edge;
      return { ...edge, animated: active, style: newStyle };
    }));
  }, [activeAgents, isWorking, staticTree, layoutNodes, setNodes, setEdges]);

  // ── Fallback: dynamic log-based layout when no staticTree ────────────────
  useEffect(() => {
    if (staticTree?.executives || !logs?.length) return;

    const nodeMap = new Map();
    const dynEdges = [];
    logs.forEach(log => {
      const id = log.agent_name;
      if (!nodeMap.has(id)) {
        nodeMap.set(id, { id, type: 'agentNode',
          data: { agentType: log.agent, agentName: id, status: log.status },
          position: { x: 0, y: 0 } });
      } else {
        nodeMap.get(id).data.status = log.status;
      }
    });

    const cols = [[], [], [], []];
    const LAYER = { CEO: 0, Executive: 1, Department: 2, Employee: 3 };
    nodeMap.forEach(n => cols[LAYER[n.data.agentType] ?? 3].push(n));
    const finalNodes = [];
    cols.forEach((col, xIdx) => {
      const startY = -(col.length * 150) / 2;
      col.forEach((n, yIdx) => { n.position = { x: xIdx * 300, y: startY + yIdx * 150 }; finalNodes.push(n); });
    });
    let last = null;
    logs.forEach(log => {
      if (last && last !== log.agent_name && log.status === 'started') {
        dynEdges.push({ id: `de-${last}-${log.agent_name}`, source: last, target: log.agent_name,
          animated: true, style: { stroke: '#fbbf24', strokeWidth: 2 } });
      }
      last = log.agent_name;
    });
    setNodes(finalNodes);
    setEdges(dynEdges);
  }, [logs, staticTree, setNodes, setEdges]);

  return (
    <div style={{ width: '100%', height: '100%', minHeight: '650px', background: 'transparent' }}>
      <ReactFlow
        nodes={nodes} edges={edges}
        onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView proOptions={{ hideAttribution: true }}
      >
        <Background color="rgba(208,149,255,0.15)" gap={40} size={1} />
        <Controls style={{ background: 'rgba(30,35,45,0.8)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }} />
        {nodes.length === 0 && (
          <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', textAlign: 'center', opacity: 0.6 }}>
            <p style={{ fontSize: '14px', fontWeight: '900', color: '#d095ff', letterSpacing: '0.2em' }}>NEXUS ARCHITECTURE SYNCING...</p>
            <p style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)' }}>Assembling organizational hierarchy</p>
          </div>
        )}
        <div style={{ position: 'absolute', bottom: '10px', left: '10px', fontSize: '9px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          NODES: {nodes.length} | EDGES: {edges.length}
        </div>
      </ReactFlow>
    </div>
  );
}
