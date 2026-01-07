/**
 * NEXOUS GUI - API Client
 * 
 * ⚠️ 이것은 챗봇 API가 아닙니다.
 *    Project/Run/Trace 관리 API입니다.
 */

import type {
  ProjectSummary,
  ProjectDetail,
  ValidationResult,
  RunSummary,
  TraceDetail,
  ArtifactInfo,
  LogEntry,
} from './types';

const API_BASE = '/api';

// ============================================
// 공통 fetch 래퍼
// ============================================

async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API Error: ${res.status}`);
  }

  return res.json();
}


// ============================================
// Projects API
// ============================================

export const projectsApi = {
  /** 프로젝트 목록 조회 */
  list: (): Promise<ProjectSummary[]> => 
    apiFetch('/projects'),

  /** 프로젝트 상세 조회 */
  get: (projectId: string): Promise<ProjectDetail> =>
    apiFetch(`/projects/${projectId}`),

  /** 프로젝트 생성 */
  create: (name: string, template: string = 'basic'): Promise<ProjectSummary> =>
    apiFetch('/projects', {
      method: 'POST',
      body: JSON.stringify({ name, template }),
    }),

  /** 프로젝트 YAML 저장 */
  update: (projectId: string, yamlContent: string): Promise<{ status: string }> =>
    apiFetch(`/projects/${projectId}`, {
      method: 'PUT',
      body: JSON.stringify({ yaml_content: yamlContent }),
    }),

  /** 프로젝트 삭제 */
  delete: (projectId: string): Promise<{ status: string }> =>
    apiFetch(`/projects/${projectId}`, {
      method: 'DELETE',
    }),

  /** 프로젝트 YAML 검증 */
  validate: (projectId: string): Promise<ValidationResult> =>
    apiFetch(`/projects/${projectId}/validate`, {
      method: 'POST',
    }),

  /** YAML 내용 직접 검증 (저장 전) */
  validateContent: (yamlContent: string): Promise<ValidationResult> =>
    apiFetch('/projects/validate-content', {
      method: 'POST',
      body: JSON.stringify({ yaml_content: yamlContent }),
    }),
};


// ============================================
// Runs API
// ============================================

export const runsApi = {
  /** Run 목록 조회 */
  list: (): Promise<RunSummary[]> =>
    apiFetch('/runs'),

  /** Run 상세 조회 */
  get: (runId: string): Promise<RunSummary> =>
    apiFetch(`/runs/${runId}`),

  /** Run 생성 및 실행 */
  create: (projectId: string): Promise<RunSummary> =>
    apiFetch('/runs', {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId }),
    }),

  /** Run 중지 */
  stop: (runId: string): Promise<{ status: string }> =>
    apiFetch(`/runs/${runId}/stop`, {
      method: 'POST',
    }),

  /** Trace 조회 */
  getTrace: (runId: string): Promise<TraceDetail> =>
    apiFetch(`/runs/${runId}/trace`),

  /** Artifacts 조회 */
  getArtifacts: (runId: string): Promise<ArtifactInfo[]> =>
    apiFetch(`/runs/${runId}/artifacts`),

  /** Logs 조회 */
  getLogs: (runId: string): Promise<LogEntry[]> =>
    apiFetch(`/runs/${runId}/logs`),
};


// ============================================
// WebSocket - 실시간 로그 스트리밍
// ============================================

export function createRunStream(runId: string): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return new WebSocket(`${protocol}//${host}/api/runs/${runId}/stream`);
}


// ============================================
// Health Check
// ============================================

export const healthApi = {
  check: (): Promise<{
    status: string;
    version: string;
    projects_count: number;
    runs_count: number;
    active_runs: number;
  }> => apiFetch('/health'),
};
