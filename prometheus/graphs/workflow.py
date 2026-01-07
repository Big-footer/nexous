"""
PROMETHEUS LangGraph 워크플로우

Multi-Agent 협업 워크플로우를 정의합니다.
StateGraph를 사용하여 Agent 간 흐름을 관리합니다.
"""

from typing import Dict, Any, Optional
import json
import os
from datetime import datetime
from pathlib import Path

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from prometheus.graphs.state import AgentState, create_initial_state
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


def create_workflow(checkpointer: bool = True):
    """
    PROMETHEUS 워크플로우 생성
    
    Args:
        checkpointer: 체크포인터 사용 여부
    
    Returns:
        컴파일된 LangGraph
    
    워크플로우 흐름:
        START → meta_agent → planner → executor → writer → (qa) → END
                                          ↓
                                      (retry/error)
    """
    # StateGraph 생성
    builder = StateGraph(AgentState)
    
    # ==========================================================================
    # 노드 추가
    # ==========================================================================
    builder.add_node("meta_agent", meta_agent_node)
    builder.add_node("planner", planner_node)
    builder.add_node("executor", executor_node)
    builder.add_node("writer", writer_node)
    builder.add_node("qa", qa_node)
    builder.add_node("error_handler", error_handler_node)
    
    # ==========================================================================
    # 엣지 추가
    # ==========================================================================
    
    # START → meta_agent
    builder.add_edge(START, "meta_agent")
    
    # meta_agent → planner
    builder.add_edge("meta_agent", "planner")
    
    # planner → executor
    builder.add_edge("planner", "executor")
    
    # executor → (조건부) writer 또는 재시도 또는 에러
    builder.add_conditional_edges(
        "executor",
        should_retry_executor,
        {
            "executor": "executor",  # 재시도
            "writer": "writer",       # 정상 진행
            "error": "error_handler"  # 에러 처리
        }
    )
    
    # writer → (조건부) qa 또는 END
    builder.add_conditional_edges(
        "writer",
        should_run_qa,
        {
            "qa": "qa",
            "end": END
        }
    )
    
    # qa → END
    builder.add_edge("qa", END)
    
    # error_handler → END
    builder.add_edge("error_handler", END)
    
    # ==========================================================================
    # 컴파일
    # ==========================================================================
    if checkpointer:
        memory = MemorySaver()
        graph = builder.compile(checkpointer=memory)
    else:
        graph = builder.compile()
    
    return graph


class PrometheusWorkflow:
    """
    PROMETHEUS 워크플로우 클래스
    
    워크플로우 실행 및 결과 저장을 관리합니다.
    """
    
    def __init__(self, output_dir: str = "runs"):
        """
        초기화
        
        Args:
            output_dir: 결과 저장 디렉토리
        """
        self.output_dir = output_dir
        self.graph = create_workflow()
    
    def run(
        self,
        request: str,
        project_name: str = "unnamed",
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        워크플로우 실행
        
        Args:
            request: 사용자 요청
            project_name: 프로젝트 이름
            config: 추가 설정
        
        Returns:
            최종 State
        """
        # 초기 State 생성
        initial_state = create_initial_state(
            request=request,
            project_name=project_name,
        )
        
        # 실행
        config = config or {}
        config["configurable"] = config.get("configurable", {})
        config["configurable"]["thread_id"] = initial_state["trace_id"]
        
        final_state = self.graph.invoke(initial_state, config)
        
        # 결과 저장
        self._save_outputs(final_state)
        
        return final_state
    
    async def arun(
        self,
        request: str,
        project_name: str = "unnamed",
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        비동기 워크플로우 실행
        
        Args:
            request: 사용자 요청
            project_name: 프로젝트 이름
            config: 추가 설정
        
        Returns:
            최종 State
        """
        initial_state = create_initial_state(
            request=request,
            project_name=project_name,
        )
        
        config = config or {}
        config["configurable"] = config.get("configurable", {})
        config["configurable"]["thread_id"] = initial_state["trace_id"]
        
        final_state = await self.graph.ainvoke(initial_state, config)
        
        self._save_outputs(final_state)
        
        return final_state
    
    def stream(
        self,
        request: str,
        project_name: str = "unnamed",
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        스트리밍 실행
        
        Args:
            request: 사용자 요청
            project_name: 프로젝트 이름
            config: 추가 설정
        
        Yields:
            각 단계의 State 업데이트
        """
        initial_state = create_initial_state(
            request=request,
            project_name=project_name,
        )
        
        config = config or {}
        config["configurable"] = config.get("configurable", {})
        config["configurable"]["thread_id"] = initial_state["trace_id"]
        
        for event in self.graph.stream(initial_state, config):
            yield event
    
    def _save_outputs(self, state: AgentState) -> None:
        """
        결과 저장
        
        Args:
            state: 최종 State
        """
        artifacts_dir = state.get("artifacts_dir", "runs/unknown")
        Path(artifacts_dir).mkdir(parents=True, exist_ok=True)
        
        # project_request.txt
        with open(f"{artifacts_dir}/project_request.txt", "w", encoding="utf-8") as f:
            f.write(state.get("request", ""))
        
        # meta_decision.json
        if state.get("meta_decision"):
            with open(f"{artifacts_dir}/meta_decision.json", "w", encoding="utf-8") as f:
                json.dump(state["meta_decision"], f, ensure_ascii=False, indent=2)
        
        # plan.json
        if state.get("plan"):
            with open(f"{artifacts_dir}/plan.json", "w", encoding="utf-8") as f:
                json.dump(state["plan"], f, ensure_ascii=False, indent=2)
        
        # results.json
        if state.get("execution_result"):
            with open(f"{artifacts_dir}/results.json", "w", encoding="utf-8") as f:
                json.dump(state["execution_result"], f, ensure_ascii=False, indent=2)
        
        # report.md
        if state.get("report"):
            report = state["report"]
            with open(f"{artifacts_dir}/report.md", "w", encoding="utf-8") as f:
                f.write(f"# {report.get('title', 'Report')}\n\n")
                f.write(f"## 요약\n{report.get('summary', '')}\n\n")
                f.write(f"## 본문\n{report.get('content', '')}\n\n")
                if report.get("conclusions"):
                    f.write("## 결론\n")
                    for c in report["conclusions"]:
                        f.write(f"- {c}\n")
        
        # qa_report.json
        if state.get("qa_result"):
            with open(f"{artifacts_dir}/qa_report.json", "w", encoding="utf-8") as f:
                json.dump(state["qa_result"], f, ensure_ascii=False, indent=2)
        
        # environment.json
        env_info = {
            "trace_id": state.get("trace_id"),
            "project_name": state.get("project_name"),
            "start_time": state.get("start_time"),
            "end_time": datetime.now().isoformat(),
            "current_agent": state.get("current_agent"),
            "error": state.get("error"),
        }
        with open(f"{artifacts_dir}/environment.json", "w", encoding="utf-8") as f:
            json.dump(env_info, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 결과 저장 완료: {artifacts_dir}")


# =============================================================================
# CLI 지원
# =============================================================================

def run_workflow_cli(
    request: str,
    project_name: str = "unnamed",
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    CLI에서 워크플로우 실행
    
    Args:
        request: 사용자 요청
        project_name: 프로젝트 이름
        verbose: 상세 출력
    
    Returns:
        최종 State
    """
    workflow = PrometheusWorkflow()
    
    if verbose:
        print("=" * 60)
        print("🔥 PROMETHEUS Multi-Agent Workflow")
        print("=" * 60)
        print(f"📋 요청: {request[:100]}...")
        print(f"📁 프로젝트: {project_name}")
        print("-" * 60)
    
    # 스트리밍 실행
    final_state = None
    for event in workflow.stream(request, project_name):
        for node_name, node_output in event.items():
            if verbose:
                current_agent = node_output.get("current_agent", node_name)
                print(f"✓ {current_agent.upper()} 완료")
            final_state = node_output
    
    if verbose:
        print("-" * 60)
        if final_state:
            print(f"✅ 워크플로우 완료")
            if final_state.get("error"):
                print(f"❌ 에러: {final_state['error']}")
            if final_state.get("qa_result"):
                qa = final_state["qa_result"]
                print(f"📊 QA 점수: {qa.get('score', 0)}점")
        print("=" * 60)
    
    return final_state


if __name__ == "__main__":
    # 테스트 실행
    result = run_workflow_cli(
        request="Python으로 피보나치 수열을 계산하고 결과를 분석해주세요.",
        project_name="fibonacci_test",
    )
