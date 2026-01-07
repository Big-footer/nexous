"""
PROMETHEUS Graph Configuration Schema

워크플로우 그래프 설정을 위한 Pydantic 스키마입니다.
"""

from typing import Dict, List, Optional, Any, Union, Literal
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class LLMProviderType(str, Enum):
    """LLM 프로바이더 타입"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AUTO = "auto"  # Meta Agent가 결정


class NodeType(str, Enum):
    """노드 타입"""
    AGENT = "agent"           # LangChain Agent
    FUNCTION = "function"     # 일반 함수
    CONDITIONAL = "conditional"  # 조건 분기
    SUBGRAPH = "subgraph"     # 서브 그래프


class EdgeType(str, Enum):
    """엣지 타입"""
    DIRECT = "direct"         # 직접 연결
    CONDITIONAL = "conditional"  # 조건부 연결


# =============================================================================
# Node Configuration
# =============================================================================

class LLMConfig(BaseModel):
    """LLM 설정"""
    provider: LLMProviderType = Field(default=LLMProviderType.AUTO)
    model: Optional[str] = Field(default=None, description="모델명 (없으면 기본값)")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)
    
    model_config = {"use_enum_values": True}


class NodeConfig(BaseModel):
    """노드 설정"""
    id: str = Field(..., description="노드 고유 ID")
    type: NodeType = Field(default=NodeType.AGENT)
    agent_class: Optional[str] = Field(default=None, description="Agent 클래스명")
    function: Optional[str] = Field(default=None, description="함수명 (function 타입)")
    llm: LLMConfig = Field(default_factory=LLMConfig)
    description: str = Field(default="", description="노드 설명")
    enabled: bool = Field(default=True, description="활성화 여부")
    retry_count: int = Field(default=3, ge=0)
    timeout: float = Field(default=300.0, gt=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        if not v or not v.strip():
            raise ValueError("Node ID cannot be empty")
        # 예약어 체크
        reserved = {'__start__', '__end__', 'START', 'END'}
        if v in reserved:
            raise ValueError(f"Node ID '{v}' is reserved")
        return v.strip()


# =============================================================================
# Edge Configuration
# =============================================================================

class ConditionalBranch(BaseModel):
    """조건부 분기"""
    condition: str = Field(..., description="조건 값")
    target: str = Field(..., description="대상 노드 ID")


class EdgeConfig(BaseModel):
    """엣지 설정"""
    source: str = Field(..., description="소스 노드 ID")
    target: Optional[str] = Field(default=None, description="대상 노드 ID (direct)")
    type: EdgeType = Field(default=EdgeType.DIRECT)
    condition_function: Optional[str] = Field(default=None, description="조건 함수명")
    branches: Optional[List[ConditionalBranch]] = Field(default=None, description="조건부 분기")
    
    @field_validator('source')
    @classmethod
    def validate_source(cls, v):
        # __start__ 허용
        if v == '__start__':
            return v
        if not v or not v.strip():
            raise ValueError("Source cannot be empty")
        return v.strip()
    
    @field_validator('target')
    @classmethod
    def validate_target(cls, v):
        if v is None:
            return v
        # __end__ 허용
        if v == '__end__':
            return v
        if not v.strip():
            raise ValueError("Target cannot be empty")
        return v.strip()


# =============================================================================
# Graph Configuration
# =============================================================================

class GraphConfig(BaseModel):
    """
    그래프 전체 설정
    
    Example:
        ```yaml
        name: prometheus_workflow
        version: "1.0"
        nodes:
          - id: meta_agent
            type: agent
            agent_class: MetaAgent
            llm:
              provider: anthropic
          - id: planner
            type: agent
            agent_class: PlannerAgent
        edges:
          - source: __start__
            target: meta_agent
          - source: meta_agent
            target: planner
        ```
    """
    name: str = Field(default="workflow", description="워크플로우 이름")
    version: str = Field(default="1.0", description="버전")
    description: str = Field(default="", description="설명")
    
    # 노드 및 엣지
    nodes: List[NodeConfig] = Field(default_factory=list)
    edges: List[EdgeConfig] = Field(default_factory=list)
    
    # 전역 설정
    default_llm: LLMConfig = Field(default_factory=LLMConfig)
    enable_checkpointer: bool = Field(default=True)
    max_iterations: int = Field(default=50, gt=0)
    
    # 메타데이터
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('nodes')
    @classmethod
    def validate_nodes(cls, v):
        # 중복 ID 체크
        ids = [node.id for node in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate node IDs found")
        return v
    
    def get_node(self, node_id: str) -> Optional[NodeConfig]:
        """노드 ID로 노드 설정 반환"""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_enabled_nodes(self) -> List[NodeConfig]:
        """활성화된 노드만 반환"""
        return [n for n in self.nodes if n.enabled]
    
    def get_edges_from(self, source: str) -> List[EdgeConfig]:
        """특정 노드에서 나가는 엣지들 반환"""
        return [e for e in self.edges if e.source == source]
    
    def validate_graph(self) -> List[str]:
        """
        그래프 유효성 검사
        
        Returns:
            오류 메시지 리스트 (비어있으면 유효)
        """
        errors = []
        node_ids = {n.id for n in self.nodes}
        
        # 시작 노드 확인
        start_edges = [e for e in self.edges if e.source == '__start__']
        if not start_edges:
            errors.append("No edge from __start__ found")
        
        # 엣지 유효성 검사
        for edge in self.edges:
            # 소스 노드 존재 확인
            if edge.source != '__start__' and edge.source not in node_ids:
                errors.append(f"Edge source '{edge.source}' not found in nodes")
            
            # 대상 노드 존재 확인
            if edge.type == EdgeType.DIRECT:
                if edge.target and edge.target != '__end__' and edge.target not in node_ids:
                    errors.append(f"Edge target '{edge.target}' not found in nodes")
            
            # 조건부 엣지 검사
            if edge.type == EdgeType.CONDITIONAL:
                if not edge.branches:
                    errors.append(f"Conditional edge from '{edge.source}' has no branches")
                else:
                    for branch in edge.branches:
                        if branch.target != '__end__' and branch.target not in node_ids:
                            errors.append(f"Branch target '{branch.target}' not found in nodes")
        
        return errors


# =============================================================================
# Predefined Configurations
# =============================================================================

def create_default_prometheus_config() -> GraphConfig:
    """기본 PROMETHEUS 워크플로우 설정 생성"""
    return GraphConfig(
        name="prometheus_default",
        version="1.0",
        description="PROMETHEUS 기본 Multi-Agent 워크플로우",
        nodes=[
            NodeConfig(
                id="meta_agent",
                type=NodeType.AGENT,
                agent_class="MetaAgent",
                llm=LLMConfig(provider=LLMProviderType.ANTHROPIC),
                description="요청 분석 및 Agent/LLM 선택",
            ),
            NodeConfig(
                id="planner",
                type=NodeType.AGENT,
                agent_class="PlannerAgent",
                llm=LLMConfig(provider=LLMProviderType.AUTO),
                description="작업 계획 수립",
            ),
            NodeConfig(
                id="executor",
                type=NodeType.AGENT,
                agent_class="ExecutorAgent",
                llm=LLMConfig(provider=LLMProviderType.AUTO),
                description="계획 실행 및 Tool 호출",
            ),
            NodeConfig(
                id="writer",
                type=NodeType.AGENT,
                agent_class="WriterAgent",
                llm=LLMConfig(provider=LLMProviderType.AUTO),
                description="보고서 작성",
            ),
            NodeConfig(
                id="qa",
                type=NodeType.AGENT,
                agent_class="QAAgent",
                llm=LLMConfig(provider=LLMProviderType.ANTHROPIC),
                description="품질 검토",
            ),
            NodeConfig(
                id="error_handler",
                type=NodeType.FUNCTION,
                function="error_handler_node",
                description="에러 처리",
            ),
        ],
        edges=[
            EdgeConfig(source="__start__", target="meta_agent"),
            EdgeConfig(source="meta_agent", target="planner"),
            EdgeConfig(source="planner", target="executor"),
            EdgeConfig(
                source="executor",
                type=EdgeType.CONDITIONAL,
                condition_function="should_retry_executor",
                branches=[
                    ConditionalBranch(condition="executor", target="executor"),
                    ConditionalBranch(condition="writer", target="writer"),
                    ConditionalBranch(condition="error", target="error_handler"),
                ],
            ),
            EdgeConfig(
                source="writer",
                type=EdgeType.CONDITIONAL,
                condition_function="should_run_qa",
                branches=[
                    ConditionalBranch(condition="qa", target="qa"),
                    ConditionalBranch(condition="end", target="__end__"),
                ],
            ),
            EdgeConfig(source="qa", target="__end__"),
            EdgeConfig(source="error_handler", target="__end__"),
        ],
        default_llm=LLMConfig(provider=LLMProviderType.ANTHROPIC),
        enable_checkpointer=True,
    )


def create_simple_config() -> GraphConfig:
    """단순 워크플로우 설정 (QA 없음)"""
    return GraphConfig(
        name="prometheus_simple",
        version="1.0",
        description="단순화된 워크플로우 (QA 스킵)",
        nodes=[
            NodeConfig(
                id="meta_agent",
                type=NodeType.AGENT,
                agent_class="MetaAgent",
                llm=LLMConfig(provider=LLMProviderType.ANTHROPIC),
            ),
            NodeConfig(
                id="planner",
                type=NodeType.AGENT,
                agent_class="PlannerAgent",
            ),
            NodeConfig(
                id="executor",
                type=NodeType.AGENT,
                agent_class="ExecutorAgent",
            ),
            NodeConfig(
                id="writer",
                type=NodeType.AGENT,
                agent_class="WriterAgent",
            ),
        ],
        edges=[
            EdgeConfig(source="__start__", target="meta_agent"),
            EdgeConfig(source="meta_agent", target="planner"),
            EdgeConfig(source="planner", target="executor"),
            EdgeConfig(source="executor", target="writer"),
            EdgeConfig(source="writer", target="__end__"),
        ],
    )
