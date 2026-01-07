/**
 * MainPanel Component - 중앙 메인 패널 (탭 포함)
 * 
 * 와이어프레임:
 * ┌──────────────────────────────────────────────────────────────┐
 * │ [탭] Project | Run | Trace                                   │
 * ├──────────────────────────────────────────────────────────────┤
 * │                                                              │
 * │                    (탭 내용)                                  │
 * │                                                              │
 * └──────────────────────────────────────────────────────────────┘
 */
import { FileText, Play, Activity } from 'lucide-react';
import type { MainTab } from '../App';
import type { ProjectDetail, RunSummary, TraceDetail, LogEntry } from '../types';

// Sub-components
import ProjectEditor from './ProjectEditor';
import RunConsole from './RunConsole';
import TraceViewer from './TraceViewer';

interface Props {
  activeTab: MainTab;
  onTabChange: (tab: MainTab) => void;
  project: ProjectDetail | null;
  run: RunSummary | null;
  trace: TraceDetail | null;
  logs: LogEntry[];
  onSaveProject: (yamlContent: string) => void;
  onRunProject: () => void;
  onStopRun: () => void;
}

export default function MainPanel({
  activeTab,
  onTabChange,
  project,
  run,
  trace,
  logs,
  onSaveProject,
  onRunProject,
  onStopRun,
}: Props) {
  const tabs: { id: MainTab; label: string; icon: React.ReactNode }[] = [
    { id: 'project', label: 'Project', icon: <FileText size={16} /> },
    { id: 'run', label: 'Run', icon: <Play size={16} /> },
    { id: 'trace', label: 'Trace', icon: <Activity size={16} /> },
  ];

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* 탭 헤더 */}
      <div className="bg-slate-800 border-b border-slate-700 px-4 flex items-center gap-1 flex-shrink-0">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`
              flex items-center gap-2 px-4 py-3 text-sm font-medium
              border-b-2 transition-colors
              ${activeTab === tab.id
                ? 'text-teal-400 border-teal-400'
                : 'text-slate-400 border-transparent hover:text-slate-200'
              }
            `}
          >
            {tab.icon}
            {tab.label}
            
            {/* Run 탭에 상태 표시 */}
            {tab.id === 'run' && run?.status === 'RUNNING' && (
              <span className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse" />
            )}
          </button>
        ))}
        
        {/* 현재 프로젝트 표시 */}
        {project && (
          <div className="ml-auto text-sm text-slate-500">
            {project.name}
          </div>
        )}
      </div>

      {/* 탭 내용 */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'project' && (
          project ? (
            <ProjectEditor
              project={project}
              onSave={onSaveProject}
              onRun={onRunProject}
            />
          ) : (
            <EmptyState
              icon={<FileText size={48} />}
              title="프로젝트를 선택하세요"
              description="좌측 목록에서 프로젝트를 선택하거나 새로 생성하세요"
            />
          )
        )}
        
        {activeTab === 'run' && (
          run ? (
            <RunConsole
              run={run}
              logs={logs}
              trace={trace}
              onStop={onStopRun}
            />
          ) : (
            <EmptyState
              icon={<Play size={48} />}
              title="실행 중인 Run이 없습니다"
              description="Project 탭에서 Run 버튼을 클릭하여 실행하세요"
            />
          )
        )}
        
        {activeTab === 'trace' && (
          trace ? (
            <TraceViewer
              trace={trace}
              run={run}
            />
          ) : (
            <EmptyState
              icon={<Activity size={48} />}
              title="Trace 데이터가 없습니다"
              description="우측 Run History에서 실행을 선택하세요"
            />
          )
        )}
      </div>
    </div>
  );
}

// 빈 상태 컴포넌트
function EmptyState({ 
  icon, 
  title, 
  description 
}: { 
  icon: React.ReactNode; 
  title: string; 
  description: string;
}) {
  return (
    <div className="flex-1 h-full flex items-center justify-center text-slate-500">
      <div className="text-center">
        <div className="mb-4 opacity-30">{icon}</div>
        <p className="text-lg font-medium">{title}</p>
        <p className="text-sm mt-2 text-slate-600">{description}</p>
      </div>
    </div>
  );
}
