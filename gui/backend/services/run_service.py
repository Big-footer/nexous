"""
Run Service

Runner 실행 관리 (Thread 기반)
"""

import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import sys

# NEXOUS Core 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class RunService:
    """Run 실행 서비스"""
    
    def __init__(self, projects_dir: str = "projects", traces_dir: str = "traces"):
        self.projects_dir = Path(projects_dir)
        self.traces_dir = Path(traces_dir)
        self._active_runs: Dict[str, Dict[str, Any]] = {}
    
    def start_run(self, project_id: str, run_id: str = None) -> Dict[str, Any]:
        """
        Run 시작 (Thread로 비동기 실행)
        
        Returns:
            {"run_id": "...", "status": "STARTED"}
        """
        # Run ID 생성
        if not run_id:
            run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        project_yaml = self.projects_dir / project_id / "project.yaml"
        if not project_yaml.exists():
            raise ValueError(f"Project not found: {project_id}")
        
        # 실행 정보 저장
        self._active_runs[run_id] = {
            "project_id": project_id,
            "run_id": run_id,
            "status": "STARTING",
            "started_at": datetime.now().isoformat()
        }
        
        # Thread로 실행
        thread = threading.Thread(
            target=self._execute_run,
            args=(project_id, run_id, str(project_yaml)),
            daemon=True
        )
        thread.start()
        
        return {"run_id": run_id, "status": "STARTED"}
    
    def _execute_run(self, project_id: str, run_id: str, project_yaml_path: str):
        """Runner 실행 (Thread에서 호출)"""
        try:
            self._active_runs[run_id]["status"] = "RUNNING"
            
            from nexous.core.runner import run_project
            
            trace_path = run_project(
                project_yaml_path=project_yaml_path,
                run_id=run_id,
                trace_dir=str(self.traces_dir)
            )
            
            self._active_runs[run_id]["status"] = "COMPLETED"
            self._active_runs[run_id]["trace_path"] = trace_path
            
        except Exception as e:
            self._active_runs[run_id]["status"] = "FAILED"
            self._active_runs[run_id]["error"] = str(e)
    
    def get_run_status(self, project_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        """Run 상태 조회"""
        # 먼저 active runs 확인
        if run_id in self._active_runs:
            return self._active_runs[run_id]
        
        # trace.json에서 상태 확인
        trace_path = self.traces_dir / project_id / run_id / "trace.json"
        if trace_path.exists():
            import json
            with open(trace_path, 'r', encoding='utf-8') as f:
                trace = json.load(f)
            return {
                "project_id": project_id,
                "run_id": run_id,
                "status": trace.get("status", "UNKNOWN"),
                "started_at": trace.get("started_at"),
                "ended_at": trace.get("ended_at"),
                "duration_ms": trace.get("duration_ms")
            }
        
        return None
    
    def list_runs(self, project_id: str) -> List[Dict[str, Any]]:
        """프로젝트의 Run 목록 조회"""
        runs = []
        project_traces_dir = self.traces_dir / project_id
        
        if not project_traces_dir.exists():
            return runs
        
        import json
        for run_dir in project_traces_dir.iterdir():
            if run_dir.is_dir():
                trace_path = run_dir / "trace.json"
                if trace_path.exists():
                    try:
                        with open(trace_path, 'r', encoding='utf-8') as f:
                            trace = json.load(f)
                        runs.append({
                            "run_id": run_dir.name,
                            "status": trace.get("status", "UNKNOWN"),
                            "started_at": trace.get("started_at"),
                            "ended_at": trace.get("ended_at"),
                            "duration_ms": trace.get("duration_ms"),
                            "summary": trace.get("summary", {})
                        })
                    except Exception:
                        runs.append({
                            "run_id": run_dir.name,
                            "status": "ERROR",
                            "error": "Failed to read trace"
                        })
        
        return sorted(runs, key=lambda x: x.get("started_at") or "", reverse=True)
