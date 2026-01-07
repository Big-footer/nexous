"""
LangChain Agent 테스트
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


class TestAgentImports:
    """Agent Import 테스트"""
    
    def test_base_agent_import(self):
        """BaseLangChainAgent import"""
        from prometheus.agents import BaseLangChainAgent, AgentConfig, AgentRole
        assert BaseLangChainAgent is not None
        assert AgentConfig is not None
        assert AgentRole is not None
    
    def test_planner_agent_import(self):
        """PlannerAgent import"""
        from prometheus.agents import PlannerAgent, PlanOutput, PlanStep
        assert PlannerAgent is not None
        assert PlanOutput is not None
        assert PlanStep is not None
    
    def test_executor_agent_import(self):
        """ExecutorAgent import"""
        from prometheus.agents import ExecutorAgent, ExecutionResult, StepResult
        assert ExecutorAgent is not None
        assert ExecutionResult is not None
        assert StepResult is not None
    
    def test_writer_agent_import(self):
        """WriterAgent import"""
        from prometheus.agents import WriterAgent, ReportOutput, Citation
        assert WriterAgent is not None
        assert ReportOutput is not None
        assert Citation is not None
    
    def test_qa_agent_import(self):
        """QAAgent import"""
        from prometheus.agents import QAAgent, QAResult, QAIssue
        assert QAAgent is not None
        assert QAResult is not None
        assert QAIssue is not None
    
    def test_factory_functions_import(self):
        """팩토리 함수 import"""
        from prometheus.agents import (
            create_planner_agent,
            create_executor_agent,
            create_writer_agent,
            create_qa_agent,
            create_all_agents,
        )
        assert callable(create_planner_agent)
        assert callable(create_executor_agent)
        assert callable(create_writer_agent)
        assert callable(create_qa_agent)
        assert callable(create_all_agents)


class TestAgentConfig:
    """AgentConfig 테스트"""
    
    def test_default_config(self):
        """기본 설정 테스트"""
        from prometheus.agents import AgentConfig, AgentRole
        
        config = AgentConfig()
        assert config.name == "BaseAgent"
        assert config.role == AgentRole.META
        assert config.temperature == 0.7
        assert config.max_tokens == 2000
    
    def test_custom_config(self):
        """커스텀 설정 테스트"""
        from prometheus.agents import AgentConfig, AgentRole
        
        config = AgentConfig(
            name="CustomAgent",
            role=AgentRole.PLANNER,
            temperature=0.5,
            max_tokens=4000,
        )
        assert config.name == "CustomAgent"
        assert config.role == AgentRole.PLANNER
        assert config.temperature == 0.5
        assert config.max_tokens == 4000


class TestPydanticModels:
    """Pydantic 모델 테스트"""
    
    def test_plan_step_model(self):
        """PlanStep 모델 테스트"""
        from prometheus.agents import PlanStep
        
        step = PlanStep(
            step_id=1,
            action="테스트 작업",
            tool="python_exec",
            expected_output="결과",
        )
        assert step.step_id == 1
        assert step.action == "테스트 작업"
        assert step.tool == "python_exec"
    
    def test_plan_output_model(self):
        """PlanOutput 모델 테스트"""
        from prometheus.agents import PlanOutput, PlanStep
        
        plan = PlanOutput(
            task_summary="테스트 작업",
            analysis="분석 결과",
            steps=[
                PlanStep(step_id=1, action="Step 1", expected_output="결과")
            ],
            total_steps=1,
        )
        assert plan.task_summary == "테스트 작업"
        assert len(plan.steps) == 1
    
    def test_qa_result_model(self):
        """QAResult 모델 테스트"""
        from prometheus.agents import QAResult
        
        result = QAResult(
            passed=True,
            score=85.0,
            grade="B",
            summary="검토 완료",
        )
        assert result.passed is True
        assert result.score == 85.0
        assert result.grade == "B"


class TestDefaultTools:
    """기본 Tool 테스트"""
    
    def test_default_tools_exist(self):
        """기본 Tool 존재 확인"""
        from prometheus.agents import (
            python_exec,
            file_write,
            file_read,
            web_search,
            rag_search,
            DEFAULT_TOOLS,
        )
        assert python_exec is not None
        assert file_write is not None
        assert file_read is not None
        assert web_search is not None
        assert rag_search is not None
        assert len(DEFAULT_TOOLS) == 5
    
    def test_python_exec_tool(self):
        """python_exec Tool 테스트"""
        from prometheus.agents import python_exec
        
        result = python_exec.invoke({"code": "print(1 + 1)"})
        assert "2" in result
    
    def test_file_operations_tool(self):
        """file 작업 Tool 테스트"""
        from prometheus.agents import file_write, file_read
        import tempfile
        import os
        
        # 임시 파일에 쓰기
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name
        
        try:
            # 쓰기
            write_result = file_write.invoke({
                "filepath": temp_path,
                "content": "테스트 내용"
            })
            assert "완료" in write_result
            
            # 읽기
            read_result = file_read.invoke({"filepath": temp_path})
            assert "테스트 내용" in read_result
        finally:
            os.unlink(temp_path)
