/**
 * ProjectEditor Component - YAML 편집기 + 검증
 * 
 * 와이어프레임:
 * ┌──────────────────────────────┬──────────────────────────────┐
 * │ YAML Editor                  │ Validation / Preview         │
 * │ ─────────────────────────── │ ───────────────────────────  │
 * │ project:                     │ ✓ Schema OK                  │
 * │   id: flood_analysis_ulsan   │ Agents:                       │
 * │ agents:                      │ - planner                    │
 * │   - id: planner              │ - executor                   │
 * │   - id: executor             │ Artifacts:                   │
 * │                              │ - report                     │
 * │                              │                              │
 * │                              │ [Validate] [Save] [Run]     │
 * └──────────────────────────────┴──────────────────────────────┘
 */
import { useState, useEffect, useCallback } from 'react';
import Editor from '@monaco-editor/react';
import { 
  Save, 
  Play, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  RefreshCw,
  Users,
  FileOutput,
  Code
} from 'lucide-react';
import type { ProjectDetail, ValidationResult } from '../types';
import { projectsApi } from '../api';

interface Props {
  project: ProjectDetail;
  onSave: (yamlContent: string) => void;
  onRun: () => void;
}

export default function ProjectEditor({ project, onSave, onRun }: Props) {
  const [content, setContent] = useState(project.yaml_content);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [isValidating, setIsValidating] = useState(false);

  // 프로젝트 변경 시 리셋
  useEffect(() => {
    setContent(project.yaml_content);
    setValidation(null);
    setIsDirty(false);
  }, [project.id, project.yaml_content]);

  // 에디터 변경 핸들러
  const handleEditorChange = useCallback((value: string | undefined) => {
    if (value !== undefined) {
      setContent(value);
      setIsDirty(value !== project.yaml_content);
    }
  }, [project.yaml_content]);

  // 검증
  const handleValidate = async () => {
    setIsValidating(true);
    try {
      const result = await projectsApi.validateContent(content);
      setValidation(result);
    } catch (e) {
      setValidation({
        valid: false,
        errors: [{ field: 'api', message: '검증 API 호출 실패' }],
        warnings: [],
        agents: [],
        artifacts: [],
      });
    } finally {
      setIsValidating(false);
    }
  };

  // 저장
  const handleSave = () => {
    onSave(content);
    setIsDirty(false);
  };

  // 실행
  const handleRun = async () => {
    // 저장 안 된 경우 먼저 저장
    if (isDirty) {
      onSave(content);
    }
    // 검증 안 된 경우 검증
    if (!validation) {
      await handleValidate();
    }
    onRun();
  };

  return (
    <div className="h-full flex">
      {/* ========== 좌측: YAML 에디터 ========== */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 에디터 툴바 */}
        <div className="bg-slate-800 border-b border-slate-700 px-4 py-2 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <Code size={18} className="text-slate-400" />
            <span className="font-medium">{project.id}.yaml</span>
            {isDirty && (
              <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded">
                수정됨
              </span>
            )}
          </div>
        </div>

        {/* Monaco Editor */}
        <div className="flex-1 min-h-0">
          <Editor
            height="100%"
            language="yaml"
            theme="vs-dark"
            value={content}
            onChange={handleEditorChange}
            options={{
              minimap: { enabled: false },
              fontSize: 13,
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
              wordWrap: 'on',
              tabSize: 2,
              automaticLayout: true,
              padding: { top: 12, bottom: 12 },
              scrollbar: {
                verticalScrollbarSize: 8,
                horizontalScrollbarSize: 8,
              },
            }}
          />
        </div>
      </div>

      {/* ========== 우측: 검증 + 미리보기 ========== */}
      <div className="w-80 bg-slate-800 border-l border-slate-700 flex flex-col flex-shrink-0">
        {/* 검증 결과 */}
        <div className="p-4 border-b border-slate-700">
          <h3 className="text-sm font-medium text-slate-400 mb-3">Validation</h3>
          
          {validation ? (
            <div className={`
              flex items-center gap-2 px-3 py-2.5 rounded-lg
              ${validation.valid 
                ? 'bg-green-500/10 border border-green-500/30' 
                : 'bg-red-500/10 border border-red-500/30'
              }
            `}>
              {validation.valid ? (
                <>
                  <CheckCircle size={20} className="text-green-400" />
                  <div>
                    <span className="text-green-400 font-medium">Schema OK</span>
                    <p className="text-xs text-green-400/70 mt-0.5">JSON Schema + 로직 검증 통과</p>
                  </div>
                </>
              ) : (
                <>
                  <XCircle size={20} className="text-red-400" />
                  <div>
                    <span className="text-red-400 font-medium">
                      {validation.errors.length} Error(s)
                    </span>
                    {validation.warnings.length > 0 && (
                      <p className="text-xs text-yellow-400/70 mt-0.5">
                        + {validation.warnings.length} Warning(s)
                      </p>
                    )}
                  </div>
                </>
              )}
            </div>
          ) : (
            <div className="text-sm text-slate-500 bg-slate-700/30 px-3 py-2.5 rounded-lg">
              <p>Validate 버튼을 클릭하세요</p>
              <p className="text-xs text-slate-600 mt-1">JSON Schema + 로직 검증 수행</p>
            </div>
          )}
        </div>

        {/* 에러 목록 */}
        {validation && validation.errors.length > 0 && (
          <div className="p-4 border-b border-slate-700 max-h-48 overflow-auto">
            <h4 className="text-xs font-medium text-red-400 mb-2 flex items-center gap-1.5">
              <XCircle size={14} />
              Errors
            </h4>
            <ul className="space-y-2">
              {validation.errors.map((err, i) => (
                <li key={i} className="text-xs bg-slate-900/50 px-2.5 py-2 rounded">
                  <div className="text-red-400 font-mono">{err.field}</div>
                  <div className="text-slate-400 mt-0.5">{err.message}</div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 경고 목록 */}
        {validation && validation.warnings.length > 0 && (
          <div className="p-4 border-b border-slate-700">
            <h4 className="text-xs font-medium text-yellow-400 mb-2 flex items-center gap-1.5">
              <AlertTriangle size={14} />
              Warnings
            </h4>
            <ul className="space-y-1">
              {validation.warnings.map((warn, i) => (
                <li key={i} className="text-xs text-slate-400 bg-slate-900/50 px-2.5 py-1.5 rounded">
                  {warn}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Quick Preview */}
        <div className="flex-1 p-4 overflow-auto">
          <h3 className="text-sm font-medium text-slate-400 mb-3">Quick Preview</h3>
          
          {/* Agents */}
          <div className="mb-4">
            <div className="flex items-center gap-2 text-xs text-slate-500 mb-2">
              <Users size={14} />
              <span>Agents ({validation?.agents.length || project.agents.length})</span>
            </div>
            <ul className="space-y-1">
              {(validation?.agents || project.agents.map(a => a.id)).map(agentId => (
                <li 
                  key={agentId}
                  className="text-xs font-mono bg-slate-700/50 px-2 py-1 rounded flex items-center gap-2"
                >
                  <span className="w-1.5 h-1.5 bg-teal-400 rounded-full" />
                  {agentId}
                </li>
              ))}
            </ul>
          </div>

          {/* Artifacts */}
          <div>
            <div className="flex items-center gap-2 text-xs text-slate-500 mb-2">
              <FileOutput size={14} />
              <span>Artifacts ({validation?.artifacts.length || project.artifacts.length})</span>
            </div>
            <ul className="space-y-1">
              {(validation?.artifacts || project.artifacts.map(a => a.id)).map(artifactId => (
                <li 
                  key={artifactId}
                  className="text-xs font-mono bg-slate-700/50 px-2 py-1 rounded flex items-center gap-2"
                >
                  <span className="w-1.5 h-1.5 bg-purple-400 rounded-full" />
                  {artifactId}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* 버튼 영역 */}
        <div className="p-4 border-t border-slate-700 space-y-2">
          <button
            onClick={handleValidate}
            disabled={isValidating}
            className="btn btn-secondary w-full justify-center"
          >
            {isValidating ? (
              <RefreshCw size={16} className="animate-spin" />
            ) : (
              <CheckCircle size={16} />
            )}
            Validate
          </button>
          
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={!isDirty}
              className="btn btn-secondary flex-1 justify-center disabled:opacity-50"
            >
              <Save size={16} />
              Save
            </button>
            
            <button
              onClick={handleRun}
              disabled={validation !== null && !validation.valid}
              className="btn btn-success flex-1 justify-center disabled:opacity-50"
            >
              <Play size={16} />
              Run
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
