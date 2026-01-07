/**
 * NEXOUS GUI - TypeScript 타입 정의
 * 
 * ⚠️ 이것은 챗봇 타입이 아닙니다.
 *    Project/Run/Trace 관리 타입입니다.
 */

// ============================================
// Enums
// ============================================

export type RunStatus = 
  | 'DEFINED' 
  | 'CREATED' 
  | 'IDLE' 
  | 'RUNNING' 
  | 'COMPLETED' 
  | 'FAILED' 
  | 'STOPPED';

export type StepType = 'INPUT' | 'LLM' | 'TOOL' | 'OUTPUT';

export type LogLevel = 'info' | 'warning' | 'error' | 'debug';


// ============================================
// Project
// ============================================

export interface ProjectSummary {
  id: string;
  name: string;
  domain: string;
  description: string;
  last_modified: string;
  path: string;
  agent_count: number;
  artifact_count: number;
}

export interface ProjectDetail {
  id: string;
  name: string;
  yaml_content: string;
  agents: AgentConfig[];
  artifacts: ArtifactConfig[];
}

export interface AgentConfig {
  id: string;
  preset?: string;
  purpose?: string;
  dependencies?: string[];
  config?: Record<string, unknown>;
}

export interface ArtifactConfig {
  id: string;
  source: string;
  format: string;
  path: string;
}


// ============================================
// Validation
// ============================================

export interface ValidationError {
  field: string;
  message: string;
  line?: number;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: string[];
  agents: string[];
  artifacts: string[];
}


// ============================================
// Run
// ============================================

export interface RunSummary {
  id: string;
  project_id: string;
  project_name: string;
  status: RunStatus;
  started_at: string;
  finished_at?: string;
  duration_ms?: number;
  current_agent?: string;
}


// ============================================
// Trace
// ============================================

export interface TraceStep {
  step_id: string;
  agent_id: string;
  step_type: StepType;
  status: string;
  started_at: string;
  finished_at?: string;
  latency_ms?: number;
  tokens?: number;
  model?: string;
  input_summary?: string;
  output_summary?: string;
  tool_name?: string;
  tool_args?: Record<string, unknown>;
  tool_result?: string;
}

export interface TraceDetail {
  run_id: string;
  project_id: string;
  status: RunStatus;
  steps: TraceStep[];
  total_tokens: number;
  total_cost_usd: number;
  total_duration_ms: number;
}


// ============================================
// Artifacts
// ============================================

export interface ArtifactInfo {
  name: string;
  path: string;
  type: string;
  size_bytes: number;
  created_at: string;
}


// ============================================
// Logs
// ============================================

export interface LogEntry {
  time: string;
  level: LogLevel;
  component: string;
  message: string;
}


// ============================================
// WebSocket Messages
// ============================================

export type WSMessageType = 'status' | 'log' | 'step' | 'error';

export interface WSMessage {
  type: WSMessageType;
  data: RunStatus | LogEntry | TraceStep | string;
}


// ============================================
// App State
// ============================================

export type ActivePanel = 'projects' | 'editor' | 'run' | 'trace';

export interface AppState {
  // 선택된 항목
  selectedProjectId: string | null;
  selectedRunId: string | null;
  
  // 활성 패널
  activePanel: ActivePanel;
  
  // 로딩 상태
  isLoading: boolean;
  error: string | null;
}
