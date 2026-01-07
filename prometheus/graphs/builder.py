"""
PROMETHEUS Graph Builder

설정 기반으로 LangGraph 워크플로우를 동적으로 생성합니다.
"""

from typing import Dict, Any, Optional, Callable, Type, Union
import importlib
import logging
import json
from pathlib import Path

import yaml
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from prometheus.graphs.state import AgentState
from prometheus.graphs.config import (
    GraphConfig,
    NodeConfig,
    EdgeConfig,
    NodeType,
    EdgeType,
    LLMProviderType,
    create_default_prometheus_config,
    create_simple_config,
)

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Agent 레지스트리
    
    Agent 클래스와 노드 함수를 등록하고 검색합니다.
    새 Agent를 추가할 때 이 레지스트리에 등록하면 됩니다.
    
    Example:
        ```python
        registry = get_registry()
        
        # 커스텀 Agent 등록
        registry.register_agent("MyCustomAgent", MyCustomAgent)
        registry.register_node_function("my_custom_node", my_custom_node_func)
        ```
    """
    
    def __init__(self):
        self._agents: Dict[str, Type] = {}
        self._node_functions: Dict[str, Callable] = {}
        self._condition_functions: Dict[str, Callable] = {}
        self._tools: Dict[str, Any] = {}
        
        # 기본 등록
        self._register_defaults()
    
    def _register_defaults(self):
        """기본 Agent, 함수, Tool 등록"""
        # Agent 클래스
        try:
            from prometheus.agents import (
                PlannerAgent,
                ExecutorAgent,
                WriterAgent,
                QAAgent,
            )
            self._agents["PlannerAgent"] = PlannerAgent
            self._agents["ExecutorAgent"] = ExecutorAgent
            self._agents["WriterAgent"] = WriterAgent
            self._agents["QAAgent"] = QAAgent
        except ImportError as e:
            logger.warning(f"Agent import 실패: {e}")
        
        # 노드 함수
        try:
            from prometheus.graphs.nodes import (
                meta_agent_node,
                planner_node,
                executor_node,
                writer_node,
                qa_node,
                error_handler_node,
                should_run_qa,
                should_retry_executor,
            )
            # Agent 클래스명과 노드 함수 매핑
            self._node_functions["MetaAgent"] = meta_agent_node
            self._node_functions["PlannerAgent"] = planner_node
            self._node_functions["ExecutorAgent"] = executor_node
            self._node_functions["WriterAgent"] = writer_node
            self._node_functions["QAAgent"] = qa_node
            
            # 일반 함수명으로도 등록
            self._node_functions["meta_agent_node"] = meta_agent_node
            self._node_functions["planner_node"] = planner_node
            self._node_functions["executor_node"] = executor_node
            self._node_functions["writer_node"] = writer_node
            self._node_functions["qa_node"] = qa_node
            self._node_functions["error_handler_node"] = error_handler_node
            
            # 조건 함수
            self._condition_functions["should_run_qa"] = should_run_qa
            self._condition_functions["should_retry_executor"] = should_retry_executor
        except ImportError as e:
            logger.warning(f"Node function import 실패: {e}")
        
        # Tool
        try:
            from prometheus.agents import (
                python_exec,
                file_write,
                file_read,
                web_search,
                rag_search,
            )
            self._tools["python_exec"] = python_exec
            self._tools["file_write"] = file_write
            self._tools["file_read"] = file_read
            self._tools["web_search"] = web_search
            self._tools["rag_search"] = rag_search
        except ImportError as e:
            logger.warning(f"Tool import 실패: {e}")
    
    def register_agent(self, name: str, agent_class: Type):
        """Agent 클래스 등록"""
        self._agents[name] = agent_class
        logger.debug(f"Agent 등록: {name}")
    
    def register_node_function(self, name: str, func: Callable):
        """노드 함수 등록"""
        self._node_functions[name] = func
        logger.debug(f"노드 함수 등록: {name}")
    
    def register_condition_function(self, name: str, func: Callable):
        """조건 함수 등록"""
        self._condition_functions[name] = func
        logger.debug(f"조건 함수 등록: {name}")
    
    def register_tool(self, name: str, tool: Any):
        """Tool 등록"""
        self._tools[name] = tool
        logger.debug(f"Tool 등록: {name}")
    
    def get_agent(self, name: str) -> Optional[Type]:
        """Agent 클래스 반환"""
        return self._agents.get(name)
    
    def get_node_function(self, name: str) -> Optional[Callable]:
        """노드 함수 반환"""
        return self._node_functions.get(name)
    
    def get_condition_function(self, name: str) -> Optional[Callable]:
        """조건 함수 반환"""
        return self._condition_functions.get(name)
    
    def get_tool(self, name: str) -> Optional[Any]:
        """Tool 반환"""
        return self._tools.get(name)
    
    def get_tools(self, names: list) -> list:
        """여러 Tool 반환"""
        return [self._tools[n] for n in names if n in self._tools]
    
    def list_agents(self) -> list:
        """등록된 Agent 목록"""
        return list(self._agents.keys())
    
    def list_node_functions(self) -> list:
        """등록된 노드 함수 목록"""
        return list(self._node_functions.keys())
    
    def list_condition_functions(self) -> list:
        """등록된 조건 함수 목록"""
        return list(self._condition_functions.keys())
    
    def list_tools(self) -> list:
        """등록된 Tool 목록"""
        return list(self._tools.keys())
    
    def import_function(self, path: str) -> Optional[Callable]:
        """경로에서 함수 동적 import"""
        try:
            module_path, func_name = path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return getattr(module, func_name)
        except (ValueError, ImportError, AttributeError) as e:
            logger.error(f"함수 import 실패 ({path}): {e}")
            return None


# 전역 레지스트리
_global_registry: Optional[AgentRegistry] = None


def get_registry() -> AgentRegistry:
    """전역 레지스트리 반환"""
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistry()
    return _global_registry


def reset_registry():
    """레지스트리 초기화"""
    global _global_registry
    _global_registry = None


class GraphBuilder:
    """
    설정 기반 그래프 빌더
    
    GraphConfig를 받아 LangGraph StateGraph를 생성합니다.
    
    Example:
        ```python
        # 기본 설정으로 빌드
        config = create_default_prometheus_config()
        builder = GraphBuilder(config)
        graph = builder.build()
        
        # YAML에서 로드
        config = GraphBuilder.load_config("workflow.yaml")
        graph = GraphBuilder(config).build()
        
        # 시각화
        print(builder.visualize())
        ```
    """
    
    def __init__(
        self,
        config: GraphConfig,
        registry: Optional[AgentRegistry] = None,
    ):
        """
        초기화
        
        Args:
            config: 워크플로우 설정
            registry: Agent 레지스트리 (없으면 전역 사용)
        """
        self.config = config
        self.registry = registry or get_registry()
        
        # 유효성 검사
        errors = config.validate_graph()
        if errors:
            raise ValueError(f"Invalid graph config: {errors}")
    
    def build(self, compile: bool = True):
        """
        그래프 빌드
        
        Args:
            compile: 컴파일 여부 (True면 CompiledGraph 반환)
        
        Returns:
            StateGraph 또는 CompiledGraph
        """
        logger.info(f"🔨 그래프 빌드 시작: {self.config.name}")
        
        # StateGraph 생성
        builder = StateGraph(AgentState)
        
        # 활성화된 노드만 추가
        enabled_nodes = self.config.get_enabled_nodes()
        for node_config in enabled_nodes:
            self._add_node(builder, node_config)
        
        # 엣지 추가
        for edge_config in self.config.edges:
            self._add_edge(builder, edge_config)
        
        logger.info(f"✅ 그래프 빌드 완료: {len(enabled_nodes)} 노드, {len(self.config.edges)} 엣지")
        
        # 컴파일
        if compile:
            if self.config.enable_checkpointer:
                return builder.compile(checkpointer=MemorySaver())
            else:
                return builder.compile()
        
        return builder
    
    def _add_node(self, builder: StateGraph, node_config: NodeConfig):
        """노드 추가"""
        node_id = node_config.id
        
        # 노드 함수 결정
        if node_config.type == NodeType.AGENT:
            # Agent 노드: agent_class로 노드 함수 찾기
            func = self.registry.get_node_function(node_config.agent_class)
            if func is None:
                raise ValueError(f"Node function not found for agent: {node_config.agent_class}")
        
        elif node_config.type == NodeType.FUNCTION:
            # Function 노드: 함수명으로 찾기
            func = self.registry.get_node_function(node_config.function)
            if func is None:
                # 동적 import 시도
                func = self.registry.import_function(node_config.function)
            if func is None:
                raise ValueError(f"Function not found: {node_config.function}")
        
        else:
            raise ValueError(f"Unsupported node type: {node_config.type}")
        
        builder.add_node(node_id, func)
        logger.debug(f"노드 추가: {node_id} ({node_config.type.value})")
    
    def _add_edge(self, builder: StateGraph, edge_config: EdgeConfig):
        """엣지 추가"""
        source = START if edge_config.source == "__start__" else edge_config.source
        
        if edge_config.type == EdgeType.DIRECT:
            # 직접 연결
            target = END if edge_config.target == "__end__" else edge_config.target
            builder.add_edge(source, target)
            logger.debug(f"엣지 추가: {source} → {target}")
        
        elif edge_config.type == EdgeType.CONDITIONAL:
            # 조건부 연결
            condition_func = self.registry.get_condition_function(edge_config.condition_function)
            if condition_func is None:
                raise ValueError(f"Condition function not found: {edge_config.condition_function}")
            
            # 브랜치 매핑
            path_map = {}
            for branch in edge_config.branches:
                target = END if branch.target == "__end__" else branch.target
                path_map[branch.condition] = target
            
            builder.add_conditional_edges(source, condition_func, path_map)
            logger.debug(f"조건부 엣지 추가: {source} → {path_map}")
    
    def get_node_info(self, node_id: str) -> Optional[Dict[str, Any]]:
        """노드 정보 반환"""
        node_config = self.config.get_node(node_id)
        if node_config:
            return node_config.model_dump()
        return None
    
    def visualize(self, format: str = "mermaid") -> str:
        """
        그래프 시각화
        
        Args:
            format: "mermaid" 또는 "text"
        
        Returns:
            시각화 문자열
        """
        if format == "mermaid":
            return self._visualize_mermaid()
        else:
            return self._visualize_text()
    
    def _visualize_mermaid(self) -> str:
        """Mermaid 형식 시각화"""
        lines = ["graph TD"]
        
        for edge in self.config.edges:
            source = "START" if edge.source == "__start__" else edge.source
            
            if edge.type == EdgeType.DIRECT:
                target = "END" if edge.target == "__end__" else edge.target
                lines.append(f"    {source} --> {target}")
            else:
                for branch in edge.branches:
                    target = "END" if branch.target == "__end__" else branch.target
                    lines.append(f"    {source} -->|{branch.condition}| {target}")
        
        return "\n".join(lines)
    
    def _visualize_text(self) -> str:
        """텍스트 형식 시각화"""
        lines = [f"Workflow: {self.config.name} (v{self.config.version})", ""]
        
        lines.append("Nodes:")
        for node in self.config.nodes:
            status = "✓" if node.enabled else "✗"
            lines.append(f"  [{status}] {node.id} ({node.type.value})")
        
        lines.append("")
        lines.append("Edges:")
        for edge in self.config.edges:
            if edge.type == EdgeType.DIRECT:
                lines.append(f"  {edge.source} → {edge.target}")
            else:
                branches = ", ".join([f"{b.condition}:{b.target}" for b in edge.branches])
                lines.append(f"  {edge.source} → [{branches}]")
        
        return "\n".join(lines)
    
    @staticmethod
    def load_config(path: Union[str, Path]) -> GraphConfig:
        """
        파일에서 설정 로드
        
        Args:
            path: YAML 또는 JSON 파일 경로
        
        Returns:
            GraphConfig
        """
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            if path.suffix in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            elif path.suffix == '.json':
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported config format: {path.suffix}")
        
        return GraphConfig(**data)
    
    @staticmethod
    def save_config(config: GraphConfig, path: Union[str, Path]):
        """
        설정을 파일로 저장
        
        Args:
            config: GraphConfig
            path: 저장 경로
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = config.model_dump()
        
        with open(path, 'w', encoding='utf-8') as f:
            if path.suffix in ['.yaml', '.yml']:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            elif path.suffix == '.json':
                json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                raise ValueError(f"Unsupported config format: {path.suffix}")


# =============================================================================
# 편의 함수
# =============================================================================

def build_workflow_from_config(config: GraphConfig):
    """설정에서 워크플로우 빌드"""
    builder = GraphBuilder(config)
    return builder.build()


def build_default_workflow():
    """기본 워크플로우 빌드"""
    config = create_default_prometheus_config()
    return build_workflow_from_config(config)


def build_simple_workflow():
    """단순 워크플로우 빌드 (QA 없음)"""
    config = create_simple_config()
    return build_workflow_from_config(config)


def build_workflow_from_yaml(path: str):
    """YAML 파일에서 워크플로우 빌드"""
    config = GraphBuilder.load_config(path)
    return build_workflow_from_config(config)


def build_workflow_from_json(path: str):
    """JSON 파일에서 워크플로우 빌드"""
    config = GraphBuilder.load_config(path)
    return build_workflow_from_config(config)
