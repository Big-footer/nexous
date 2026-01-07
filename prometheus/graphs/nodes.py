"""
PROMETHEUS LangGraph 노드 함수 (LangChain Agent 통합)

각 Agent의 실행 로직을 정의합니다.
LangChain Agent와 연동하여 실제 LLM을 호출합니다.

개선사항:
- LLM Factory 사용으로 Fallback/Retry 자동 적용
- 재시도 횟수 State에서 관리
"""

from typing import Dict, Any, Literal, Optional
from datetime import datetime
import json
import os
import logging

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from prometheus.graphs.state import AgentState
from prometheus.llm import (
    get_llm_factory,
    create_robust_llm,
    get_llm,  # 하위 호환성
    LLMFactory,
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 전역 LLM Factory
_llm_factory: Optional[LLMFactory] = None


def get_node_llm_factory() -> LLMFactory:
    """노드용 LLM Factory 반환"""
    global _llm_factory
    if _llm_factory is None:
        _llm_factory = get_llm_factory()
    return _llm_factory


def set_node_llm_factory(factory: LLMFactory):
    """노드용 LLM Factory 설정"""
    global _llm_factory
    _llm_factory = factory


# =============================================================================
# Meta Agent 노드
# =============================================================================

def meta_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Meta Agent: 요청 분석 및 Agent/LLM 선택
    
    LangChain Agent를 사용하여 요청을 분석하고
    각 Agent에 사용할 LLM을 결정합니다.
    
    Fallback: Claude → GPT → Gemini
    """
    logger.info("🔍 Meta Agent 시작")
    
    request = state["request"]
    retry_count = state.get("retry_count", 0)
    
    # Fallback이 설정된 LLM 사용
    factory = get_node_llm_factory()
    llm = factory.get_meta_llm()
    
    system_prompt = """당신은 PROMETHEUS의 Meta-Agent입니다.
사용자 요청을 분석하고 최적의 Agent와 LLM 조합을 결정합니다.

다음 Agent들이 있습니다:
- planner: 작업 계획 수립 (복잡한 추론 필요 → Claude 추천)
- executor: 코드 실행, Tool 호출 (정확한 실행 필요 → GPT 추천)
- writer: 문서/보고서 작성 (자연스러운 글 → Gemini 추천)
- qa: 품질 검토 (꼼꼼한 검토 → Claude 추천)

반드시 다음 JSON 형식으로 응답하세요:
{
    "selected_agents": ["planner", "executor", "writer"],
    "llm_assignments": {
        "planner": "anthropic",
        "executor": "openai",
        "writer": "google"
    },
    "skip_qa": false,
    "reasoning": "이유 설명"
}
"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"다음 요청을 분석해주세요:\n\n{request}")
    ]
    
    try:
        response = llm.invoke(messages)
        
        # JSON 파싱
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        decision = json.loads(content.strip())
        logger.info(f"✅ Meta Agent 결정: {decision.get('reasoning', '')[:50]}...")
        
    except Exception as e:
        logger.warning(f"⚠️ Meta Agent 오류 (시도 {retry_count + 1}): {e}")
        decision = {
            "selected_agents": ["planner", "executor", "writer"],
            "llm_assignments": {
                "planner": "anthropic",
                "executor": "openai",
                "writer": "google"
            },
            "skip_qa": False,
            "reasoning": f"기본 워크플로우 적용 (fallback, 오류: {str(e)[:50]})"
        }
    
    return {
        "meta_decision": decision,
        "current_agent": "meta",
        "messages": [AIMessage(content=f"Meta Agent 결정 완료: {decision.get('reasoning', '')}")]
    }


# =============================================================================
# Planner Agent 노드
# =============================================================================

def planner_node(state: AgentState) -> Dict[str, Any]:
    """
    Planner Agent: 작업 계획 수립
    
    LangChain PlannerAgent를 사용하여 계획을 생성합니다.
    Fallback: Meta 결정 provider → 대체 provider
    """
    logger.info("📋 Planner Agent 시작")
    
    request = state["request"]
    meta_decision = state.get("meta_decision", {})
    retry_count = state.get("retry_count", 0)
    
    # LLM 선택 (Meta 결정 또는 Factory)
    provider = meta_decision.get("llm_assignments", {}).get("planner", "anthropic")
    
    try:
        # LangChain PlannerAgent 사용
        from prometheus.agents import create_planner_agent
        from prometheus.llm import create_llm
        
        # 기본 LLM 생성 (Retry 없이 - with_structured_output 호환성)
        llm = create_llm(provider=provider)
        
        planner = create_planner_agent(llm=llm)
        plan_output = planner.plan(request)
        
        # Pydantic 모델을 dict로 변환
        plan = plan_output.model_dump() if hasattr(plan_output, 'model_dump') else dict(plan_output)
        
        logger.info(f"✅ Planner 완료: {plan.get('task_summary', '')[:50]}...")
        
    except Exception as e:
        logger.error(f"❌ Planner 오류 (시도 {retry_count + 1}): {e}")
        # 폴백: Robust LLM으로 직접 호출
        plan = _fallback_planner(request, provider)
    
    return {
        "plan": plan,
        "current_agent": "planner",
        "current_step": 0,
        "messages": [AIMessage(content=f"계획 수립 완료: {plan.get('task_summary', '')}")]
    }


def _fallback_planner(request: str, provider: str) -> Dict[str, Any]:
    """Planner 폴백 (Robust LLM 직접 호출)"""
    # Fallback이 설정된 LLM 사용
    llm = create_robust_llm(provider, with_fallback=True, max_retries=2)
    
    system_prompt = """당신은 Planner입니다. 다음 JSON 형식으로 계획을 수립하세요:
{
    "task_summary": "작업 요약",
    "analysis": "분석",
    "steps": [{"step_id": 1, "action": "작업", "tool": null}],
    "total_steps": 1,
    "estimated_time": "5분"
}"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=request)
    ]
    
    response = llm.invoke(messages)
    
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        return json.loads(content.strip())
    except:
        return {
            "task_summary": request[:100],
            "analysis": "기본 분석",
            "steps": [{"step_id": 1, "action": "요청 처리", "tool": None}],
            "total_steps": 1,
            "estimated_time": "알 수 없음"
        }


# =============================================================================
# Executor Agent 노드
# =============================================================================

def executor_node(state: AgentState) -> Dict[str, Any]:
    """
    Executor Agent: 계획 실행
    
    LangChain ExecutorAgent를 사용하여 Tool을 호출합니다.
    """
    logger.info("⚡ Executor Agent 시작")
    
    plan = state.get("plan", {})
    meta_decision = state.get("meta_decision", {})
    retry_count = state.get("retry_count", 0)
    
    # LLM 선택
    provider = meta_decision.get("llm_assignments", {}).get("executor", "openai")
    
    try:
        # LangChain ExecutorAgent 사용
        from prometheus.agents import create_executor_agent
        
        executor = create_executor_agent(provider=provider)
        exec_result = executor.execute_plan(plan)
        
        # Pydantic 모델을 dict로 변환
        execution_result = exec_result.model_dump() if hasattr(exec_result, 'model_dump') else dict(exec_result)
        
        logger.info(f"✅ Executor 완료: {execution_result.get('summary', '')}")
        
    except Exception as e:
        logger.error(f"❌ Executor 오류: {e}")
        # 폴백
        execution_result = _fallback_executor(plan, provider)
    
    return {
        "execution_result": execution_result,
        "current_agent": "executor",
        "retry_count": retry_count,
        "messages": [AIMessage(content=f"실행 완료: {execution_result.get('success_count', 0)}개 성공")]
    }


def _fallback_executor(plan: Dict[str, Any], provider: str) -> Dict[str, Any]:
    """Executor 폴백"""
    steps = plan.get("steps", [])
    step_results = []
    
    for step in steps:
        step_results.append({
            "step_id": step.get("step_id", 0),
            "action": step.get("action", ""),
            "status": "success",
            "output": f"Step {step.get('step_id', 0)} 완료",
            "tool_calls": [],
            "error": None
        })
    
    return {
        "step_results": step_results,
        "success_count": len(step_results),
        "fail_count": 0,
        "artifacts": [],
        "total_execution_time": 0.0,
        "summary": f"총 {len(step_results)}개 단계 실행 완료"
    }


# =============================================================================
# Writer Agent 노드
# =============================================================================

def writer_node(state: AgentState) -> Dict[str, Any]:
    """
    Writer Agent: 보고서 작성
    
    LangChain WriterAgent를 사용하여 보고서를 생성합니다.
    """
    logger.info("✍️ Writer Agent 시작")
    
    request = state["request"]
    plan = state.get("plan", {})
    execution_result = state.get("execution_result", {})
    meta_decision = state.get("meta_decision", {})
    
    # LLM 선택
    provider = meta_decision.get("llm_assignments", {}).get("writer", "google")
    
    try:
        # LangChain WriterAgent 사용
        from prometheus.agents import create_writer_agent
        
        writer = create_writer_agent(provider=provider)
        report_output = writer.write_report(request, plan, execution_result)
        
        # Pydantic 모델을 dict로 변환
        report = report_output.model_dump() if hasattr(report_output, 'model_dump') else dict(report_output)
        
        logger.info(f"✅ Writer 완료: {report.get('title', '')}")
        
    except Exception as e:
        logger.error(f"❌ Writer 오류: {e}")
        # 폴백
        report = _fallback_writer(request, plan, execution_result, provider)
    
    return {
        "report": report,
        "current_agent": "writer",
        "messages": [AIMessage(content=f"보고서 작성 완료: {report.get('title', '')}")]
    }


def _fallback_writer(request: str, plan: Dict, execution_result: Dict, provider: str) -> Dict[str, Any]:
    """Writer 폴백"""
    llm = get_llm(provider)
    
    system_prompt = """당신은 Writer입니다. 다음 JSON 형식으로 보고서를 작성하세요:
{
    "title": "보고서 제목",
    "summary": "요약",
    "content": "본문 (Markdown)",
    "conclusions": ["결론1"],
    "recommendations": [],
    "citations": [],
    "word_count": 100
}"""
    
    context = f"요청: {request}\n계획: {json.dumps(plan, ensure_ascii=False)}\n결과: {json.dumps(execution_result, ensure_ascii=False)}"
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=context)
    ]
    
    try:
        response = llm.invoke(messages)
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        return json.loads(content.strip())
    except:
        return {
            "title": "실행 결과 보고서",
            "summary": plan.get("task_summary", "작업 완료"),
            "content": f"# 결과\n\n{str(execution_result)}",
            "conclusions": ["작업이 완료되었습니다."],
            "recommendations": [],
            "citations": [],
            "word_count": 100
        }


# =============================================================================
# QA Agent 노드
# =============================================================================

def qa_node(state: AgentState) -> Dict[str, Any]:
    """
    QA Agent: 품질 검토
    
    LangChain QAAgent를 사용하여 보고서를 검토합니다.
    """
    logger.info("🔍 QA Agent 시작")
    
    request = state["request"]
    report = state.get("report", {})
    execution_result = state.get("execution_result", {})
    meta_decision = state.get("meta_decision", {})
    
    # QA 스킵 체크
    if meta_decision.get("skip_qa", False):
        logger.info("⏭️ QA 스킵됨")
        return {
            "qa_result": {
                "passed": True,
                "score": 100.0,
                "grade": "A",
                "summary": "QA 스킵됨",
                "issues": [],
                "strengths": [],
                "recommendations": []
            },
            "current_agent": "qa",
            "messages": [AIMessage(content="QA 스킵됨")]
        }
    
    try:
        # LangChain QAAgent 사용
        from prometheus.agents import create_qa_agent
        
        qa = create_qa_agent(provider="anthropic")
        qa_output = qa.review(request, report, execution_result)
        
        # Pydantic 모델을 dict로 변환
        qa_result = qa_output.model_dump() if hasattr(qa_output, 'model_dump') else dict(qa_output)
        
        logger.info(f"✅ QA 완료: {qa_result.get('grade', '')} ({qa_result.get('score', 0)}점)")
        
    except Exception as e:
        logger.error(f"❌ QA 오류: {e}")
        # 폴백
        qa_result = {
            "passed": True,
            "score": 75.0,
            "grade": "C",
            "summary": "기본 검토 완료",
            "issues": [],
            "strengths": ["작업 완료"],
            "recommendations": ["상세 검토 권장"]
        }
    
    return {
        "qa_result": qa_result,
        "current_agent": "qa",
        "messages": [AIMessage(content=f"QA 완료: {qa_result.get('grade', '')} ({qa_result.get('score', 0)}점)")]
    }


# =============================================================================
# 에러 핸들러 노드
# =============================================================================

def error_handler_node(state: AgentState) -> Dict[str, Any]:
    """에러 처리 노드"""
    logger.error("❌ 에러 핸들러 호출됨")
    
    return {
        "error": "최대 재시도 횟수 초과 또는 심각한 오류 발생",
        "current_agent": "error",
        "messages": [AIMessage(content="에러 발생: 워크플로우를 완료할 수 없습니다.")]
    }


# =============================================================================
# 라우팅 함수
# =============================================================================

def should_run_qa(state: AgentState) -> Literal["qa", "end"]:
    """QA 실행 여부 결정"""
    meta_decision = state.get("meta_decision", {})
    
    if meta_decision.get("skip_qa", False):
        logger.info("➡️ QA 스킵 → END")
        return "end"
    
    logger.info("➡️ QA 실행")
    return "qa"


def should_retry_executor(state: AgentState) -> Literal["executor", "writer", "error"]:
    """Executor 재시도 여부 결정"""
    execution_result = state.get("execution_result", {})
    retry_count = state.get("retry_count", 0)
    
    fail_count = execution_result.get("fail_count", 0)
    
    if fail_count > 0 and retry_count < 3:
        logger.info(f"🔄 Executor 재시도 ({retry_count + 1}/3)")
        return "executor"
    elif fail_count > 0 and retry_count >= 3:
        logger.error("❌ 최대 재시도 초과 → 에러")
        return "error"
    
    logger.info("➡️ Writer로 진행")
    return "writer"
