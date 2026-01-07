"""
LangGraph 워크플로우 테스트
"""

import pytest
from prometheus.graphs import (
    create_workflow,
    create_initial_state,
    PrometheusWorkflow,
    AgentState,
)


class TestState:
    """State 스키마 테스트"""
    
    def test_create_initial_state(self):
        """초기 상태 생성 테스트"""
        state = create_initial_state("테스트 요청", "test_project")
        
        assert state["request"] == "테스트 요청"
        assert state["project_name"] == "test_project"
        assert state["trace_id"] is not None
        assert len(state["trace_id"]) == 8
        assert "runs/" in state["artifacts_dir"]
    
    def test_initial_state_defaults(self):
        """초기 상태 기본값 테스트"""
        state = create_initial_state("test", "proj")
        
        assert state["meta_decision"] is None
        assert state["plan"] is None
        assert state["execution_result"] is None
        assert state["report"] is None
        assert state["qa_result"] is None
        assert state["retry_count"] == 0
        assert state["error"] is None


class TestWorkflow:
    """워크플로우 테스트"""
    
    def test_create_workflow(self):
        """워크플로우 생성 테스트"""
        workflow = create_workflow(checkpointer=False)
        
        assert workflow is not None
        assert len(workflow.nodes) == 7  # 6 agents + error_handler
    
    def test_workflow_nodes_exist(self):
        """워크플로우 노드 존재 확인"""
        workflow = create_workflow(checkpointer=False)
        
        expected_nodes = [
            "meta_agent", "planner", "executor",
            "writer", "qa", "error_handler"
        ]
        
        for node_name in expected_nodes:
            assert node_name in workflow.nodes
    
    def test_prometheus_workflow_class(self):
        """PrometheusWorkflow 클래스 테스트"""
        pw = PrometheusWorkflow(output_dir="runs_test")
        
        assert pw.output_dir == "runs_test"
        assert pw.graph is not None


class TestNodes:
    """노드 함수 테스트 (Mock)"""
    
    def test_meta_agent_node_import(self):
        """meta_agent_node import 테스트"""
        from prometheus.graphs.nodes import meta_agent_node
        assert callable(meta_agent_node)
    
    def test_planner_node_import(self):
        """planner_node import 테스트"""
        from prometheus.graphs.nodes import planner_node
        assert callable(planner_node)
    
    def test_executor_node_import(self):
        """executor_node import 테스트"""
        from prometheus.graphs.nodes import executor_node
        assert callable(executor_node)
    
    def test_writer_node_import(self):
        """writer_node import 테스트"""
        from prometheus.graphs.nodes import writer_node
        assert callable(writer_node)
    
    def test_qa_node_import(self):
        """qa_node import 테스트"""
        from prometheus.graphs.nodes import qa_node
        assert callable(qa_node)
    
    def test_routing_functions(self):
        """라우팅 함수 테스트"""
        from prometheus.graphs.nodes import should_run_qa, should_retry_executor
        
        assert callable(should_run_qa)
        assert callable(should_retry_executor)
