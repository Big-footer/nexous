"""
통합 테스트 (API 키 필요)

실제 LLM을 호출하는 테스트입니다.
API 키가 없으면 스킵됩니다.
"""

import pytest
import os


# API 키가 없으면 스킵
def requires_api_keys():
    """API 키 필요 마커"""
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    return pytest.mark.skipif(
        not (has_openai or has_anthropic),
        reason="API keys not available"
    )


@pytest.mark.e2e
@pytest.mark.integration
class TestLLMIntegration:
    """LLM 통합 테스트"""
    
    @pytest.fixture(autouse=True)
    def setup(self, setup_env):
        """환경 설정"""
        pass
    
    @requires_api_keys()
    def test_get_llm_openai(self):
        """OpenAI LLM 생성 테스트"""
        if not os.environ.get("OPENAI_API_KEY"):
            pytest.skip("OpenAI API key not set")
        
        from prometheus.graphs.nodes import get_llm
        
        llm = get_llm("openai", "gpt-4o-mini")
        assert llm is not None
    
    @requires_api_keys()
    def test_get_llm_anthropic(self):
        """Anthropic LLM 생성 테스트"""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("Anthropic API key not set")
        
        from prometheus.graphs.nodes import get_llm
        
        llm = get_llm("anthropic", "claude-3-5-haiku-20241022")
        assert llm is not None


@pytest.mark.integration
@pytest.mark.slow
class TestWorkflowIntegration:
    """워크플로우 통합 테스트"""
    
    @pytest.fixture(autouse=True)
    def setup(self, setup_env):
        """환경 설정"""
        pass
    
    @requires_api_keys()
    def test_simple_workflow(self):
        """간단한 워크플로우 테스트"""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("Anthropic API key required for Meta Agent")
        
        from prometheus.graphs import PrometheusWorkflow
        
        workflow = PrometheusWorkflow(output_dir="runs_test")
        
        # 간단한 요청으로 테스트
        result = None
        for event in workflow.stream("1+1은 얼마인가요?", "test"):
            for node_name, node_output in event.items():
                result = node_output
        
        assert result is not None
        # 최소한 plan이나 report가 있어야 함
        assert result.get("plan") is not None or result.get("report") is not None


@pytest.mark.integration
class TestAgentIntegration:
    """Agent 통합 테스트"""
    
    @pytest.fixture(autouse=True)
    def setup(self, setup_env):
        """환경 설정"""
        pass
    
    @requires_api_keys()
    def test_planner_agent_real(self):
        """PlannerAgent 실제 테스트"""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("Anthropic API key required")
        
        from prometheus.agents import create_planner_agent
        
        planner = create_planner_agent(provider="anthropic")
        plan = planner.plan("간단한 계산: 1+1")
        
        assert plan is not None
        assert plan.task_summary is not None
        assert len(plan.steps) > 0
    
    @requires_api_keys()
    def test_qa_agent_real(self, sample_plan, sample_execution_result):
        """QAAgent 실제 테스트"""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("Anthropic API key required")
        
        from prometheus.agents import create_qa_agent
        
        qa = create_qa_agent(provider="anthropic")
        
        report = {
            "title": "테스트 보고서",
            "summary": "테스트 요약",
            "content": "테스트 내용",
            "conclusions": ["결론 1"],
        }
        
        result = qa.review("테스트 요청", report)
        
        assert result is not None
        assert result.score >= 0
        assert result.grade in ["A", "B", "C", "D", "F"]
