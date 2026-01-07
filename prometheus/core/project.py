"""
NEXUS Project System

프로젝트 정의(project.yaml)를 파싱하고 관리합니다.
"""

import os
import yaml
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class ProjectType(str, Enum):
    """프로젝트 유형"""
    GENERAL = "general"
    ACADEMIC_PAPER = "academic_paper"
    DATA_ANALYSIS = "data_analysis"
    CODE_GENERATION = "code_generation"
    REPORT = "report"
    RESEARCH = "research"
    SIMULATION = "simulation"


class AgentSpec(BaseModel):
    """Agent 명세"""
    name: str = Field(description="Agent 이름")
    provider: Optional[str] = Field(default=None, description="LLM 프로바이더")
    config: Dict[str, Any] = Field(default_factory=dict, description="추가 설정")


class OutputSpec(BaseModel):
    """출력 명세"""
    format: str = Field(default="markdown", description="출력 형식")
    style: Optional[str] = Field(default=None, description="스타일 (KCI, IEEE 등)")
    path: Optional[str] = Field(default=None, description="출력 경로")


class ProjectConfig(BaseModel):
    """프로젝트 설정"""
    # 기본 정보
    name: str = Field(description="프로젝트 이름")
    type: ProjectType = Field(default=ProjectType.GENERAL, description="프로젝트 유형")
    description: Optional[str] = Field(default=None, description="설명")
    version: str = Field(default="1.0.0", description="버전")
    
    # 입력
    inputs: Dict[str, Any] = Field(default_factory=dict, description="입력 데이터")
    
    # Agent 구성
    agents: List[Union[str, AgentSpec]] = Field(default_factory=list, description="사용할 Agent")
    
    # 출력
    output: OutputSpec = Field(default_factory=OutputSpec, description="출력 설정")
    
    # 실행 설정
    settings: Dict[str, Any] = Field(default_factory=dict, description="실행 설정")
    
    # 메타데이터
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)


class Project:
    """
    NEXUS Project
    
    프로젝트 정의를 로드하고 관리합니다.
    """
    
    def __init__(self, config: ProjectConfig, base_path: Optional[Path] = None):
        self.config = config
        self.base_path = base_path or Path.cwd()
        self.project_id = self._generate_id()
        
    def _generate_id(self) -> str:
        """프로젝트 ID 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_slug = self.config.name.replace(" ", "_").lower()[:20]
        return f"{name_slug}_{timestamp}"
    
    @classmethod
    def from_yaml(cls, yaml_path: Union[str, Path]) -> "Project":
        """YAML 파일에서 프로젝트 로드"""
        yaml_path = Path(yaml_path)
        
        if not yaml_path.exists():
            raise FileNotFoundError(f"Project file not found: {yaml_path}")
        
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # 기존 PROMETHEUS 형식 변환 (metadata.name 구조)
        if 'metadata' in data and 'name' in data['metadata']:
            old_data = data
            data = {
                'name': old_data['metadata'].get('name', 'unnamed'),
                'type': old_data['metadata'].get('type', 'general'),
                'description': old_data['metadata'].get('description', ''),
                'version': old_data['metadata'].get('version', '1.0.0'),
            }
            
            # agents 변환 (딕셔너리 또는 리스트)
            if 'agents' in old_data:
                agent_list = []
                agents_data = old_data['agents']
                
                if isinstance(agents_data, dict):
                    # 딕셔너리 형식: {agent_name: {enabled: true}}
                    for agent_name, agent_conf in agents_data.items():
                        if isinstance(agent_conf, dict) and agent_conf.get('enabled', True):
                            agent_list.append(agent_name)
                        elif agent_conf is True:
                            agent_list.append(agent_name)
                elif isinstance(agents_data, list):
                    # 리스트 형식: [{agent_type: "planner", name: "ProjectPlanner"}, ...]
                    for agent in agents_data:
                        if isinstance(agent, str):
                            agent_list.append(agent)
                        elif isinstance(agent, dict):
                            # agent_type이 있으면 그걸 사용 (핵심!)
                            if 'agent_type' in agent:
                                agent_list.append(agent['agent_type'])
                            elif 'name' in agent:
                                # name을 소문자로 변환하여 매핑
                                name = agent['name'].lower()
                                # ProjectPlanner -> planner 매핑
                                name_map = {
                                    'projectplanner': 'planner',
                                    'taskexecutor': 'executor',
                                    'documentwriter': 'writer',
                                    'qualityassurance': 'qa',
                                }
                                agent_list.append(name_map.get(name, name))
                
                data['agents'] = agent_list if agent_list else ['planner', 'executor', 'writer', 'qa']
            else:
                data['agents'] = ['planner', 'executor', 'writer', 'qa']
            
            # output 변환
            if 'output' in old_data:
                data['output'] = {
                    'format': old_data['output'].get('format', 'markdown'),
                    'path': old_data['output'].get('directory', 'outputs'),
                }
            
            # settings 복사
            if 'settings' in old_data:
                data['settings'] = old_data['settings']
        
        # Agent 목록 정규화
        if 'agents' in data:
            normalized_agents = []
            for agent in data['agents']:
                if isinstance(agent, str):
                    normalized_agents.append(agent)
                elif isinstance(agent, dict):
                    normalized_agents.append(AgentSpec(**agent))
            data['agents'] = normalized_agents
        else:
            # agents가 없으면 기본값
            data['agents'] = ['planner', 'executor', 'writer', 'qa']
        
        # Output 정규화
        if 'output' in data and isinstance(data['output'], dict):
            data['output'] = OutputSpec(**data['output'])
        
        config = ProjectConfig(**data)
        config.created_at = datetime.now()
        
        return cls(config, base_path=yaml_path.parent)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], base_path: Optional[Path] = None) -> "Project":
        """딕셔너리에서 프로젝트 생성"""
        # Agent 목록 정규화
        if 'agents' in data:
            normalized_agents = []
            for agent in data['agents']:
                if isinstance(agent, str):
                    normalized_agents.append(agent)
                elif isinstance(agent, dict):
                    normalized_agents.append(AgentSpec(**agent))
            data['agents'] = normalized_agents
        
        # Output 정규화
        if 'output' in data and isinstance(data['output'], dict):
            data['output'] = OutputSpec(**data['output'])
        
        config = ProjectConfig(**data)
        config.created_at = datetime.now()
        
        return cls(config, base_path=base_path)
    
    def to_yaml(self, output_path: Optional[Union[str, Path]] = None) -> str:
        """프로젝트를 YAML로 저장"""
        data = self.config.model_dump(exclude_none=True)
        
        # Enum 값 변환
        if 'type' in data:
            data['type'] = data['type'].value if hasattr(data['type'], 'value') else data['type']
        
        # Agent 정규화
        if 'agents' in data:
            data['agents'] = [
                a if isinstance(a, str) else a 
                for a in data['agents']
            ]
        
        yaml_content = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
        
        return yaml_content
    
    def get_input_files(self) -> List[Path]:
        """입력 파일 경로 목록"""
        files = []
        data = self.config.inputs.get('data', [])
        
        if isinstance(data, list):
            for f in data:
                path = self.base_path / f if not Path(f).is_absolute() else Path(f)
                files.append(path)
        
        return files
    
    def get_agent_names(self) -> List[str]:
        """Agent 이름 목록"""
        names = []
        for agent in self.config.agents:
            if isinstance(agent, str):
                names.append(agent)
            elif isinstance(agent, AgentSpec):
                names.append(agent.name)
        return names
    
    def get_output_path(self) -> Path:
        """출력 경로"""
        if self.config.output.path:
            return Path(self.config.output.path)
        return self.base_path / "outputs" / self.project_id
    
    def __repr__(self) -> str:
        return f"Project(name='{self.config.name}', type={self.config.type}, agents={self.get_agent_names()})"


# =============================================================================
# 프로젝트 템플릿
# =============================================================================

PROJECT_TEMPLATES = {
    "academic_paper": {
        "name": "학술 논문 프로젝트",
        "type": "academic_paper",
        "description": "학술 논문 작성 프로젝트",
        "agents": [
            "literature",
            "gis",
            "swmm",
            "visualization",
            "academic_writer",
            "qa"
        ],
        "output": {
            "format": "docx",
            "style": "KCI"
        }
    },
    "data_analysis": {
        "name": "데이터 분석 프로젝트",
        "type": "data_analysis",
        "description": "데이터 분석 및 보고서 작성",
        "agents": [
            "planner",
            "executor",
            "visualization",
            "writer",
            "qa"
        ],
        "output": {
            "format": "markdown"
        }
    },
    "flood_simulation": {
        "name": "침수 시뮬레이션 프로젝트",
        "type": "simulation",
        "description": "SWMM 기반 침수 시뮬레이션",
        "agents": [
            "gis",
            "swmm",
            "visualization",
            "writer"
        ],
        "output": {
            "format": "html"
        }
    }
}


def create_project_from_template(
    template_name: str,
    project_name: str,
    **kwargs
) -> Project:
    """템플릿에서 프로젝트 생성"""
    if template_name not in PROJECT_TEMPLATES:
        raise ValueError(f"Unknown template: {template_name}")
    
    template = PROJECT_TEMPLATES[template_name].copy()
    template["name"] = project_name
    template.update(kwargs)
    
    return Project.from_dict(template)
