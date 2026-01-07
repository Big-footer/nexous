/**
 * Run Console Component
 * 실행 상태 표시 및 폴링
 */

import React, { useState, useEffect, useRef } from 'react';

const styles = {
  container: {
    padding: '16px',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    marginBottom: '16px',
  },
  runId: {
    fontSize: '14px',
    color: '#888',
    marginBottom: '8px',
  },
  status: {
    fontSize: '24px',
    fontWeight: 'bold',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  statusDot: {
    width: '12px',
    height: '12px',
    borderRadius: '50%',
  },
  running: {
    background: '#ff9800',
    animation: 'pulse 1s infinite',
  },
  completed: {
    background: '#4CAF50',
  },
  failed: {
    background: '#f44336',
  },
  summary: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '16px',
    marginTop: '24px',
  },
  summaryCard: {
    background: '#252540',
    padding: '16px',
    borderRadius: '8px',
    textAlign: 'center',
  },
  summaryValue: {
    fontSize: '28px',
    fontWeight: 'bold',
    color: '#4a9eff',
  },
  summaryLabel: {
    fontSize: '12px',
    color: '#888',
    marginTop: '4px',
  },
  timeline: {
    flex: 1,
    marginTop: '24px',
    overflowY: 'auto',
  },
  timelineItem: {
    display: 'flex',
    alignItems: 'center',
    padding: '12px',
    background: '#252540',
    borderRadius: '8px',
    marginBottom: '8px',
  },
  agentIcon: {
    width: '40px',
    height: '40px',
    borderRadius: '50%',
    background: '#4a9eff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: '12px',
    fontSize: '18px',
  },
  agentInfo: {
    flex: 1,
  },
  agentName: {
    fontWeight: 'bold',
  },
  agentPurpose: {
    fontSize: '12px',
    color: '#888',
  },
  agentStatus: {
    padding: '4px 12px',
    borderRadius: '12px',
    fontSize: '12px',
    fontWeight: 'bold',
  },
  empty: {
    textAlign: 'center',
    color: '#666',
    padding: '48px',
  },
};

const STATUS_COLORS = {
  COMPLETED: '#4CAF50',
  FAILED: '#f44336',
  RUNNING: '#ff9800',
  IDLE: '#666',
};

const PRESET_ICONS = {
  planner: '📋',
  executor: '⚡',
  analyst: '📊',
  writer: '✍️',
};

export default function RunConsole({ projectId, runId, trace, onPoll }) {
  const [polling, setPolling] = useState(false);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (runId && trace?.status === 'RUNNING') {
      setPolling(true);
      intervalRef.current = setInterval(() => {
        onPoll();
      }, 1000);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [runId, trace?.status]);

  useEffect(() => {
    if (trace?.status === 'COMPLETED' || trace?.status === 'FAILED') {
      setPolling(false);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    }
  }, [trace?.status]);

  if (!runId) {
    return (
      <div style={styles.empty}>
        Click "Run" to start execution
      </div>
    );
  }

  const summary = trace?.summary || {};
  const agents = trace?.agents || [];

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.runId}>Run: {runId}</div>
        <div style={styles.status}>
          <span
            style={{
              ...styles.statusDot,
              ...(trace?.status === 'RUNNING' ? styles.running :
                  trace?.status === 'COMPLETED' ? styles.completed :
                  trace?.status === 'FAILED' ? styles.failed : {}),
            }}
          />
          {trace?.status || 'STARTING'}
          {polling && ' (polling...)'}
        </div>
      </div>

      <div style={styles.summary}>
        <div style={styles.summaryCard}>
          <div style={styles.summaryValue}>{summary.total_agents || 0}</div>
          <div style={styles.summaryLabel}>Agents</div>
        </div>
        <div style={styles.summaryCard}>
          <div style={styles.summaryValue}>{summary.total_llm_calls || 0}</div>
          <div style={styles.summaryLabel}>LLM Calls</div>
        </div>
        <div style={styles.summaryCard}>
          <div style={styles.summaryValue}>{summary.total_tool_calls || 0}</div>
          <div style={styles.summaryLabel}>Tool Calls</div>
        </div>
        <div style={styles.summaryCard}>
          <div style={styles.summaryValue}>{summary.total_tokens || 0}</div>
          <div style={styles.summaryLabel}>Tokens</div>
        </div>
      </div>

      <div style={styles.timeline}>
        {agents.map((agent) => (
          <div key={agent.agent_id} style={styles.timelineItem}>
            <div style={styles.agentIcon}>
              {PRESET_ICONS[agent.preset] || '🤖'}
            </div>
            <div style={styles.agentInfo}>
              <div style={styles.agentName}>{agent.agent_id}</div>
              <div style={styles.agentPurpose}>{agent.purpose}</div>
            </div>
            <div
              style={{
                ...styles.agentStatus,
                background: STATUS_COLORS[agent.status] || '#666',
              }}
            >
              {agent.status}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
