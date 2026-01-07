/**
 * ProjectList Component - 프로젝트 목록 (좌측 사이드바)
 * 
 * 와이어프레임:
 * ┌─────────────────────────────────────────────────────────────┐
 * │ Projects                                                     │
 * ├─────────────────────────────────────────────────────────────┤
 * │ ID                      | Domain          | Modified        │
 * ├─────────────────────────┼─────────────────┼────────────────┤
 * │ flood_analysis_ulsan    | flood_analysis  | 2026-01-01      │
 * │ traffic_simulation      | traffic         | 2026-01-02      │
 * ├─────────────────────────────────────────────────────────────┤
 * │ [New Project] [Duplicate] [Delete]                           │
 * └─────────────────────────────────────────────────────────────┘
 */
import { useState } from 'react';
import { FolderPlus, Copy, Trash2, FileText, ChevronRight } from 'lucide-react';
import type { ProjectSummary } from '../types';

interface Props {
  projects: ProjectSummary[];
  selectedId?: string;
  onSelect: (projectId: string) => void;
  onCreate: (name: string, template: string) => void;
  onDelete: (projectId: string) => void;
}

export default function ProjectList({ 
  projects, 
  selectedId, 
  onSelect, 
  onCreate,
  onDelete 
}: Props) {
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newTemplate, setNewTemplate] = useState('basic');

  const handleCreate = () => {
    if (newName.trim()) {
      onCreate(newName.trim(), newTemplate);
      setNewName('');
      setShowCreate(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleCreate();
    if (e.key === 'Escape') setShowCreate(false);
  };

  return (
    <>
      {/* 헤더 */}
      <div className="p-3 border-b border-slate-700">
        <h2 className="font-semibold text-lg">Projects</h2>
      </div>

      {/* 프로젝트 목록 */}
      <div className="flex-1 overflow-auto">
        {projects.length === 0 ? (
          <div className="p-4 text-sm text-slate-500 text-center">
            <FileText size={32} className="mx-auto mb-2 opacity-50" />
            <p>프로젝트가 없습니다</p>
            <p className="text-xs mt-1">새 프로젝트를 생성하세요</p>
          </div>
        ) : (
          <ul>
            {projects.map(project => (
              <li
                key={project.id}
                onClick={() => onSelect(project.id)}
                className={`
                  px-3 py-2.5 cursor-pointer border-b border-slate-700/50
                  hover:bg-slate-700/50 transition-colors group
                  ${selectedId === project.id ? 'bg-slate-700 border-l-2 border-l-teal-500' : ''}
                `}
              >
                {/* 프로젝트 이름 */}
                <div className="flex items-center gap-2">
                  <ChevronRight 
                    size={14} 
                    className={`text-slate-500 transition-transform ${
                      selectedId === project.id ? 'rotate-90 text-teal-400' : ''
                    }`}
                  />
                  <span className={`font-medium truncate text-sm ${
                    selectedId === project.id ? 'text-teal-400' : ''
                  }`}>
                    {project.id}
                  </span>
                </div>

                {/* 메타 정보 */}
                <div className="ml-6 mt-1 flex items-center gap-2 text-xs text-slate-500">
                  <span className="bg-slate-700 px-1.5 py-0.5 rounded">
                    {project.domain || 'general'}
                  </span>
                  <span>•</span>
                  <span>{project.last_modified}</span>
                </div>

                {/* 에이전트/아티팩트 수 */}
                <div className="ml-6 mt-1 text-xs text-slate-600">
                  {project.agent_count} agents • {project.artifact_count} artifacts
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* 하단 버튼 */}
      <div className="p-3 border-t border-slate-700 flex gap-2">
        <button
          onClick={() => setShowCreate(true)}
          className="btn btn-primary btn-sm flex-1"
        >
          <FolderPlus size={16} />
          New Project
        </button>
        
        {selectedId && (
          <button
            onClick={() => {
              if (confirm(`"${selectedId}" 프로젝트를 삭제할까요?`)) {
                onDelete(selectedId);
              }
            }}
            className="btn btn-ghost btn-sm text-red-400 hover:text-red-300 hover:bg-red-500/20"
            title="Delete"
          >
            <Trash2 size={16} />
          </button>
        )}
      </div>

      {/* ========== 생성 모달 ========== */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg p-6 w-[420px] shadow-2xl border border-slate-700">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <FolderPlus size={24} className="text-teal-400" />
              New Project
            </h3>
            
            <div className="space-y-4">
              {/* 프로젝트 이름 */}
              <div>
                <label className="block text-sm text-slate-400 mb-1.5">
                  Project Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="input"
                  placeholder="my_flood_analysis"
                  autoFocus
                />
                <p className="text-xs text-slate-500 mt-1">
                  영문, 숫자, 밑줄(_)만 사용 가능
                </p>
              </div>
              
              {/* 템플릿 선택 */}
              <div>
                <label className="block text-sm text-slate-400 mb-1.5">Template</label>
                <div className="space-y-2">
                  <label className={`
                    flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors
                    ${newTemplate === 'basic' 
                      ? 'border-teal-500 bg-teal-500/10' 
                      : 'border-slate-600 hover:border-slate-500'
                    }
                  `}>
                    <input
                      type="radio"
                      name="template"
                      value="basic"
                      checked={newTemplate === 'basic'}
                      onChange={(e) => setNewTemplate(e.target.value)}
                      className="mt-1"
                    />
                    <div>
                      <div className="font-medium">Basic</div>
                      <div className="text-xs text-slate-400">
                        Planner → Executor → Writer (3 agents)
                      </div>
                    </div>
                  </label>
                  
                  <label className={`
                    flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors
                    ${newTemplate === 'research' 
                      ? 'border-teal-500 bg-teal-500/10' 
                      : 'border-slate-600 hover:border-slate-500'
                    }
                  `}>
                    <input
                      type="radio"
                      name="template"
                      value="research"
                      checked={newTemplate === 'research'}
                      onChange={(e) => setNewTemplate(e.target.value)}
                      className="mt-1"
                    />
                    <div>
                      <div className="font-medium">Research</div>
                      <div className="text-xs text-slate-400">
                        Planner → Literature → Analyzer → Writer → QA (5 agents)
                      </div>
                    </div>
                  </label>
                </div>
              </div>
            </div>
            
            {/* 버튼 */}
            <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-slate-700">
              <button 
                onClick={() => { setShowCreate(false); setNewName(''); }}
                className="btn btn-ghost"
              >
                Cancel
              </button>
              <button 
                onClick={handleCreate}
                disabled={!newName.trim()}
                className="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Create Project
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
