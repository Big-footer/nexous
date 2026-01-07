/**
 * Trace Viewer Component
 * Timeline + Steps + Artifacts
 */

import React, { useState } from 'react';

const styles = {
  container: {
    padding: '16px',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
  },
  tabs: {
    display: 'flex',
    gap: '8px',
    marginBottom: '16px',
  },
  tab: {
    padding: '8px 16px',
    background: '#252540',
    border: 'none',
    borderRadius: '4px',
    color: '#888',
    cursor: 'pointer',
  },
  tabActive: {
    background: '#4a9eff',
    color: 'white',
  },
  content: {
    flex: 1,
    overflowY: 'auto',
  },
  agentCard: {
    background: '#252540',
    borderRadius: '8px',
    marginBottom: '16px',
    overflow: 'hidden',
  },
  agentHeader: {
    padding: '12px 16px',
    background: '#1e1e30',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    cursor: 'pointer',
  },
  agentTitle: {
    fontWeight: 'bold',
  },
  agentStatus: {
    padding: '4px 8px',
    borderRadius: '4px',
    fontSize: '12px',
  },
  stepsContainer: {
    padding: '16px',
  },
  step: {
    display: 'flex',
    alignItems: 'center',
    padding: '8px',
    borderLeft: '2px solid #4a9eff',
    marginLeft: '8px',
    marginBottom: '8px',
  },
  stepType: {
    width: '60px',
    fontSize: '12px',
    fontWeight: 'bold',
    color: '#4a9eff',
  },
  stepInfo: {
    flex: 1,
    fontSize: '12px',
    color: '#888',
  },
  stepStatus: {
    fontSize: '12px',
  },
  artifactCard: {
    background: '#252540',
    padding: '16px',
    borderRadius: '8px',
    marginBottom: '8px',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  artifactIcon: {
    fontSize: '24px',
  },
  artifactInfo: {
    flex: 1,
  },
  artifactName: {
    fontWeight: 'bold',
  },
  artifactPath: {
    fontSize: '12px',
    color: '#888',
  },
  empty: {
    textAlign: 'center',
    color: '#666',
    padding: '48px',
  },
  errorCard: {
    background: '#3d1f1f',
    border: '1px solid #f44336',
    padding: '16px',
    borderRadius: '8px',
    marginBottom: '8px',
  },
  errorType: {
    color: '#f44336',
    fontWeight: 'bold',
    marginBottom: '4px',
  },
  errorMessage: {
    fontSize: '14px',
  },
};

const ARTIFACT_ICONS = {
  raster: '🗺️',
  markdown: '📄',
  json: '📋',
  csv: '📊',
  default: '📁',
};

const STATUS_COLORS = {
  OK: '#4CAF50',
  ERROR: '#f44336',
  COMPLETED: '#4CAF50',
  FAILED: '#f44336',
};

export default function TraceViewer({ trace }) {
  const [activeTab, setActiveTab] = useState('timeline');
  const [expandedAgents, setExpandedAgents] = useState({});

  if (!trace) {
    return (
      <div style={styles.empty}>
        Run a project to view trace
      </div>
    );
  }

  const toggleAgent = (agentId) => {
    setExpandedAgents((prev) => ({
      ...prev,
      [agentId]: !prev[agentId],
    }));
  };

  const renderTimeline = () => (
    <div>
      {trace.agents?.map((agent) => (
        <div key={agent.agent_id} style={styles.agentCard}>
          <div
            style={styles.agentHeader}
            onClick={() => toggleAgent(agent.agent_id)}
          >
            <span style={styles.agentTitle}>
              {expandedAgents[agent.agent_id] ? '▼' : '▶'} {agent.agent_id}
              <span style={{ color: '#888', fontWeight: 'normal', marginLeft: '8px' }}>
                ({agent.preset})
              </span>
            </span>
            <span
              style={{
                ...styles.agentStatus,
                background: STATUS_COLORS[agent.status] || '#666',
              }}
            >
              {agent.status}
            </span>
          </div>
          
          {expandedAgents[agent.agent_id] && (
            <div style={styles.stepsContainer}>
              {agent.steps?.map((step, idx) => (
                <div key={idx} style={styles.step}>
                  <span style={styles.stepType}>{step.type}</span>
                  <span style={styles.stepInfo}>
                    {step.type === 'LLM' && `${step.provider}/${step.model} • ${step.latency_ms}ms`}
                    {step.type === 'TOOL' && `${step.tool_name} • ${step.latency_ms}ms`}
                    {step.type === 'INPUT' && 'Context loaded'}
                    {step.type === 'OUTPUT' && `Keys: ${step.payload_summary?.output_keys?.join(', ')}`}
                  </span>
                  <span style={{ ...styles.stepStatus, color: STATUS_COLORS[step.status] }}>
                    {step.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );

  const renderArtifacts = () => (
    <div>
      {trace.artifacts?.length === 0 ? (
        <div style={styles.empty}>No artifacts</div>
      ) : (
        trace.artifacts?.map((artifact) => (
          <div key={artifact.artifact_id} style={styles.artifactCard}>
            <span style={styles.artifactIcon}>
              {ARTIFACT_ICONS[artifact.type] || ARTIFACT_ICONS.default}
            </span>
            <div style={styles.artifactInfo}>
              <div style={styles.artifactName}>{artifact.artifact_id}</div>
              <div style={styles.artifactPath}>{artifact.path}</div>
            </div>
            <span style={{ color: '#888', fontSize: '12px' }}>
              by {artifact.created_by}
            </span>
          </div>
        ))
      )}
    </div>
  );

  const renderErrors = () => (
    <div>
      {trace.errors?.length === 0 ? (
        <div style={styles.empty}>No errors</div>
      ) : (
        trace.errors?.map((error, idx) => (
          <div key={idx} style={styles.errorCard}>
            <div style={styles.errorType}>{error.type}</div>
            <div style={styles.errorMessage}>{error.message}</div>
            <div style={{ fontSize: '12px', color: '#888', marginTop: '8px' }}>
              {error.agent_id} / {error.step_id}
            </div>
          </div>
        ))
      )}
    </div>
  );

  return (
    <div style={styles.container}>
      <div style={styles.tabs}>
        <button
          style={{ ...styles.tab, ...(activeTab === 'timeline' ? styles.tabActive : {}) }}
          onClick={() => setActiveTab('timeline')}
        >
          Timeline
        </button>
        <button
          style={{ ...styles.tab, ...(activeTab === 'artifacts' ? styles.tabActive : {}) }}
          onClick={() => setActiveTab('artifacts')}
        >
          Artifacts ({trace.artifacts?.length || 0})
        </button>
        <button
          style={{ ...styles.tab, ...(activeTab === 'errors' ? styles.tabActive : {}) }}
          onClick={() => setActiveTab('errors')}
        >
          Errors ({trace.errors?.length || 0})
        </button>
      </div>
      
      <div style={styles.content}>
        {activeTab === 'timeline' && renderTimeline()}
        {activeTab === 'artifacts' && renderArtifacts()}
        {activeTab === 'errors' && renderErrors()}
      </div>
    </div>
  );
}
