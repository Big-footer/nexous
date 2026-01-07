/**
 * NEXOUS STEP 4A-1: Diff Modal Components
 * 
 * Diff 결과를 GUI로 표시하는 React 컴포넌트
 */

import React, { useState } from 'react';
import './DiffModal.css';

// ============================================
// Type Definitions
// ============================================

interface DiffSummary {
  baseline_run: string;
  target_run: string;
  status: 'IDENTICAL' | 'CHANGED' | 'FAILED';
  first_divergence: {
    step_index: number;
    step_type: string;
    reason: string;
  } | null;
  counts: {
    llm: number;
    tool: number;
    errors: number;
  };
}

interface DiffChange {
  step_index: number;
  type: 'LLM' | 'TOOL' | 'ERROR' | 'METADATA';
  field: string;
  baseline_value: string;
  target_value: string;
  policy: any;
}

interface DiffResult {
  ok: boolean;
  summary: DiffSummary;
  changes: DiffChange[];
  report: string;
}

type FilterType = 'ALL' | 'LLM' | 'TOOL' | 'ERROR';

// ============================================
// DiffSummaryComponent
// ============================================

const DiffSummaryComponent: React.FC<{ summary: DiffSummary }> = ({ summary }) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'IDENTICAL': return '#10b981'; // Green
      case 'CHANGED': return '#f59e0b'; // Orange
      case 'FAILED': return '#ef4444'; // Red
      default: return '#6b7280'; // Gray
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'IDENTICAL': return '✓';
      case 'CHANGED': return '⚠';
      case 'FAILED': return '✗';
      default: return '?';
    }
  };

  return (
    <div className="diff-summary">
      <div className="diff-header">
        <h3>Diff: {summary.baseline_run} ↔ {summary.target_run}</h3>
      </div>
      
      <div className="summary-content">
        <div className="status-badge" style={{ backgroundColor: getStatusColor(summary.status) }}>
          <span className="status-icon">{getStatusIcon(summary.status)}</span>
          <span className="status-text">{summary.status}</span>
        </div>
        
        {summary.first_divergence && (
          <div className="first-divergence">
            <strong>First Divergence:</strong>
            <div className="divergence-detail">
              <span>Step {summary.first_divergence.step_index}</span>
              <span className="type-badge">{summary.first_divergence.step_type}</span>
              <span className="reason">{summary.first_divergence.reason}</span>
            </div>
          </div>
        )}
        
        <div className="counts">
          <span className="count-item">
            <strong>LLM:</strong> {summary.counts.llm}
          </span>
          <span className="count-item">
            <strong>TOOL:</strong> {summary.counts.tool}
          </span>
          <span className="count-item">
            <strong>ERROR:</strong> {summary.counts.errors}
          </span>
        </div>
      </div>
    </div>
  );
};

// ============================================
// DiffFilter
// ============================================

const DiffFilter: React.FC<{
  activeFilter: FilterType;
  onFilterChange: (filter: FilterType) => void;
  counts: DiffSummary['counts'];
}> = ({ activeFilter, onFilterChange, counts }) => {
  const filters: FilterType[] = ['ALL', 'LLM', 'TOOL', 'ERROR'];
  
  const getFilterLabel = (filter: FilterType) => {
    switch (filter) {
      case 'ALL': return `All (${counts.llm + counts.tool + counts.errors})`;
      case 'LLM': return `LLM (${counts.llm})`;
      case 'TOOL': return `TOOL (${counts.tool})`;
      case 'ERROR': return `ERROR (${counts.errors})`;
    }
  };

  return (
    <div className="diff-filter">
      {filters.map(filter => (
        <button
          key={filter}
          className={`filter-btn ${activeFilter === filter ? 'active' : ''}`}
          onClick={() => onFilterChange(filter)}
        >
          {getFilterLabel(filter)}
        </button>
      ))}
    </div>
  );
};

// ============================================
// DiffChangeItem
// ============================================

const DiffChangeItem: React.FC<{ change: DiffChange }> = ({ change }) => {
  const getTypeColor = (type: string) => {
    switch (type) {
      case 'LLM': return '#3b82f6'; // Blue
      case 'TOOL': return '#8b5cf6'; // Purple
      case 'ERROR': return '#ef4444'; // Red
      case 'METADATA': return '#6b7280'; // Gray
      default: return '#6b7280';
    }
  };

  return (
    <div className="change-item">
      <div className="change-header">
        <span className="step-index">[Step {change.step_index}]</span>
        <span 
          className="type-badge" 
          style={{ backgroundColor: getTypeColor(change.type) }}
        >
          {change.type}
        </span>
        <span className="field-name">{change.field}</span>
      </div>
      
      <div className="change-values">
        <div className="value-row">
          <span className="label">Baseline:</span>
          <code className="value">{change.baseline_value}</code>
        </div>
        <div className="value-row">
          <span className="label">Target:</span>
          <code className="value">{change.target_value}</code>
        </div>
      </div>
      
      {change.policy && (
        <div className="policy-info">
          <span className="label">Policy:</span>
          <code>{JSON.stringify(change.policy, null, 2)}</code>
        </div>
      )}
    </div>
  );
};

// ============================================
// DiffChangeList
// ============================================

const DiffChangeList: React.FC<{
  changes: DiffChange[];
  filter: FilterType;
}> = ({ changes, filter }) => {
  const MAX_DISPLAY = 200;
  
  // Filter changes
  const filteredChanges = changes.filter(change => {
    if (filter === 'ALL') return true;
    return change.type === filter;
  });
  
  const displayChanges = filteredChanges.slice(0, MAX_DISPLAY);
  const hasMore = filteredChanges.length > MAX_DISPLAY;
  
  if (filteredChanges.length === 0) {
    return (
      <div className="no-changes">
        <p>No changes found for this filter.</p>
      </div>
    );
  }
  
  return (
    <div className="change-list">
      {displayChanges.map((change, index) => (
        <DiffChangeItem key={index} change={change} />
      ))}
      
      {hasMore && (
        <div className="too-many-changes">
          <p>⚠ Too many changes ({filteredChanges.length} total)</p>
          <p>Showing first {MAX_DISPLAY}. Please use filters to narrow down.</p>
        </div>
      )}
    </div>
  );
};

// ============================================
// DiffModal (Main Component)
// ============================================

export const DiffModal: React.FC<{
  diffResult: DiffResult;
  onClose: () => void;
}> = ({ diffResult, onClose }) => {
  const [activeFilter, setActiveFilter] = useState<FilterType>('ALL');
  const [activeTab, setActiveTab] = useState<'CHANGES' | 'REPORT'>('CHANGES');
  
  const handleCopyJSON = () => {
    navigator.clipboard.writeText(JSON.stringify(diffResult, null, 2));
    alert('Diff result copied to clipboard!');
  };
  
  const handleCopyReport = () => {
    navigator.clipboard.writeText(diffResult.report);
    alert('Report copied to clipboard!');
  };
  
  const handleExport = () => {
    const blob = new Blob([JSON.stringify(diffResult, null, 2)], { 
      type: 'application/json' 
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `diff_${diffResult.summary.baseline_run}_vs_${diffResult.summary.target_run}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };
  
  return (
    <div className="diff-modal-overlay" onClick={onClose}>
      <div className="diff-modal" onClick={(e) => e.stopPropagation()}>
        <DiffSummaryComponent summary={diffResult.summary} />
        
        <div className="diff-tabs">
          <button
            className={`tab-btn ${activeTab === 'CHANGES' ? 'active' : ''}`}
            onClick={() => setActiveTab('CHANGES')}
          >
            Changes
          </button>
          <button
            className={`tab-btn ${activeTab === 'REPORT' ? 'active' : ''}`}
            onClick={() => setActiveTab('REPORT')}
          >
            Report
          </button>
        </div>
        
        {activeTab === 'CHANGES' && (
          <>
            <DiffFilter
              activeFilter={activeFilter}
              onFilterChange={setActiveFilter}
              counts={diffResult.summary.counts}
            />
            
            <DiffChangeList
              changes={diffResult.changes}
              filter={activeFilter}
            />
          </>
        )}
        
        {activeTab === 'REPORT' && (
          <div className="report-tab">
            <pre className="report-text">{diffResult.report}</pre>
            <button className="copy-btn" onClick={handleCopyReport}>
              Copy Report
            </button>
          </div>
        )}
        
        <div className="modal-actions">
          <button className="action-btn" onClick={handleCopyJSON}>
            Copy JSON
          </button>
          <button className="action-btn" onClick={handleExport}>
            Export
          </button>
          <button className="action-btn close-btn" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default DiffModal;
