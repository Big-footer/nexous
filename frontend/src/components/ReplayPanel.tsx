/**
 * NEXOUS STEP 4A-2: Replay Panel Components
 * 
 * DRY Replay 결과를 타임라인으로 시각화하는 React 컴포넌트
 */

import React, { useState } from 'react';
import './ReplayPanel.css';

// ============================================
// Type Definitions
// ============================================

interface ReplaySummary {
  total_steps: number;
  llm_steps: number;
  tool_steps: number;
  error_steps: number;
  status: 'COMPLETED' | 'FAILED' | 'UNKNOWN';
}

interface TimelineStep {
  step_index: number;
  type: 'SYSTEM' | 'LLM' | 'TOOL' | 'ERROR';
  label: string;
  duration_ms: number;
  meta?: any;
}

interface ReplayResult {
  ok: boolean;
  mode: string;
  summary: ReplaySummary;
  timeline: TimelineStep[];
  report: string;
}

// ============================================
// ReplaySummaryComponent
// ============================================

const ReplaySummaryComponent: React.FC<{ 
  summary: ReplaySummary;
  runId: string;
}> = ({ summary, runId }) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'COMPLETED': return '#10b981'; // Green
      case 'FAILED': return '#ef4444'; // Red
      default: return '#6b7280'; // Gray
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'COMPLETED': return '✓';
      case 'FAILED': return '✗';
      default: return '?';
    }
  };

  return (
    <div className="replay-summary">
      <div className="replay-header">
        <h3>Replay (DRY) — {runId}</h3>
      </div>
      
      <div className="summary-content">
        <div className="status-badge" style={{ backgroundColor: getStatusColor(summary.status) }}>
          <span className="status-icon">{getStatusIcon(summary.status)}</span>
          <span className="status-text">{summary.status}</span>
        </div>
        
        <div className="steps-info">
          <span className="total-steps">
            <strong>Steps:</strong> {summary.total_steps}
          </span>
          <span className="step-breakdown">
            (LLM {summary.llm_steps} | TOOL {summary.tool_steps} | ERROR {summary.error_steps})
          </span>
        </div>
      </div>
    </div>
  );
};

// ============================================
// ReplayTimelineItem
// ============================================

const ReplayTimelineItem: React.FC<{
  step: TimelineStep;
  isSelected: boolean;
  onClick: () => void;
}> = ({ step, isSelected, onClick }) => {
  const getTypeColor = (type: string) => {
    switch (type) {
      case 'LLM': return '#3b82f6'; // Blue
      case 'TOOL': return '#8b5cf6'; // Purple
      case 'ERROR': return '#ef4444'; // Red
      case 'SYSTEM': return '#9ca3af'; // Gray
      default: return '#6b7280';
    }
  };

  const formatDuration = (ms: number) => {
    if (ms === 0) return '—';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  return (
    <div 
      className={`timeline-item ${isSelected ? 'selected' : ''}`}
      onClick={onClick}
    >
      <span className="step-index">[{step.step_index}]</span>
      <span 
        className="step-type-badge"
        style={{ backgroundColor: getTypeColor(step.type) }}
      >
        {step.type}
      </span>
      <span className="step-label">{step.label}</span>
      <span className="step-duration">{formatDuration(step.duration_ms)}</span>
    </div>
  );
};

// ============================================
// ReplayTimeline
// ============================================

const ReplayTimeline: React.FC<{
  timeline: TimelineStep[];
  selectedIndex: number | null;
  onSelectStep: (index: number) => void;
}> = ({ timeline, selectedIndex, onSelectStep }) => {
  return (
    <div className="replay-timeline">
      <h4>TIMELINE</h4>
      <div className="timeline-list">
        {timeline.map((step) => (
          <ReplayTimelineItem
            key={step.step_index}
            step={step}
            isSelected={selectedIndex === step.step_index}
            onClick={() => onSelectStep(step.step_index)}
          />
        ))}
      </div>
    </div>
  );
};

// ============================================
// ReplayStepDetail
// ============================================

const ReplayStepDetail: React.FC<{ step: TimelineStep | null }> = ({ step }) => {
  if (!step) {
    return (
      <div className="step-detail">
        <p className="no-selection">Select a step to view details</p>
      </div>
    );
  }

  const renderLLMDetail = (meta: any) => (
    <>
      <div className="detail-row">
        <span className="label">Provider:</span>
        <span className="value">{meta.provider}</span>
      </div>
      <div className="detail-row">
        <span className="label">Model:</span>
        <span className="value">{meta.model}</span>
      </div>
      <div className="detail-row">
        <span className="label">Attempt:</span>
        <span className="value">{meta.attempt}</span>
      </div>
      {meta.tokens && (
        <div className="detail-row">
          <span className="label">Tokens:</span>
          <span className="value">
            {meta.tokens.total || 0} 
            {meta.tokens.input && ` (in: ${meta.tokens.input}, out: ${meta.tokens.output})`}
          </span>
        </div>
      )}
      <div className="detail-row">
        <span className="label">Status:</span>
        <span className={`value status-${meta.status?.toLowerCase()}`}>{meta.status}</span>
      </div>
    </>
  );

  const renderToolDetail = (meta: any) => (
    <>
      <div className="detail-row">
        <span className="label">Tool Name:</span>
        <span className="value">{meta.tool_name}</span>
      </div>
      <div className="detail-row">
        <span className="label">Status:</span>
        <span className={`value status-${meta.status?.toLowerCase()}`}>{meta.status}</span>
      </div>
      {meta.input_summary && (
        <div className="detail-row">
          <span className="label">Input:</span>
          <div className="value summary-text">{meta.input_summary.substring(0, 200)}...</div>
        </div>
      )}
      {meta.output_summary && (
        <div className="detail-row">
          <span className="label">Output:</span>
          <div className="value summary-text">{meta.output_summary.substring(0, 200)}...</div>
        </div>
      )}
    </>
  );

  const renderErrorDetail = (meta: any) => (
    <>
      <div className="detail-row">
        <span className="label">Error Type:</span>
        <span className="value error-type">{meta.error_type}</span>
      </div>
      <div className="detail-row">
        <span className="label">Message:</span>
        <div className="value error-message">{meta.message}</div>
      </div>
    </>
  );

  return (
    <div className="step-detail">
      <h4>STEP DETAIL</h4>
      <div className="detail-header">
        <span className="detail-title">Step {step.step_index} | {step.type}</span>
      </div>
      
      <div className="detail-content">
        {step.meta && step.type === 'LLM' && renderLLMDetail(step.meta)}
        {step.meta && step.type === 'TOOL' && renderToolDetail(step.meta)}
        {step.meta && step.type === 'ERROR' && renderErrorDetail(step.meta)}
        {step.type === 'SYSTEM' && (
          <div className="detail-row">
            <span className="label">System Event:</span>
            <span className="value">{step.label}</span>
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================
// ReplayPanel (Main Component)
// ============================================

export const ReplayPanel: React.FC<{
  replayResult: ReplayResult;
  runId: string;
  onClose: () => void;
}> = ({ replayResult, runId, onClose }) => {
  const [selectedStepIndex, setSelectedStepIndex] = useState<number | null>(null);
  
  const selectedStep = selectedStepIndex !== null
    ? replayResult.timeline.find(step => step.step_index === selectedStepIndex) || null
    : null;
  
  const handleCopyReport = () => {
    navigator.clipboard.writeText(replayResult.report);
    alert('Report copied to clipboard!');
  };
  
  return (
    <div className="replay-panel-overlay" onClick={onClose}>
      <div className="replay-panel" onClick={(e) => e.stopPropagation()}>
        <ReplaySummaryComponent summary={replayResult.summary} runId={runId} />
        
        <div className="replay-content">
          <ReplayTimeline
            timeline={replayResult.timeline}
            selectedIndex={selectedStepIndex}
            onSelectStep={setSelectedStepIndex}
          />
          
          <ReplayStepDetail step={selectedStep} />
        </div>
        
        <div className="panel-actions">
          <button className="action-btn" onClick={handleCopyReport}>
            Copy Report
          </button>
          <button className="action-btn close-btn" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default ReplayPanel;
