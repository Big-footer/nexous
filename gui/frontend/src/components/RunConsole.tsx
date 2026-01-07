/**
 * RunConsole Component - 실행 콘솔 (로그 스트림 + 단계)
 * 
 * 와이어프레임:
 * ┌─────────────────────────────────────────────────────────────┐
 * │ Run Console                                                  │
 * ├─────────────────────────────────────────────────────────────┤
 * │ Project: flood_analysis_ulsan                                │
 * │ Run ID : run_20260101_001                                    │
 * │ Status : RUNNING                                             │
 * ├─────────────────────────────────────────────────────────────┤
 * │ Current Agent: executor (core/executor)                      │
 * │ Stage: INPUT → LLM → TOOL → OUTPUT                           │
 * ├─────────────────────────────────────────────────────────────┤
 * │ Log Stream                                                   │
 * │ [12:01:10] planner | plan created                            │
 * │ [12:01:22] executor | swmm run started                       │
 * │ [12:03:45] executor | tool: python_exec OK                   │
 * │ ...                                                          │
 * ├─────────────────────────────────────────────────────────────┤
 * │ [Stop]                                                       │
 * └─────────────────────────────────────────────────────────────┘
 */
import { useEffect, useRef } from 'react';
import { 
  Square, 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  Loader,
  ChevronRight,
  Cpu,
  Wrench,
  FileInput,
  FileOutput
} from 'lucide-react';
import type { RunSummary, LogEntry, TraceDetail, StepType } from '../types';

interface Props {
  run: RunSummary | null;
  logs: LogEntry[];
  trace: TraceDetail | null;
  onStop: () => void;
}

export default function RunConsole({ run, logs, trace, onStop }: Props) {
  const logsEndRef = useRef<HTMLDivElement>(null);

  // 로그 자동 스크롤
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  if (!run) {
    return (
      <div className="h-full flex items-center justify-center text-slate-500">
        <div className="text-center">
          <Loader size={48} className="mx-auto mb-4 opacity-30" />
          <p className="text-lg">Run이 선택되지 않았습니다</p>
          <p className="text-sm mt-2">Project 탭에서 Run 버튼을 클릭하세요</p>
        </div>
      </div>
    );
  }

  // 현재 단계 계산
  const currentSteps = trace?.steps.filter(s => s.agent_id === run.current_agent) || [];
  const lastStep = currentSteps[currentSteps.length - 1];

  return (
    <div className="h-full flex flex-col">
      {/* ========== 상단: Run 정보 ========== */}
      <div className="bg-slate-800 border-b border-slate-700 p-4 flex-shrink-0">
        <div className="grid grid-cols-3 gap-4">
          {/* Project */}
          <div>
            <div className="text-xs text-slate-500 mb-1">Project</div>
            <div className="font-mono text-sm">{run.project_name}</div>
          </div>
          
          {/* Run ID */}
          <div>
            <div className="text-xs text-slate-500 mb-1">Run ID</div>
            <div className="font-mono text-sm">{run.id}</div>
          </div>
          
          {/* Status */}
          <div>
            <div className="text-xs text-slate-500 mb-1">Status</div>
            <StatusBadge status={run.status} />
          </div>
        </div>
      </div>

      {/* ========== 현재 Agent + Stage ========== */}
      {run.status === 'RUNNING' && run.current_agent && (
        <div className="bg-slate-800/50 border-b border-slate-700 px-4 py-3 flex-shrink-0">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm">
              <span className="text-slate-400">Current Agent: </span>
              <span className="text-teal-400 font-medium">{run.current_agent}</span>
            </div>
            <div className="text-xs text-slate-500">
              {run.duration_ms ? `${(run.duration_ms / 1000).toFixed(1)}s` : '실행 중...'}
            </div>
          </div>
          
          {/* Stage Pipeline */}
          <StageIndicator currentStep={lastStep?.step_type} />
        </div>
      )}

      {/* ========== 로그 스트림 ========== */}
      <div className="flex-1 overflow-auto bg-slate-900 p-4 font-mono text-sm min-h-0">
        {logs.length === 0 ? (
          <div className="text-slate-600 text-center py-8">
            <Clock size={24} className="mx-auto mb-2 opacity-50" />
            <p>로그를 기다리는 중...</p>
          </div>
        ) : (
          <div className="space-y-0.5">
            {logs.map((log, i) => (
              <LogLine key={i} log={log} />
            ))}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>

      {/* ========== 하단: 버튼 ========== */}
      <div className="bg-slate-800 border-t border-slate-700 p-4 flex items-center justify-between flex-shrink-0">
        <div className="text-sm text-slate-500">
          {logs.length} logs • {trace?.steps.length || 0} steps
          {trace?.total_tokens ? ` • ${trace.total_tokens.toLocaleString()} tokens` : ''}
        </div>
        
        {run.status === 'RUNNING' && (
          <button onClick={onStop} className="btn btn-danger btn-sm">
            <Square size={16} />
            Stop
          </button>
        )}
        
        {run.status === 'COMPLETED' && (
          <div className="flex items-center gap-2 text-green-400 text-sm">
            <CheckCircle size={16} />
            완료됨
            {run.duration_ms && ` (${(run.duration_ms / 1000).toFixed(1)}s)`}
          </div>
        )}
        
        {run.status === 'FAILED' && (
          <div className="flex items-center gap-2 text-red-400 text-sm">
            <XCircle size={16} />
            실패
          </div>
        )}
        
        {run.status === 'STOPPED' && (
          <div className="flex items-center gap-2 text-orange-400 text-sm">
            <AlertCircle size={16} />
            중지됨
          </div>
        )}
      </div>
    </div>
  );
}

// ========== 상태 배지 ==========
function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
    RUNNING: {
      bg: 'bg-yellow-500/20 border-yellow-500/30',
      text: 'text-yellow-400',
      icon: <Loader size={14} className="animate-spin" />,
    },
    COMPLETED: {
      bg: 'bg-green-500/20 border-green-500/30',
      text: 'text-green-400',
      icon: <CheckCircle size={14} />,
    },
    FAILED: {
      bg: 'bg-red-500/20 border-red-500/30',
      text: 'text-red-400',
      icon: <XCircle size={14} />,
    },
    STOPPED: {
      bg: 'bg-orange-500/20 border-orange-500/30',
      text: 'text-orange-400',
      icon: <AlertCircle size={14} />,
    },
  };

  const { bg, text, icon } = config[status] || {
    bg: 'bg-slate-500/20 border-slate-500/30',
    text: 'text-slate-400',
    icon: <Clock size={14} />,
  };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded border ${bg} ${text}`}>
      {icon}
      <span className="text-xs font-medium">{status}</span>
    </span>
  );
}

// ========== Stage Indicator ==========
function StageIndicator({ currentStep }: { currentStep?: StepType }) {
  const stages: { type: StepType; label: string; icon: React.ReactNode }[] = [
    { type: 'INPUT', label: 'INPUT', icon: <FileInput size={14} /> },
    { type: 'LLM', label: 'LLM', icon: <Cpu size={14} /> },
    { type: 'TOOL', label: 'TOOL', icon: <Wrench size={14} /> },
    { type: 'OUTPUT', label: 'OUTPUT', icon: <FileOutput size={14} /> },
  ];

  const currentIdx = stages.findIndex(s => s.type === currentStep);

  return (
    <div className="flex items-center gap-1">
      {stages.map((stage, i) => (
        <div key={stage.type} className="flex items-center">
          <div className={`
            flex items-center gap-1.5 px-2.5 py-1 rounded text-xs
            ${i < currentIdx 
              ? 'bg-green-500/20 text-green-400' 
              : i === currentIdx 
                ? 'bg-yellow-500/20 text-yellow-400 animate-pulse' 
                : 'bg-slate-700/50 text-slate-500'
            }
          `}>
            {stage.icon}
            {stage.label}
          </div>
          {i < stages.length - 1 && (
            <ChevronRight size={14} className="text-slate-600 mx-0.5" />
          )}
        </div>
      ))}
    </div>
  );
}

// ========== 로그 라인 ==========
function LogLine({ log }: { log: LogEntry }) {
  const levelColors: Record<string, string> = {
    info: 'text-slate-400',
    warning: 'text-yellow-400',
    error: 'text-red-400',
    debug: 'text-slate-600',
  };

  const levelBgColors: Record<string, string> = {
    info: '',
    warning: 'bg-yellow-500/5',
    error: 'bg-red-500/10',
    debug: '',
  };

  return (
    <div className={`flex gap-3 py-0.5 px-2 rounded ${levelBgColors[log.level] || ''}`}>
      {/* 시간 */}
      <span className="text-slate-600 flex-shrink-0">
        {new Date(log.time).toLocaleTimeString('ko-KR', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        })}
      </span>
      
      {/* 컴포넌트 */}
      <span className="text-teal-500 w-20 truncate flex-shrink-0">
        {log.component}
      </span>
      
      {/* 메시지 */}
      <span className={levelColors[log.level] || 'text-slate-400'}>
        {log.message}
      </span>
    </div>
  );
}
