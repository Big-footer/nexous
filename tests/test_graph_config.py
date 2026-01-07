"""
Graph Configuration Schema 테스트
"""

import pytest
from prometheus.graphs.config import (
    GraphConfig,
    NodeConfig,
    EdgeConfig,
    LLMConfig,
    NodeType,
    EdgeType,
    LLMProviderType,
    ConditionalBranch,
    create_default_prometheus_config,
    create_simple_config,
)


class TestLLMConfig:
    """LLMConfig 테스트"""
    
    def test_default_config(self):
        """기본 설정"""
        config = LLMConfig()
        assert config.provider == LLMProviderType.AUTO
        assert config.temperature == 0.7
    
    def test_custom_config(self):
        """커스텀 설정"""
        config = LLMConfig(
            provider=LLMProviderType.OPENAI,
            model="gpt-4o",
            temperature=0.5,
        )
        assert config.provider == LLMProviderType.OPENAI
        assert config.model == "gpt-4o"


class TestNodeConfig:
    """NodeConfig 테스트"""
    
    def test_agent_node(self):
        """Agent 노드"""
        node = NodeConfig(
            id="planner",
            type=NodeType.AGENT,
            agent_class="PlannerAgent",
        )
        assert node.id == "planner"
        assert node.type == NodeType.AGENT
        assert node.enabled == True
    
    def test_function_node(self):
        """Function 노드"""
        node = NodeConfig(
            id="error_handler",
            type=NodeType.FUNCTION,
            function="handle_error",
        )
        assert node.type == NodeType.FUNCTION
        assert node.function == "handle_error"
    
    def test_invalid_id_empty(self):
        """빈 ID 거부"""
        with pytest.raises(ValueError):
            NodeConfig(id="", type=NodeType.AGENT)
    
    def test_invalid_id_reserved(self):
        """예약어 ID 거부"""
        with pytest.raises(ValueError):
            NodeConfig(id="__start__", type=NodeType.AGENT)


class TestEdgeConfig:
    """EdgeConfig 테스트"""
    
    def test_direct_edge(self):
        """직접 엣지"""
        edge = EdgeConfig(source="planner", target="executor")
        assert edge.type == EdgeType.DIRECT
        assert edge.source == "planner"
        assert edge.target == "executor"
    
    def test_start_edge(self):
        """시작 엣지"""
        edge = EdgeConfig(source="__start__", target="meta_agent")
        assert edge.source == "__start__"
    
    def test_end_edge(self):
        """종료 엣지"""
        edge = EdgeConfig(source="qa", target="__end__")
        assert edge.target == "__end__"
    
    def test_conditional_edge(self):
        """조건부 엣지"""
        edge = EdgeConfig(
            source="executor",
            type=EdgeType.CONDITIONAL,
            condition_function="should_retry",
            branches=[
                ConditionalBranch(condition="retry", target="executor"),
                ConditionalBranch(condition="continue", target="writer"),
            ],
        )
        assert edge.type == EdgeType.CONDITIONAL
        assert len(edge.branches) == 2


class TestGraphConfig:
    """GraphConfig 테스트"""
    
    def test_basic_config(self):
        """기본 설정"""
        config = GraphConfig(
            name="test_workflow",
            nodes=[
                NodeConfig(id="node1", type=NodeType.AGENT),
                NodeConfig(id="node2", type=NodeType.AGENT),
            ],
            edges=[
                EdgeConfig(source="__start__", target="node1"),
                EdgeConfig(source="node1", target="node2"),
                EdgeConfig(source="node2", target="__end__"),
            ],
        )
        assert config.name == "test_workflow"
        assert len(config.nodes) == 2
        assert len(config.edges) == 3
    
    def test_duplicate_node_ids_rejected(self):
        """중복 노드 ID 거부"""
        with pytest.raises(ValueError):
            GraphConfig(
                nodes=[
                    NodeConfig(id="same_id", type=NodeType.AGENT),
                    NodeConfig(id="same_id", type=NodeType.FUNCTION),
                ],
            )
    
    def test_get_node(self):
        """노드 조회"""
        config = GraphConfig(
            nodes=[
                NodeConfig(id="node1", type=NodeType.AGENT),
                NodeConfig(id="node2", type=NodeType.FUNCTION),
            ],
        )
        node = config.get_node("node1")
        assert node is not None
        assert node.id == "node1"
        
        assert config.get_node("nonexistent") is None
    
    def test_get_enabled_nodes(self):
        """활성화된 노드만 조회"""
        config = GraphConfig(
            nodes=[
                NodeConfig(id="node1", enabled=True),
                NodeConfig(id="node2", enabled=False),
                NodeConfig(id="node3", enabled=True),
            ],
        )
        enabled = config.get_enabled_nodes()
        assert len(enabled) == 2
        assert all(n.enabled for n in enabled)
    
    def test_get_edges_from(self):
        """특정 노드에서 나가는 엣지 조회"""
        config = GraphConfig(
            nodes=[NodeConfig(id="a"), NodeConfig(id="b"), NodeConfig(id="c")],
            edges=[
                EdgeConfig(source="a", target="b"),
                EdgeConfig(source="a", target="c"),
                EdgeConfig(source="b", target="c"),
            ],
        )
        edges = config.get_edges_from("a")
        assert len(edges) == 2
    
    def test_validate_graph_valid(self):
        """유효한 그래프"""
        config = GraphConfig(
            nodes=[
                NodeConfig(id="node1"),
                NodeConfig(id="node2"),
            ],
            edges=[
                EdgeConfig(source="__start__", target="node1"),
                EdgeConfig(source="node1", target="node2"),
                EdgeConfig(source="node2", target="__end__"),
            ],
        )
        errors = config.validate_graph()
        assert len(errors) == 0
    
    def test_validate_graph_no_start(self):
        """시작 엣지 없음"""
        config = GraphConfig(
            nodes=[NodeConfig(id="node1")],
            edges=[EdgeConfig(source="node1", target="__end__")],
        )
        errors = config.validate_graph()
        assert any("__start__" in e for e in errors)
    
    def test_validate_graph_invalid_target(self):
        """존재하지 않는 대상 노드"""
        config = GraphConfig(
            nodes=[NodeConfig(id="node1")],
            edges=[
                EdgeConfig(source="__start__", target="node1"),
                EdgeConfig(source="node1", target="nonexistent"),
            ],
        )
        errors = config.validate_graph()
        assert any("nonexistent" in e for e in errors)


class TestPredefinedConfigs:
    """미리 정의된 설정 테스트"""
    
    def test_default_prometheus_config(self):
        """기본 PROMETHEUS 설정"""
        config = create_default_prometheus_config()
        
        assert config.name == "prometheus_default"
        assert len(config.nodes) == 6  # meta, planner, executor, writer, qa, error
        assert len(config.edges) == 7
        
        # 유효성 검사
        errors = config.validate_graph()
        assert len(errors) == 0
    
    def test_simple_config(self):
        """단순 설정"""
        config = create_simple_config()
        
        assert config.name == "prometheus_simple"
        assert len(config.nodes) == 4  # meta, planner, executor, writer
        
        # QA 노드 없음
        assert config.get_node("qa") is None
        
        # 유효성 검사
        errors = config.validate_graph()
        assert len(errors) == 0
