import React, { useMemo, useEffect } from 'react';
import { ReactFlow, useNodesState, useEdgesState, Background, Controls, Handle, Position } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

/* ── Color palette per agent type ─────────────────────────────── */
const COLOR_MAP = {
  CEO:        { bg: '#d095ff', border: '#b26ef7', text: '#f3e8ff', glow: 'rgba(178,110,247,0.6)' },
  Executive:  { bg: '#40cef3', border: '#25b6e0', text: '#e0f7fe', glow: 'rgba(37,182,224,0.6)' },
  Department: { bg: '#ffa44c', border: '#f59e0b', text: '#fff7ed', glow: 'rgba(245,158,11,0.6)' },
  Employee:   { bg: '#10b981', border: '#059669', text: '#ecfdf5', glow: 'rgba(16,185,129,0.4)' },
};

const ICONS = { CEO: '👑', Executive: '🎯', Department: '🏢', Employee: '⚙️' };

/* ── Custom node renderer ── */
const AgentNode = ({ data }) => {
  const isActive = data.status === 'in_progress' || data.status === 'working';
  const colors = COLOR_MAP[data.agentType] || COLOR_MAP.Employee;

  return (
    <div
      style={{
        background: isActive ? colors.bg : 'rgba(30, 35, 45, 0.4)',
        borderColor: isActive ? colors.border : 'rgba(255, 255, 255, 0.1)',
        color: isActive ? '#fff' : 'rgba(255, 255, 255, 0.6)',
        boxShadow: isActive ? `0 0 30px ${colors.glow}, 0 10px 20px rgba(0,0,0,0.5)` : 'none',
        transition: 'all 0.5s cubic-bezier(0.16, 1, 0.3, 1)',
        borderWidth: '2px',
        borderStyle: 'solid',
        width: '200px',
        padding: '16px',
        borderRadius: '16px',
        backdropFilter: 'blur(10px)',
        textAlign: 'center',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '8px'
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: 'transparent', border: 'none' }} />
      <Handle type="source" position={Position.Bottom} style={{ background: 'transparent', border: 'none' }} />

      <div style={{ 
        position: 'absolute', top: '-10px', left: '50%', transform: 'translateX(-50%)',
        background: isActive ? '#fff' : colors.bg,
        color: isActive ? colors.bg : '#fff',
        padding: '2px 8px', borderRadius: '4px', fontSize: '8px', fontWeight: '900',
        letterSpacing: '0.1em', boxShadow: isActive ? `0 2px 8px ${colors.glow}` : 'none'
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
          animation: isActive ? 'pulse 2s infinite' : 'none'
        }} />
        <div style={{ fontSize: '9px', fontWeight: '900', opacity: 0.8, letterSpacing: '0.05em' }}>
          {isActive ? 'WORKING' : 'AVAILABLE'}
        </div>
      </div>
    </div>
  );
};

const nodeTypes = { agentNode: AgentNode };

export default function AgentFlowGraph({ logs, staticTree, activeAgents = {} }) {
  // Initialize with baseline hierarchy if available to prevent flash of empty state
  const initialNodes = useMemo(() => {
    if (!staticTree || !staticTree.executives) return [];
    return staticTree.executives.map((exec, idx) => ({
      id: `exec_${exec.handle}`,
      type: 'agentNode',
      data: { agentType: 'Executive', agentName: exec.name, status: 'idle' },
      position: { x: idx * 250 - ((staticTree.executives.length - 1) * 250) / 2, y: 0 }
    }));
  }, []);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Helper: check if an agent is actively working (not just present in the map)
  const isAgentWorking = (identifiers) => {
    // identifiers is an array of strings to match against activeAgents keys
    for (const [key, value] of Object.entries(activeAgents)) {
      if (value?.status !== 'working') continue;
      const keyLower = key.toLowerCase();
      for (const id of identifiers) {
        if (keyLower === id.toLowerCase()) return true;
      }
    }
    return false;
  };

  useEffect(() => {
    // ── Mode 1: Static Org Chart Tree (Always Priority) ──
    if (staticTree && staticTree.executives) {
      const newNodes = [];
      const newEdges = [];
      
      const STRATEGOS_Y = 0;
      const EXEC_Y = 250;
      const DEPT_Y = 530;
      const EMP_Y = 750;
      const DEPT_SPACING = 600;
      const EXEC_SPACING = 250;

      const allExecutives = staticTree.executives || [];

      // Separate Strategos (Strategy Planner) from operational executives
      const strategos = allExecutives.find(e => e.handle === '@executive' || e.name === 'Strategos');
      const operationalExecs = allExecutives.filter(e => e.handle !== '@executive' && e.name !== 'Strategos');

      // Map department keys to their responsible executive handle
      const DEPT_EXEC_MAP = {
        'IT': '@cto',
        'Marketing': '@cmo',
        'Operations': '@coo',
        'Finance': '@cfo',
        'HR': '@chro',
        'Customer Service': '@coo',
      };

      // ─── PHASE 1: Pre-compute bottom-up activity ───────────────
      // CEO/Executive complete in milliseconds (no LLM), so they're always
      // "idle" by the time we render. Instead, propagate activity UPWARD:
      // if any employee/dept is working → its parent exec & Strategos glow too.

      const activeDepts = new Set();     // dept keys with active employees or self
      const activeExecHandles = new Set(); // exec handles that should glow

      // Check each department and its employees
      (staticTree.departments || []).forEach((dept) => {
        const deptActive = isAgentWorking([dept.key, dept.head_name]);
        let anyEmpActive = false;

        (dept.employees || []).forEach((emp) => {
          if (isAgentWorking([emp.handle, emp.name])) {
            anyEmpActive = true;
          }
        });

        if (deptActive || anyEmpActive) {
          activeDepts.add(dept.key);
          // Propagate up: light up the responsible executive
          const execHandle = DEPT_EXEC_MAP[dept.key] || '@coo';
          activeExecHandles.add(execHandle);
        }
      });

      // If ANY agent in the pipeline is working, Strategos should glow
      const anyPipelineActive = activeDepts.size > 0 
        || isAgentWorking(['CEO', 'Nova CEO', 'Strategy Planner', 'strategy_planner']);

      // ─── PHASE 2: Build nodes with propagated status ───────────

      // 0. Level 0: Strategos
      if (strategos) {
        const strategosId = `exec_${strategos.handle}`;

        newNodes.push({
          id: strategosId,
          type: 'agentNode',
          data: {
            agentType: 'CEO',
            agentName: strategos.name,
            status: anyPipelineActive ? 'in_progress' : 'idle'
          },
          position: { x: 0, y: STRATEGOS_Y }
        });

        // Edges from Strategos to every operational executive
        operationalExecs.forEach((exec) => {
          const execId = `exec_${exec.handle}`;
          const isActive = anyPipelineActive || activeExecHandles.has(exec.handle);

          newEdges.push({
            id: `e-strategos-${execId}`,
            source: strategosId,
            target: execId,
            animated: isActive,
            style: {
              stroke: isActive ? '#d095ff' : 'rgba(255, 255, 255, 0.08)',
              strokeWidth: isActive ? 2.5 : 1.5,
              filter: isActive ? 'drop-shadow(0 0 6px rgba(208,149,255,0.5))' : 'none'
            }
          });
        });
      }

      // 1. Level 1: Operational Executives
      const execStartX = -((operationalExecs.length - 1) * EXEC_SPACING) / 2;
      
      operationalExecs.forEach((exec, idx) => {
        const execId = `exec_${exec.handle}`;
        // Active if: propagated from department OR directly logged
        const execActive = activeExecHandles.has(exec.handle)
          || isAgentWorking([exec.handle, exec.name]);
        
        newNodes.push({
          id: execId,
          type: 'agentNode',
          data: { 
            agentType: 'Executive', 
            agentName: exec.name, 
            status: execActive ? 'in_progress' : 'idle' 
          },
          position: { x: execStartX + idx * EXEC_SPACING, y: EXEC_Y }
        });
      });

      // 2. Level 2: Departments
      let currentDeptX = -((staticTree.departments.length - 1) * DEPT_SPACING) / 2;

      staticTree.departments.forEach((dept) => {
        const deptId = `dept_${dept.key}`;
        const deptActive = activeDepts.has(dept.key);
        const deptStatus = deptActive ? 'in_progress' : 'idle';
        
        newNodes.push({
          id: deptId,
          type: 'agentNode',
          data: { 
            agentType: 'Department', 
            agentName: dept.head_name, 
            status: deptStatus
          },
          position: { x: currentDeptX, y: DEPT_Y }
        });

        // Connect department to its responsible executive
        const responsibleExec = DEPT_EXEC_MAP[dept.key] || '@coo';
        const execNodeId = `exec_${responsibleExec}`;
        newEdges.push({
          id: `e-exec-${deptId}`,
          source: execNodeId,
          target: deptId,
          animated: deptActive,
          style: { 
            stroke: deptActive ? '#c782ff' : 'rgba(255, 255, 255, 0.05)', 
            strokeWidth: deptActive ? 3 : 1.5,
            filter: deptActive ? 'drop-shadow(0 0 5px #c782ff)' : 'none'
          }
        });

        // 3. Level 3: Employees
        const deptEmployees = dept.employees || [];
        deptEmployees.forEach((emp, empIdx) => {
          const empId = `emp_${emp.handle}`;
          const isEmpActive = isAgentWorking([emp.handle, emp.name]);
          
          const cols = 2;
          const col = empIdx % cols;
          const row = Math.floor(empIdx / cols);

          newNodes.push({
            id: empId,
            type: 'agentNode',
            data: { 
              agentType: 'Employee', 
              agentName: emp.name, 
              status: isEmpActive ? 'in_progress' : 'idle' 
            },
            position: { 
              x: currentDeptX + (col - (cols-1)/2) * 220, 
              y: EMP_Y + row * 150 
            }
          });

          newEdges.push({
            id: `e-${deptId}-${empId}`,
            source: deptId,
            target: empId,
            animated: isEmpActive,
            style: { 
              stroke: isEmpActive ? '#c782ff' : 'rgba(255, 255, 255, 0.03)', 
              strokeWidth: isEmpActive ? 2.5 : 1,
              opacity: isEmpActive ? 1 : 0.4
            }
          });
        });

        currentDeptX += DEPT_SPACING;
      });

      setNodes(newNodes);
      setEdges(newEdges);
      return;
    }

    // ── Mode 2: Dynamic Execution Logs ──
    if (logs && logs.length > 0) {
      const nodeMap = new Map();
      const dynamicEdges = [];

      logs.forEach((log) => {
        const id = log.agent_name;
        if (!nodeMap.has(id)) {
          nodeMap.set(id, {
            id,
            type: 'agentNode',
            data: { agentType: log.agent, agentName: id, status: log.status },
            position: { x: 0, y: 0 },
          });
        } else {
          nodeMap.get(id).data.status = log.status;
        }
      });

      const cols = [[], [], [], []];
      const LAYER_MAP = { CEO: 0, Executive: 1, Department: 2, Employee: 3 };
      
      Array.from(nodeMap.values()).forEach(node => {
        const layer = LAYER_MAP[node.data.agentType] ?? 3;
        cols[layer].push(node);
      });

      const finalNodes = [];
      cols.forEach((col, xIdx) => {
        const startY = -(col.length * 150) / 2;
        col.forEach((node, yIdx) => {
          node.position = { x: xIdx * 300, y: startY + yIdx * 150 };
          finalNodes.push(node);
        });
      });

      let lastAgent = null;
      logs.forEach(log => {
        if (lastAgent && lastAgent !== log.agent_name && log.status === 'started') {
          dynamicEdges.push({
            id: `de-${lastAgent}-${log.agent_name}`,
            source: lastAgent,
            target: log.agent_name,
            animated: true,
            style: { stroke: '#fbbf24', strokeWidth: 2 }
          });
        }
        lastAgent = log.agent_name;
      });

      setNodes(finalNodes);
      setEdges(dynamicEdges);
    }
  }, [logs, staticTree, activeAgents, setNodes, setEdges]);

  return (
    <div style={{ width: '100%', height: '100%', minHeight: '650px', background: 'transparent' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background color="rgba(208, 149, 255, 0.15)" gap={40} size={1} />
        <Controls 
          style={{ 
            background: 'rgba(30, 35, 45, 0.8)', 
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '8px'
          }} 
        />
        {(nodes.length === 0) && (
          <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center', opacity: 0.6 }}>
            <p style={{ fontSize: '14px', fontWeight: '900', color: '#d095ff', letterSpacing: '0.2em' }}>NEXUS ARCHITECTURE SYNCING...</p>
            <p style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)' }}>Assembling organizational hierarchy nodes</p>
          </div>
        )}
        <div style={{ position: 'absolute', bottom: '10px', left: '10px', fontSize: '9px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          NODES: {nodes.length} | EDGES: {edges.length}
        </div>
      </ReactFlow>
    </div>
  );
}
