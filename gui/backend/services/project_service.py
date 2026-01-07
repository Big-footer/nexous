"""
Project Service

프로젝트 CRUD 관리 (파일 시스템 기반)
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import yaml
import json
import os


class ProjectService:
    """프로젝트 관리 서비스"""
    
    def __init__(self, projects_dir: str = "projects"):
        self.projects_dir = Path(projects_dir)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """프로젝트 목록 조회"""
        projects = []
        
        for item in self.projects_dir.iterdir():
            if item.is_dir():
                project_yaml = item / "project.yaml"
                if project_yaml.exists():
                    try:
                        with open(project_yaml, 'r', encoding='utf-8') as f:
                            data = yaml.safe_load(f) or {}
                        
                        stat = project_yaml.stat()
                        projects.append({
                            "id": item.name,
                            "name": data.get("name", item.name),
                            "description": data.get("description", ""),
                            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
                    except Exception:
                        projects.append({
                            "id": item.name,
                            "name": item.name,
                            "description": "",
                            "modified_at": None
                        })
        
        return sorted(projects, key=lambda x: x.get("modified_at") or "", reverse=True)
    
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """프로젝트 조회"""
        self._validate_path(project_id)
        
        project_yaml = self.projects_dir / project_id / "project.yaml"
        if not project_yaml.exists():
            return None
        
        with open(project_yaml, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return {
            "id": project_id,
            "content": data,
            "yaml_content": project_yaml.read_text(encoding='utf-8')
        }
    
    def create_project(self, project_id: str, name: str = None, description: str = None) -> Dict[str, Any]:
        """프로젝트 생성"""
        self._validate_path(project_id)
        
        project_dir = self.projects_dir / project_id
        if project_dir.exists():
            raise ValueError(f"Project already exists: {project_id}")
        
        project_dir.mkdir(parents=True)
        
        # 기본 project.yaml 생성
        default_content = {
            "project_id": project_id,
            "name": name or project_id,
            "description": description or "",
            "execution": {"mode": "sequential"},
            "agents": [
                {
                    "id": "agent_01",
                    "preset": "planner",
                    "purpose": "분석 계획 수립"
                }
            ]
        }
        
        project_yaml = project_dir / "project.yaml"
        with open(project_yaml, 'w', encoding='utf-8') as f:
            yaml.dump(default_content, f, allow_unicode=True, default_flow_style=False)
        
        return {"id": project_id, "name": name or project_id}
    
    def update_project(self, project_id: str, yaml_content: str) -> Dict[str, Any]:
        """프로젝트 업데이트"""
        self._validate_path(project_id)
        
        project_yaml = self.projects_dir / project_id / "project.yaml"
        if not project_yaml.exists():
            raise ValueError(f"Project not found: {project_id}")
        
        # YAML 파싱 검증
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")
        
        # 스키마 검증
        self._validate_project_schema(data)
        
        # 저장
        with open(project_yaml, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        return {"id": project_id, "status": "saved"}
    
    def delete_project(self, project_id: str) -> Dict[str, Any]:
        """프로젝트 삭제"""
        self._validate_path(project_id)
        
        project_dir = self.projects_dir / project_id
        if not project_dir.exists():
            raise ValueError(f"Project not found: {project_id}")
        
        import shutil
        shutil.rmtree(project_dir)
        
        return {"id": project_id, "status": "deleted"}
    
    def validate_yaml(self, yaml_content: str) -> Dict[str, Any]:
        """YAML 검증"""
        try:
            data = yaml.safe_load(yaml_content)
            self._validate_project_schema(data)
            return {"valid": True, "errors": []}
        except Exception as e:
            return {"valid": False, "errors": [str(e)]}
    
    def _validate_path(self, project_id: str):
        """Path traversal 방지"""
        if ".." in project_id or "/" in project_id or "\\" in project_id:
            raise ValueError("Invalid project ID")
    
    def _validate_project_schema(self, data: Dict):
        """프로젝트 스키마 검증"""
        if not data:
            raise ValueError("Empty project")
        
        if "agents" not in data:
            raise ValueError("Missing 'agents' field")
        
        if not isinstance(data["agents"], list):
            raise ValueError("'agents' must be a list")
        
        for i, agent in enumerate(data["agents"]):
            if "id" not in agent:
                raise ValueError(f"Agent {i}: missing 'id'")
            if "preset" not in agent:
                raise ValueError(f"Agent {agent.get('id', i)}: missing 'preset'")
