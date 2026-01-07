/**
 * NEXOUS GUI - Main Application
 * 
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * ⚠️  이것은 챗봇 UI가 아닙니다.
 *     Project YAML 선택/편집/검증/실행 + Run/Trace 관찰 콘솔
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * 
 * 와이어프레임 레이아웃 (3열):
 * ┌────────────────────┬────────────────────────────────────┬────────────────────┐
 * │     Projects       │           Main Panel               │  Trace/Artifacts   │
 * │     (좌측)         │    [탭] Project | Run | Trace      │      (우측)        │
 * │                    │                                    │                    │
 * │ • flood_analysis   │  ┌──────────────────────────────┐  │ Run: flood_001     │
 * │ • traffic_sim      │  │                              │  │ Status: RUNNING    │
 * │ • demo_project     │  │      (탭 내용)                │  │ ───────────────── │
 * │                    │  │                              │  │ Trace Timeline     │
 * │ [+ New] [Delete]   │  │                              │  │ • planner (OK)     │
 * │                    │  └──────────────────────────────┘  │ • executor (RUN)   │
 * └────────────────────┴────────────────────────────────────┴────────────────────┘
 */

import { useState, useEffect, useCallback } from 'react';
import type {
  ProjectSummary,
  ProjectDetail,
  RunSummary,
  TraceDetail,
  LogEntry,
  TraceStep,
} from './types';
import { projectsApi, runsApi, createRunStream } from './api';

// Components
import Header from './components/Header';
import ProjectList from './components/ProjectList';
import MainPanel from './components/MainPanel';
import RunHistoryPanel from './components/RunHistoryPanel';

// 탭 타입
export type MainTab = 'project' | 'run' | 'trace';

export default function App() {
  // ============================================
  // State
  // ============================================
  
  // 프로젝트
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [selectedProject, setSelectedProject] = useState<ProjectDetail | null>(null);
  
  // Run
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [selectedRun, setSelectedRun] = useState<RunSummary | null>(null);
  
  // Trace & Logs
  const [trace, setTrace] = useState<TraceDetail | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  
  // UI 상태
  const [activeTab, setActiveTab] = useState<MainTab>('project');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ============================================
  // Data Loading
  // ============================================
  
  const loadProjects = useCallback(async () => {
    try {
      const data = await projectsApi.list();
      setProjects(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : '프로젝트 로드 실패');
    }
  }, []);

  const loadRuns = useCallback(async () => {
    try {
      const data = await runsApi.list();
      setRuns(data);
    } catch (e) {
      console.error('Run 로드 실패:', e);
    }
  }, []);

  useEffect(() => {
    setIsLoading(true);
    Promise.all([loadProjects(), loadRuns()])
      .finally(() => setIsLoading(false));
  }, [loadProjects, loadRuns]);

  // ============================================
  // Project Handlers
  // ============================================
  
  const handleSelectProject = async (projectId: string) => {
    try {
      setIsLoading(true);
      const detail = await projectsApi.get(projectId);
      setSelectedProject(detail);
      setActiveTab('project');
    } catch (e) {
      setError(e instanceof Error ? e.message : '프로젝트 로드 실패');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateProject = async (name: string, template: string) => {
    try {
      setIsLoading(true);
      const created = await projectsApi.create(name, template);
      await loadProjects();
      handleSelectProject(created.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : '프로젝트 생성 실패');
      setIsLoading(false);
    }
  };

  const handleSaveProject = async (yamlContent: string) => {
    if (!selectedProject) return;
    try {
      setIsLoading(true);
      await projectsApi.update(selectedProject.id, yamlContent);
      const detail = await projectsApi.get(selectedProject.id);
      setSelectedProject(detail);
      await loadProjects();
    } catch (e) {
      setError(e instanceof Error ? e.message : '저장 실패');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteProject = async (projectId: string) => {
    try {
      setIsLoading(true);
      await projectsApi.delete(projectId);
      if (selectedProject?.id === projectId) {
        setSelectedProject(null);
      }
      await loadProjects();
    } catch (e) {
      setError(e instanceof Error ? e.message : '삭제 실패');
    } finally {
      setIsLoading(false);
    }
  };

  // ============================================
  // Run Handlers
  // ============================================
  
  const handleRunProject = async () => {
    if (!selectedProject) return;
    try {
      setIsLoading(true);
      setLogs([]);
      setTrace(null);
      
      const run = await runsApi.create(selectedProject.id);
      setSelectedRun(run);
      setActiveTab('run');
      
      // WebSocket 연결
      const ws = createRunStream(run.id);
      
      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        
        if (message.type === 'log') {
          setLogs(prev => [...prev, message.data as LogEntry]);
        } else if (message.type === 'status') {
          setSelectedRun(prev => prev ? { ...prev, status: message.data } : null);
          if (['COMPLETED', 'FAILED', 'STOPPED'].includes(message.data)) {
            loadRuns();
            runsApi.getTrace(run.id).then(setTrace);
          }
        } else if (message.type === 'step') {
          setTrace(prev => {
            const step = message.data as TraceStep;
            if (!prev) {
              return {
                run_id: run.id,
                project_id: selectedProject.id,
                status: run.status,
                steps: [step],
                total_tokens: 0,
                total_cost_usd: 0,
                total_duration_ms: 0,
              };
            }
            const existingIdx = prev.steps.findIndex(s => s.step_id === step.step_id);
            if (existingIdx >= 0) {
              const newSteps = [...prev.steps];
              newSteps[existingIdx] = step;
              return { ...prev, steps: newSteps };
            }
            return { ...prev, steps: [...prev.steps, step] };
          });
        }
      };
      
      ws.onerror = () => setError('WebSocket 연결 실패');
      await loadRuns();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Run 실행 실패');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectRun = async (runId: string) => {
    try {
      setIsLoading(true);
      const run = runs.find(r => r.id === runId);
      if (run) {
        setSelectedRun(run);
        const [traceData, logsData] = await Promise.all([
          runsApi.getTrace(runId),
          runsApi.getLogs(runId),
        ]);
        setTrace(traceData);
        setLogs(logsData);
        setActiveTab('trace');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Trace 로드 실패');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStopRun = async () => {
    if (!selectedRun) return;
    try {
      await runsApi.stop(selectedRun.id);
      setSelectedRun(prev => prev ? { ...prev, status: 'STOPPED' } : null);
      await loadRuns();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Run 중지 실패');
    }
  };

  // ============================================
  // Render
  // ============================================
  
  return (
    <div className="h-screen flex flex-col bg-slate-900 text-slate-200 overflow-hidden">
      {/* 헤더 */}
      <Header
        selectedProject={selectedProject}
        selectedRun={selectedRun}
        onRefresh={() => { loadProjects(); loadRuns(); }}
      />

      {/* 에러 배너 */}
      {error && (
        <div className="bg-red-500/20 border-b border-red-500/50 text-red-400 px-4 py-2 flex items-center justify-between flex-shrink-0">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="hover:text-red-300 text-xl leading-none">×</button>
        </div>
      )}

      {/* 로딩 오버레이 */}
      {isLoading && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50">
          <div className="flex items-center gap-3 bg-slate-800 px-6 py-4 rounded-lg shadow-xl">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-teal-400"></div>
            <span>Loading...</span>
          </div>
        </div>
      )}

      {/* 메인 3열 레이아웃 */}
      <div className="flex-1 flex overflow-hidden">
        {/* ========== 좌측: Projects ========== */}
        <aside className="w-64 bg-slate-800 border-r border-slate-700 flex flex-col flex-shrink-0">
          <ProjectList
            projects={projects}
            selectedId={selectedProject?.id}
            onSelect={handleSelectProject}
            onCreate={handleCreateProject}
            onDelete={handleDeleteProject}
          />
        </aside>

        {/* ========== 중앙: Main Panel ========== */}
        <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <MainPanel
            activeTab={activeTab}
            onTabChange={setActiveTab}
            project={selectedProject}
            run={selectedRun}
            trace={trace}
            logs={logs}
            onSaveProject={handleSaveProject}
            onRunProject={handleRunProject}
            onStopRun={handleStopRun}
          />
        </main>

        {/* ========== 우측: Trace/Artifacts ========== */}
        <aside className="w-72 bg-slate-800 border-l border-slate-700 flex flex-col flex-shrink-0">
          <RunHistoryPanel
            runs={runs}
            selectedRunId={selectedRun?.id}
            currentRun={selectedRun}
            trace={trace}
            onSelectRun={handleSelectRun}
          />
        </aside>
      </div>
    </div>
  );
}
