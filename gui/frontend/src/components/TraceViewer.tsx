/**
 * TraceViewer Component - Trace/Artifacts 뷰어
 * 
 * 와이어프레임:
 * ┌─────────────────────────────────────────────────────────────┐
 * │ [탭] Trace | Artifacts                                       │
 * ├──────────────────────────┬──────────────────────────────────┤
 * │ Trace Timeline           │ Step Detail                      │
 * │ ─────────────────────── │ ───────────────────────────────  │
 * │ • planner / INPUT (OK)   │ Step: executor / LLM             │
 * │ • planner / LLM (OK)     │ Model: gpt-4o                    │
 * │ • planner / OUTPUT (OK)  │ Tokens: 3,210                    │
 * │ • executor / INPUT (OK)  │ Latency: 4.2s                    │
 * │ ● executor / LLM (RUN)   │ Output Summary:                  │
 * │                          │  - flood depth raster generated  │
 * └──────────────────────────┴──────────────────────────────────┘
 */
import { useState, useEffect } from 'react';
import { 
  Clock, 
  Cpu, 
  Wrench, 
  FileInput,
  FileOutput,
  CheckCircle,
  XCircle,
  Loader,
  Activity,
  FolderOpen,
  Download,
  FileText,
  Image,
  FileJson,
  Zap,
  DollarSign
} from 'lucide-react';
import type { RunSummary, TraceDetail, TraceStep, ArtifactInfo, StepType } from '../types';
import { runsApi } from '../api';

interface Props {
  trace: TraceDetail | null;
  run: RunSummary | null;
}

type Tab = 'trace' | 'artifacts';

export default function TraceViewer({ trace, run }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('trace');
  const [selectedStep, setSelectedStep] = useState<TraceStep | null>(null);
  const [artifacts, setArtifacts] = useState<ArtifactInfo[]>([]);
  const [isLoadingArtifacts, setIsLoadingArtifacts] = useState(false);

  // 첫 번째 step 자동 선택
  useEffect(() => {
    if (trace && trace.steps.length > 0 && !selectedStep) {
      setSelectedStep(trace.steps[0]);
    }
  }, [trace, selectedStep]);

  // Artifacts 로드
  useEffect(() => {
    if (run && activeTab === 'artifacts') {
      setIsLoadingArtifacts(true);
      runsApi.getArtifacts(run.id)
        .then(setArtifacts)
        .catch(console.error)
        .finally(() => setIsLoadingArtifacts(false));
    }
  }, [run, activeTab]);

  if (!trace || !run) {
    return (
      <div className="h-full flex items-center justify-center text-slate-500">
        <div className="text-center">
          <Activity size={48} className="mx-auto mb-4 opacity-30" />
          <p className="text-lg">Trace 데이터가 없습니다</p>
          <p className="text-sm mt-2">우측 Run History에서 실행을 선택하세요</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* ========== 상단: 요약 + 탭 ========== */}
      <div className="bg-slate-800 border-b border-slate-700 flex-shrink-0">
        {/* 요약 정보 */}
        <div className="px-4 py-3 flex items-center justify-between border-b border-slate-700/50">
          <div className="flex items-center gap-4">
            <div>
              <div className="text-xs text-slate-500">Run</div>
              <div className="font-mono text-sm">{run.id}</div>
            </div>
            <StatusBadge status={trace.status} />
          </div>
          
          <div className="flex items-center gap-6 text-sm">
            <div className="flex items-center gap-1.5 text-slate-400">
              <Activity size={14} />
              <span>{trace.steps.length} steps</span>
            </div>
            <div className="flex items-center gap-1.5 text-slate-400">
              <Zap size={14} />
              <span>{trace.total_tokens.toLocaleString()} tokens</span>
            </div>
            <div className="flex items-center gap-1.5 text-slate-400">
              <DollarSign size={14} />
              <span>${trace.total_cost_usd.toFixed(4)}</span>
            </div>
            {trace.total_duration_ms > 0 && (
              <div className="flex items-center gap-1.5 text-slate-400">
                <Clock size={14} />
                <span>{(trace.total_duration_ms / 1000).toFixed(1)}s</span>
              </div>
            )}
          </div>
        </div>

        {/* 탭 */}
        <div className="px-4 flex gap-1">
          <button
            onClick={() => setActiveTab('trace')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'trace'
                ? 'text-teal-400 border-teal-400'
                : 'text-slate-400 border-transparent hover:text-slate-200'
            }`}
          >
            <span className="flex items-center gap-2">
              <Activity size={14} />
              Trace ({trace.steps.length})
            </span>
          </button>
          <button
            onClick={() => setActiveTab('artifacts')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'artifacts'
                ? 'text-teal-400 border-teal-400'
                : 'text-slate-400 border-transparent hover:text-slate-200'
            }`}
          >
            <span className="flex items-center gap-2">
              <FolderOpen size={14} />
              Artifacts ({artifacts.length})
            </span>
          </button>
        </div>
      </div>

      {/* ========== 탭 내용 ========== */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'trace' ? (
          <TraceContent
            trace={trace}
            selectedStep={selectedStep}
            onSelectStep={setSelectedStep}
          />
        ) : (
          <ArtifactsContent
            artifacts={artifacts}
            isLoading={isLoadingArtifacts}
          />
        )}
      </div>
    </div>
  );
}

// ========== Trace Content ==========
function TraceContent({
  trace,
  selectedStep,
  onSelectStep,
}: {
  trace: TraceDetail;
  selectedStep: TraceStep | null;
  onSelectStep: (step: TraceStep) => void;
}) {
  return (
    <div className="h-full flex">
      {/* 좌측: Timeline */}
      <div className="w-80 border-r border-slate-700 overflow-auto flex-shrink-0">
        <ul className="divide-y divide-slate-700/50">
          {trace.steps.map(step => (
            <li
              key={step.step_id}
              onClick={() => onSelectStep(step)}
              className={`
                p-3 cursor-pointer hover:bg-slate-700/50 transition-colors
                ${selectedStep?.step_id === step.step_id ? 'bg-slate-700' : ''}
              `}
            >
              <div className="flex items-center gap-2 mb-1">
                <StepTypeIcon type={step.step_type} />
                <span className="font-medium text-sm">{step.agent_id}</span>
                <span className="text-slate-500 text-xs">/ {step.step_type}</span>
                <div className="ml-auto">
                  <StepStatusIcon status={step.status} />
                </div>
              </div>
              <div className="flex items-center gap-3 text-xs text-slate-500 ml-6">
                {step.latency_ms && <span>{step.latency_ms}ms</span>}
                {step.tokens && <span>{step.tokens} tokens</span>}
                {step.model && <span>{step.model}</span>}
              </div>
            </li>
          ))}
        </ul>
      </div>

      {/* 우측: Detail */}
      <div className="flex-1 overflow-auto p-4 bg-slate-900/50">
        {selectedStep ? (
          <StepDetail step={selectedStep} />
        ) : (
          <div className="h-full flex items-center justify-center text-slate-500">
            <p>Step을 선택하세요</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ========== Step Detail ==========
function StepDetail({ step }: { step: TraceStep }) {
  return (
    <div className="space-y-4">
      {/* 헤더 */}
      <div className="flex items-center gap-3">
        <StepTypeIcon type={step.step_type} size={24} />
        <div>
          <h3 className="text-lg font-semibold">{step.agent_id}</h3>
          <p className="text-sm text-slate-400">{step.step_type} Step</p>
        </div>
        <div className="ml-auto">
          <StepStatusBadge status={step.status} />
        </div>
      </div>

      {/* 기본 정보 */}
      <div className="grid grid-cols-2 gap-4">
        <InfoCard label="Started" value={formatTime(step.started_at)} />
        {step.finished_at && (
          <InfoCard label="Finished" value={formatTime(step.finished_at)} />
        )}
        {step.latency_ms && (
          <InfoCard label="Latency" value={`${step.latency_ms}ms`} />
        )}
        {step.tokens && (
          <InfoCard label="Tokens" value={step.tokens.toLocaleString()} />
        )}
        {step.model && (
          <InfoCard label="Model" value={step.model} />
        )}
      </div>

      {/* LLM 상세 */}
      {step.step_type === 'LLM' && (
        <>
          {step.input_summary && (
            <div className="bg-slate-800 rounded-lg p-4">
              <h4 className="text-xs font-medium text-slate-400 mb-2">Input Summary</h4>
              <p className="text-sm text-slate-300">{step.input_summary}</p>
            </div>
          )}
          {step.output_summary && (
            <div className="bg-slate-800 rounded-lg p-4">
              <h4 className="text-xs font-medium text-slate-400 mb-2">Output Summary</h4>
              <p className="text-sm text-slate-300">{step.output_summary}</p>
            </div>
          )}
        </>
      )}

      {/* Tool 상세 */}
      {step.step_type === 'TOOL' && (
        <>
          {step.tool_name && (
            <div className="bg-slate-800 rounded-lg p-4">
              <h4 className="text-xs font-medium text-slate-400 mb-2">Tool</h4>
              <p className="text-sm font-mono text-orange-400">{step.tool_name}</p>
            </div>
          )}
          {step.tool_args && (
            <div className="bg-slate-800 rounded-lg p-4">
              <h4 className="text-xs font-medium text-slate-400 mb-2">Arguments</h4>
              <pre className="text-xs text-slate-300 overflow-auto">
                {JSON.stringify(step.tool_args, null, 2)}
              </pre>
            </div>
          )}
          {step.tool_result && (
            <div className="bg-slate-800 rounded-lg p-4">
              <h4 className="text-xs font-medium text-slate-400 mb-2">Result</h4>
              <p className="text-sm text-slate-300">{step.tool_result}</p>
            </div>
          )}
        </>
      )}

      {/* Output 상세 */}
      {step.step_type === 'OUTPUT' && step.output_summary && (
        <div className="bg-slate-800 rounded-lg p-4">
          <h4 className="text-xs font-medium text-slate-400 mb-2">Output</h4>
          <p className="text-sm text-slate-300">{step.output_summary}</p>
        </div>
      )}
    </div>
  );
}

// ========== Artifacts Content ==========
function ArtifactsContent({
  artifacts,
  isLoading,
}: {
  artifacts: ArtifactInfo[];
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader size={24} className="animate-spin text-slate-400" />
      </div>
    );
  }

  if (artifacts.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-slate-500">
        <div className="text-center">
          <FolderOpen size={48} className="mx-auto mb-4 opacity-30" />
          <p className="text-lg">Artifacts가 없습니다</p>
          <p className="text-sm mt-2">Run이 완료되면 여기에 결과물이 표시됩니다</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {artifacts.map(artifact => (
        <ArtifactCard key={artifact.path} artifact={artifact} />
      ))}
    </div>
  );
}

// ========== Artifact Card ==========
function ArtifactCard({ artifact }: { artifact: ArtifactInfo }) {
  const getIcon = (type: string) => {
    switch (type) {
      case 'json':
        return <FileJson size={24} className="text-yellow-400" />;
      case 'md':
      case 'txt':
        return <FileText size={24} className="text-blue-400" />;
      case 'png':
      case 'jpg':
      case 'tif':
        return <Image size={24} className="text-purple-400" />;
      default:
        return <FileText size={24} className="text-slate-400" />;
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 hover:border-slate-600 transition-colors">
      <div className="flex items-start justify-between mb-3">
        {getIcon(artifact.type)}
        <button className="p-1.5 hover:bg-slate-700 rounded transition-colors" title="Download">
          <Download size={16} className="text-slate-400" />
        </button>
      </div>
      
      <h4 className="font-medium truncate mb-1">{artifact.name}</h4>
      
      <div className="text-xs text-slate-500 space-y-0.5">
        <div>Type: {artifact.type.toUpperCase()}</div>
        <div>Size: {formatSize(artifact.size_bytes)}</div>
        <div>Created: {new Date(artifact.created_at).toLocaleString('ko-KR')}</div>
      </div>
    </div>
  );
}

// ========== Helper Components ==========
function StepTypeIcon({ type, size = 16 }: { type: StepType; size?: number }) {
  switch (type) {
    case 'INPUT':
      return <FileInput size={size} className="text-blue-400" />;
    case 'LLM':
      return <Cpu size={size} className="text-purple-400" />;
    case 'TOOL':
      return <Wrench size={size} className="text-orange-400" />;
    case 'OUTPUT':
      return <FileOutput size={size} className="text-green-400" />;
    default:
      return <Clock size={size} className="text-slate-400" />;
  }
}

function StepStatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'COMPLETED':
      return <CheckCircle size={14} className="text-green-400" />;
    case 'RUNNING':
      return <Loader size={14} className="text-yellow-400 animate-spin" />;
    case 'FAILED':
      return <XCircle size={14} className="text-red-400" />;
    default:
      return <Clock size={14} className="text-slate-400" />;
  }
}

function StepStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    COMPLETED: 'bg-green-500/20 text-green-400 border-green-500/30',
    RUNNING: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    FAILED: 'bg-red-500/20 text-red-400 border-red-500/30',
  };

  return (
    <span className={`px-2 py-0.5 text-xs rounded border ${colors[status] || 'bg-slate-500/20 text-slate-400'}`}>
      {status}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    COMPLETED: 'bg-green-500/20 text-green-400 border-green-500/30',
    RUNNING: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    FAILED: 'bg-red-500/20 text-red-400 border-red-500/30',
    STOPPED: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  };

  return (
    <span className={`px-2.5 py-1 text-xs font-medium rounded border ${colors[status] || 'bg-slate-500/20 text-slate-400'}`}>
      {status}
    </span>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-slate-800 rounded-lg p-3">
      <div className="text-xs text-slate-500 mb-1">{label}</div>
      <div className="text-sm font-medium">{value}</div>
    </div>
  );
}

function formatTime(isoString: string) {
  return new Date(isoString).toLocaleTimeString('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}
