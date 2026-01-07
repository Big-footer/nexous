"""
Trace Service

trace.json 조회
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List


class TraceService:
    """Trace 조회 서비스"""
    
    def __init__(self, traces_dir: str = "traces"):
        self.traces_dir = Path(traces_dir)
    
    def get_trace(self, project_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        """trace.json 전체 반환"""
        trace_path = self.traces_dir / project_id / run_id / "trace.json"
        
        if not trace_path.exists():
            return None
        
        with open(trace_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_artifacts(self, project_id: str, run_id: str) -> List[Dict[str, Any]]:
        """artifacts만 반환"""
        trace = self.get_trace(project_id, run_id)
        if not trace:
            return []
        return trace.get("artifacts", [])
    
    def get_agents(self, project_id: str, run_id: str) -> List[Dict[str, Any]]:
        """agents만 반환"""
        trace = self.get_trace(project_id, run_id)
        if not trace:
            return []
        return trace.get("agents", [])
    
    def get_summary(self, project_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        """summary만 반환"""
        trace = self.get_trace(project_id, run_id)
        if not trace:
            return None
        return trace.get("summary", {})
    
    def get_errors(self, project_id: str, run_id: str) -> List[Dict[str, Any]]:
        """errors만 반환"""
        trace = self.get_trace(project_id, run_id)
        if not trace:
            return []
        return trace.get("errors", [])
