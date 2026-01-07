/**
 * Header Component - 상단 헤더 바
 * 
 * 표시 항목:
 * - NEXOUS 로고
 * - 현재 선택된 project_id
 * - 현재 run_id 및 상태 배지
 * - 새로고침 버튼
 */
import { RefreshCw, Box } from 'lucide-react';
import type { ProjectDetail, RunSummary } from '../types';

interface Props {
  selectedProject: ProjectDetail | null;
  selectedRun: RunSummary | null;
  onRefresh: () => void;
}

export default function Header({ selectedProject, selectedRun, onRefresh }: Props) {
  return (
    <header className="bg-slate-800 border-b border-slate-700 px-4 py-2.5 flex items-center justify-between flex-shrink-0">
      {/* 좌측: 로고 + 타이틀 */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-teal-500 rounded-lg flex items-center justify-center">
            <Box size={20} className="text-white" />
          </div>
          <h1 className="text-lg font-bold text-white">NEXOUS</h1>
        </div>
        <div className="h-6 w-px bg-slate-700" />
        <span className="text-sm text-slate-400">Project Execution Console</span>
      </div>

      {/* 우측: 상태 표시 + 새로고침 */}
      <div className="flex items-center gap-4">
        {/* 현재 프로젝트 */}
        {selectedProject && (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-500">Project:</span>
            <span className="text-teal-400 font-mono">{selectedProject.id}</span>
          </div>
        )}
        
        {/* 현재 Run */}
        {selectedRun && (
          <>
            <div className="h-4 w-px bg-slate-700" />
            <div className="flex items-center gap-2 text-sm">
              <span className="text-slate-500">Run:</span>
              <span className="font-mono text-xs">{selectedRun.id}</span>
              <StatusBadge status={selectedRun.status} />
            </div>
          </>
        )}

        {/* 새로고침 */}
        <div className="h-4 w-px bg-slate-700" />
        <button
          onClick={onRefresh}
          className="p-2 rounded-lg hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
          title="새로고침"
        >
          <RefreshCw size={18} />
        </button>
      </div>
    </header>
  );
}

// 상태 배지
function StatusBadge({ status }: { status: string }) {
  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'RUNNING':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'COMPLETED':
        return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'FAILED':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'STOPPED':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  return (
    <span className={`
      px-2 py-0.5 text-xs font-medium rounded border
      ${getStatusStyle(status)}
      ${status === 'RUNNING' ? 'animate-pulse' : ''}
    `}>
      {status}
    </span>
  );
}
