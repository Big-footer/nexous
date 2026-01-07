"""
ProjectSchema - 프로젝트 설정 스키마

이 파일의 책임:
- 프로젝트 설정 데이터 구조 정의
- Agent 설정 스키마
- Tool 설정 스키마
- LLM 프로바이더 설정 스키마
- 설정 유효성 검증
"""

from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import yaml


class LLMProvider(str, Enum):
    """LLM 프로바이더"""
    
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


class AgentType(str, Enum):
    """Agent 유형"""
    
    PLANNER = "planner"
    EXECUTOR = "executor"
    WRITER = "writer"
    QA = "qa"


class LLMProviderConfig(BaseModel):
    """LLM 프로바이더 설정"""
    
    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-4-turbo-preview"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = None
    api_key_env: str = "OPENAI_API_KEY"
    
    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """temperature 유효성 검증"""
        if not 0.0 <= v <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")
        return v
    
    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """model 유효성 검증"""
        if not v or not v.strip():
            raise ValueError("model name cannot be empty")
        return v.strip()


class ToolConfig(BaseModel):
    """Tool 설정"""
    
    name: str
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """name 유효성 검증"""
        if not v or not v.strip():
            raise ValueError("tool name cannot be empty")
        return v.strip()


class AgentConfig(BaseModel):
    """Agent 설정"""
    
    agent_type: AgentType
    name: Optional[str] = None
    llm: Optional[LLMProviderConfig] = None
    tools: List[str] = Field(default_factory=list)
    system_prompt: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    
    def model_post_init(self, __context: Any) -> None:
        """초기화 후 처리 - 이름 자동 설정"""
        if self.name is None:
            self.name = f"{self.agent_type.value.capitalize()}Agent"


class MemoryConfig(BaseModel):
    """메모리 설정"""
    
    type: str = "local"
    vector_store: str = "chroma"
    persist_path: Optional[str] = None
    max_context_length: int = 4096
    
    @field_validator("max_context_length")
    @classmethod
    def validate_max_context_length(cls, v: int) -> int:
        """max_context_length 유효성 검증"""
        if v < 256:
            raise ValueError("max_context_length must be at least 256")
        return v


class ProjectMetadata(BaseModel):
    """프로젝트 메타데이터"""
    
    name: str
    description: str = ""
    version: str = "1.0.0"
    author: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """name 유효성 검증"""
        if not v or not v.strip():
            raise ValueError("project name cannot be empty")
        # 프로젝트 이름에 허용되는 문자 검증
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', v.strip()):
            raise ValueError(
                "project name must start with a letter and contain only "
                "letters, numbers, underscores, and hyphens"
            )
        return v.strip()


class ProjectConfig(BaseModel):
    """
    프로젝트 설정 스키마
    
    PROMETHEUS 프로젝트의 전체 설정을 정의합니다.
    YAML 파일로부터 로드되어 사용됩니다.
    """
    
    metadata: ProjectMetadata
    default_llm: LLMProviderConfig = Field(default_factory=LLMProviderConfig)
    agents: List[AgentConfig] = Field(default_factory=list)
    tools: List[ToolConfig] = Field(default_factory=list)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    settings: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator("agents")
    @classmethod
    def validate_agents(cls, v: List[AgentConfig]) -> List[AgentConfig]:
        """agents 유효성 검증 - 중복 타입 체크"""
        agent_types = [agent.agent_type for agent in v]
        if len(agent_types) != len(set(agent_types)):
            raise ValueError("duplicate agent types are not allowed")
        return v
    
    def get_agent_config(
        self,
        agent_type: AgentType,
    ) -> Optional[AgentConfig]:
        """
        Agent 타입으로 설정 조회
        
        Args:
            agent_type: Agent 유형
            
        Returns:
            Agent 설정 또는 None
        """
        for agent in self.agents:
            if agent.agent_type == agent_type:
                return agent
        return None
    
    def get_tool_config(
        self,
        tool_name: str,
    ) -> Optional[ToolConfig]:
        """
        Tool 이름으로 설정 조회
        
        Args:
            tool_name: Tool 이름
            
        Returns:
            Tool 설정 또는 None
        """
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None
    
    def get_enabled_tools(self) -> List[ToolConfig]:
        """
        활성화된 Tool 목록 조회
        
        Returns:
            활성화된 Tool 설정 목록
        """
        return [tool for tool in self.tools if tool.enabled]
    
    def get_setting(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        추가 설정 조회
        
        Args:
            key: 설정 키
            default: 기본값
            
        Returns:
            설정 값 또는 기본값
        """
        return self.settings.get(key, default)
    
    def validate_all(self) -> bool:
        """
        전체 설정 유효성 검증
        
        Returns:
            유효성 여부
        """
        try:
            # Agent에서 참조하는 Tool이 존재하는지 확인
            tool_names = {tool.name for tool in self.tools}
            for agent in self.agents:
                for tool_name in agent.tools:
                    if tool_name not in tool_names:
                        raise ValueError(
                            f"Agent '{agent.name}' references unknown tool '{tool_name}'"
                        )
            return True
        except Exception:
            return False
    
    def to_yaml(self) -> str:
        """
        YAML 문자열로 변환
        
        Returns:
            YAML 문자열
        """
        data = self.model_dump(mode='json')
        return yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    @classmethod
    def from_yaml(cls, yaml_str: str) -> "ProjectConfig":
        """
        YAML 문자열로부터 생성
        
        Args:
            yaml_str: YAML 문자열
            
        Returns:
            ProjectConfig 인스턴스
        """
        data = yaml.safe_load(yaml_str)
        return cls.model_validate(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectConfig":
        """
        딕셔너리로부터 생성
        
        Args:
            data: 설정 딕셔너리
            
        Returns:
            ProjectConfig 인스턴스
        """
        return cls.model_validate(data)
