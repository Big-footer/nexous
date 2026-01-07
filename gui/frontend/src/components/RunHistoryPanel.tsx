/**
 * RunHistoryPanel Component - 우측 사이드바 (Run History + Trace Timeline)
 * 
 * 와이어프레임:
 * ┌──────────────────────────┐
 * │ Run: flood_001           │
 * │ Status: RUNNING          │
 * │ ──────────────────────── │
 * │ Trace Timeline           │
 * │ • planner_01 (OK)        │
 * │ • executor_01 (RUN)      │
 * │ ──────────────────────── │
 * │ Run History              │
 * │ • run_001 (COMPLETED)    │
 * │ • run_002 (FAILED)       │
 * └──────────────────────────┘
 */
import { Clock, CheckCircle, XCircle, AlertCircle, Loader, Cpu, Wrench, FileOutput } from 'lucide-react';
import type { RunSummary, TraceDetail, TraceStep, StepType } from '../types';

interface Props {
  runs: RunSummary[];
  selectedRunId?: string;
  currentRun: RunSummary | null;
  trace: TraceDetail | null;
  onSelectRun: (runId: string) => void;
}

export default function RunHistoryPanel({
  runs,
  selectedRunId,
  currentRun,
  trace,
  onSelectRun,
}: Props) {
  return (
    <div className="flex flex-col h-full">
      {/* ========== 현재 Run 상태 ========== */}
      {currentRun && (
        <div className="p-4 border-b border-slate-700">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-slate-400">Current Run</span>
            <StatusBadge status={currentRun.status} />
          </div>
          <div className="font-mono text-sm truncate">{currentRun.id}</div>
          <div className="text-xs text-slate-500 mt-1">{currentRun.project_name}</div>
          
          {/* 현재 에이전트 */}
          {currentRun.current_agent && currentRun.status === 'RUNNING' && (
            <div className="mt-2 flex items-center gap-2 text-xs text-yellow-400">
              <Loader size={12} className="animate-spin" />
              <span>실행 중: {currentRun.current_agent}</span>
            </div>
          )}
          
          {/* 실행 시간 */}
          {currentRun.duration_ms && (
            <div className="mt-2 text-xs text-slate-500">
              소요 시간: {(currentRun.duration_ms / 1000).toFixed(1)}s
            </div>
          )}
        </div>
      )}

      {/* ========== Trace Timeline ========== */}
      {trace && trace.steps.length > 0 && (
        <div className="border-b border-slate-700">
          <div className="px-4 py-2 text-sm font-medium text-slate-400 bg-slate-800/50">
            Trace Timeline
          </div>
          <div className="max-h-48 overflow-auto">
            <ul className="divide-y divide-slate-700/50">
              {trace.steps.map(step => (
                <TraceStepItem key={step.step_id} step={step} />
              ))}
            </ul>
          </div>
          
          {/* 요약 */}
          <div className="px-4 py-2 bg-slate-800/30 text-xs text-slate-500 flex justify-between">
            <span>{trace.steps.length} steps</span>
            <span>{trace.total_tokens.toLocaleString()} tokens</span>
          </div>
        </div>
      )}

      {/* ========== Run History ========== */}
      <div className="flex-1 flex flex-col min-h-0">
        <div className="px-4 py-2 text-sm font-medium text-slate-400 bg-slate-800/50 flex-shrink-0">
          Run History
        </div>
        <div className="flex-1 overflow-auto">
          {runs.length === 0 ? (
            <div className="p-4 text-sm text-slate-500 text-center">
              실행 기록이 없습니다
            </div>
          ) : (
            <ul className="divide-y divide-slate-700/50">
              {runs.slice(0, 20).map(run => (
                <li
                  key={run.id}
                  onClick={() => onSelectRun(run.id)}
                  className={`
                    px-4 py-3 cursor-pointer hover:bg-slate-700/50 transition-colors
                    ${selectedRunId === run.id ? 'bg-slate-700' : ''}
                  `}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-xs truncate flex-1">{run.id}</span>
                    <StatusBadge status={run.status} size="sm" />
                  </div>
                  <div className="text-xs text-slate-500 truncate">{run.project_name}</div>
                  <div className="text-xs text-slate-600 mt-1">
                    {new Date(run.started_at).toLocaleString('ko-KR', {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

// ========== 상태 배지 ==========
function StatusBadge({ status, size = 'md' }: { status: string; size?: 'sm' | 'md' }) {
  const baseClass = size === 'sm' ? 'badge text-[10px] px-1.5 py-0' : 'badge';
  
  switch (status) {
    case 'RUNNING':
      return (
        <span className={`${baseClass} badge-running flex items-center gap-1`}>
          <span className="w-1.5 h-1.5 bg-yellow-400 rounded-full animate-pulse" />
          RUNNING
        </span>
      );
    case 'COMPLETED':
      return <span className={`${baseClass} badge-completed`}>COMPLETED</span>;
    case 'FAILED':
      return <span className={`${baseClass} badge-failed`}>FAILED</span>;
    case 'STOPPED':
      return <span className={`${baseClass} badge-stopped`}>STOPPED</span>;
    default:
      return <span className={`${baseClass} badge-idle`}>{status}</span>;
  }
}

// ========== Trace Step 아이템 ==========
function TraceStepItem({ step }: { step: TraceStep }) {
  const getStepIcon = (type: StepType) => {
    switch (type) {
      case 'INPUT':
        return <FileOutput size={12} className="text-blue-400" />;
      case 'LLM':
        return <Cpu size={12} className="text-purple-400" />;
      case 'TOOL':
        return <Wrench size={12} className="text-orange-400" />;
      case 'OUTPUT':
        return <FileOutput size={12} className="text-green-400" />;
      default:
        return <Clock size={12} className="text-slate-400" />;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return <CheckCircle size={12} className="text-green-400" />;
      case 'RUNNING':
        return <Loader size={12} className="text-yellow-400 animate-spin" />;
      case 'FAILED':
        return <XCircle size={12} className="text-red-400" />;
      default:
        return <Clock size={12} className="text-slate-400" />;
    }
  };

  return (
    <li className="px-4 py-2 flex items-center gap-2 text-xs">
      {getStepIcon(step.step_type)}
      <span className="flex-1 truncate">
        <span className="text-slate-300">{step.agent_id}</span>
        <span className="text-slate-500 ml-1">/ {step.step_type}</span>
      </span>
      {step.latency_ms && (
        <span className="text-slate-600">{step.latency_ms}ms</span>
      )}
      {getStatusIcon(step.status)}
    </li>
  );
}
