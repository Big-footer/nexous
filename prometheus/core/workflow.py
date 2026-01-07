"""
NEXUS Dynamic Workflow Builder

project.yaml 기반으로 워크플로우를 자동 구성합니다.
"""

import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from prometheus.core.project import Project, ProjectConfig
from prometheus.core.registry import get_registry, AgentRegistry
from prometheus.core.artifact import get_artifact_manager, ArtifactManager
from prometheus.core.trace import create_trace, get_trace_store, Trace, TraceStore
from prometheus.graphs.state import AgentState

logger = logging.getLogger(__name__)


class WorkflowBuilder:
    """
    Dynamic Workflow Builder
    
    프로젝트 정의에 따라 워크플로우를 자동 구성합니다.
    """
    
    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        artifact_manager: Optional[ArtifactManager] = None,
        trace_store: Optional[TraceStore] = None,
    ):
        self.registry = registry or get_registry()
        self.artifact_manager = artifact_manager or get_artifact_manager()
        self.trace_store = trace_store or get_trace_store()
    
    def build(self, project: Project) -> StateGraph:
        """
        프로젝트에서 워크플로우 구성
        
        Args:
            project: Project 인스턴스
        
        Returns:
            LangGraph StateGraph
        """
        agent_names = project.get_agent_names()
        
        if not agent_names:
            raise ValueError("프로젝트에 Agent가 정의되지 않았습니다.")
        
        # 의존성 기반 실행 순서 결정
        ordered_agents = self.registry.resolve_order(agent_names)
        logger.info(f"Agent 실행 순서: {ordered_agents}")
        
        # StateGraph 생성
        workflow = StateGraph(AgentState)
        
        # 각 Agent를 노드로 추가
        for agent_name in ordered_agents:
            node_func = self._create_node(agent_name, project)
            workflow.add_node(agent_name, node_func)
        
        # 엣지 연결 (순차 실행)
        workflow.set_entry_point(ordered_agents[0])
        
        for i in range(len(ordered_agents) - 1):
            workflow.add_edge(ordered_agents[i], ordered_agents[i + 1])
        
        # 마지막 노드 → END
        workflow.add_edge(ordered_agents[-1], END)
        
        return workflow.compile()
    
    def _create_node(self, agent_name: str, project: Project) -> Callable:
        """Agent 노드 함수 생성"""
        
        def node_func(state: AgentState) -> Dict[str, Any]:
            logger.info(f"🔗 {agent_name.upper()} Agent 실행")
            
            try:
                # Agent 생성
                agent = self.registry.create(agent_name)
                
                # 입력 준비
                request = state.get("request", "")
                context = {
                    "project": project.config.model_dump(),
                    "inputs": project.config.inputs,
                    "previous_results": state.get("results", {}),
                }
                
                # Agent 메서드 호출
                if hasattr(agent, 'plan'):
                    result = agent.plan(request, context)
                elif hasattr(agent, 'execute_plan'):
                    plan = state.get("plan", {})
                    result = agent.execute_plan(plan)
                elif hasattr(agent, 'write'):
                    result = agent.write(request, state.get("results", {}))
                elif hasattr(agent, 'review'):
                    result = agent.review(request, context)
                elif hasattr(agent, 'analyze'):
                    result = agent.analyze(
                        project.config.inputs.get("study_area", ""),
                        context=context
                    )
                elif hasattr(agent, 'simulate'):
                    result = agent.simulate(
                        project.config.name,
                        project.config.inputs.get("study_area", ""),
                        rainfall=project.config.inputs.get("rainfall", {}),
                        context=context
                    )
                elif hasattr(agent, 'visualize'):
                    result = agent.visualize(
                        str(state.get("results", {})),
                        context=context
                    )
                elif hasattr(agent, 'write_paper'):
                    result = agent.write_paper(
                        project.config.inputs.get("topic", request),
                        research_data=state.get("results", {}),
                        context=context
                    )
                else:
                    # 기본 invoke
                    result = agent.invoke(request)
                
                # 결과 저장 (datetime 직렬화 처리)
                if hasattr(result, 'model_dump'):
                    result_dict = result.model_dump(mode='json')
                elif isinstance(result, dict):
                    result_dict = result
                else:
                    result_dict = str(result)
                
                # 현재 결과를 state에 추가
                current_results = state.get("results", {})
                current_results[agent_name] = result_dict
                
                logger.info(f"✅ {agent_name.upper()} Agent 완료")
                
                return {
                    "current_agent": agent_name,
                    "results": current_results,
                    "messages": [AIMessage(content=f"{agent_name} 완료")],
                }
                
            except Exception as e:
                logger.error(f"❌ {agent_name} 오류: {e}")
                return {
                    "current_agent": agent_name,
                    "error": str(e),
                    "messages": [AIMessage(content=f"{agent_name} 오류: {e}")],
                }
        
        return node_func


class ProjectRunner:
    """
    Project Runner
    
    프로젝트를 실행하고 결과를 관리합니다.
    """
    
    def __init__(self):
        self.builder = WorkflowBuilder()
        self.artifact_manager = get_artifact_manager()
        self.trace_store = get_trace_store()
    
    def run(
        self,
        project: Project,
        request: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        프로젝트 실행
        
        Args:
            project: Project 인스턴스
            request: 사용자 요청 (없으면 프로젝트 description 사용)
        
        Returns:
            실행 결과
        """
        # Trace 생성
        trace = create_trace(
            project_id=project.project_id,
            project_name=project.config.name,
            request=request or project.config.description,
            config=project.config.model_dump(),
        )
        
        logger.info(f"🚀 프로젝트 실행 시작: {project.config.name}")
        logger.info(f"📋 Trace ID: {trace.trace_id}")
        
        try:
            # 워크플로우 빌드
            workflow = self.builder.build(project)
            
            # 초기 상태
            initial_state = {
                "request": request or project.config.description or "",
                "project_name": project.config.name,
                "trace_id": trace.trace_id,
                "messages": [HumanMessage(content=request or "")],
                "results": {},
                "inputs": project.config.inputs,
            }
            
            # 워크플로우 실행
            final_state = None
            for event in workflow.stream(initial_state):
                for node_name, node_output in event.items():
                    trace.start_agent(node_name, {"input": initial_state.get("request")})
                    
                    if node_output.get("error"):
                        trace.finish_agent(node_name, error=node_output["error"])
                    else:
                        trace.finish_agent(node_name, output_data=node_output.get("results", {}).get(node_name))
                    
                    final_state = node_output
            
            # 결과 처리
            results = final_state.get("results", {}) if final_state else {}
            
            # Artifact 저장
            artifact_ids = self._save_artifacts(project, results, trace.trace_id)
            
            # Trace 완료
            trace.complete(outputs=results, artifacts=artifact_ids)
            self.trace_store.save(trace)
            
            logger.info(f"✅ 프로젝트 실행 완료: {project.config.name}")
            logger.info(f"📊 Artifact 수: {len(artifact_ids)}")
            
            return {
                "success": True,
                "trace_id": trace.trace_id,
                "project_id": project.project_id,
                "results": results,
                "artifacts": artifact_ids,
                "summary": trace.get_summary(),
            }
            
        except Exception as e:
            import traceback
            trace.fail(str(e), traceback.format_exc())
            self.trace_store.save(trace)
            
            logger.error(f"❌ 프로젝트 실행 실패: {e}")
            
            return {
                "success": False,
                "trace_id": trace.trace_id,
                "project_id": project.project_id,
                "error": str(e),
                "summary": trace.get_summary(),
            }
    
    def _save_artifacts(
        self,
        project: Project,
        results: Dict[str, Any],
        trace_id: str,
    ) -> List[str]:
        """결과물을 Artifact로 저장"""
        artifact_ids = []
        
        for agent_name, result in results.items():
            if not result:
                continue
            
            # JSON으로 저장
            artifact = self.artifact_manager.save(
                content=str(result) if not isinstance(result, str) else result,
                name=f"{agent_name}_result.json",
                project_id=project.project_id,
                trace_id=trace_id,
                created_by=agent_name,
                description=f"{agent_name} Agent 실행 결과",
            )
            artifact_ids.append(artifact.id)
            
            # 특정 필드 별도 저장
            if isinstance(result, dict):
                # 코드
                if result.get("python_code") or result.get("analysis_code"):
                    code = result.get("python_code") or result.get("analysis_code")
                    artifact = self.artifact_manager.save(
                        content=code,
                        name=f"{agent_name}_code.py",
                        project_id=project.project_id,
                        trace_id=trace_id,
                        created_by=agent_name,
                    )
                    artifact_ids.append(artifact.id)
                
                # 보고서/논문
                if result.get("content") or result.get("introduction"):
                    content = self._format_document(result)
                    artifact = self.artifact_manager.save(
                        content=content,
                        name=f"{agent_name}_document.md",
                        project_id=project.project_id,
                        trace_id=trace_id,
                        created_by=agent_name,
                    )
                    artifact_ids.append(artifact.id)
        
        return artifact_ids
    
    def _format_document(self, result: Dict) -> str:
        """결과를 문서 형식으로 포맷"""
        lines = []
        
        if result.get("title"):
            lines.append(f"# {result['title']}\n")
        
        if result.get("abstract_ko"):
            lines.append("## 초록\n")
            lines.append(result["abstract_ko"] + "\n")
        
        for section in ["introduction", "literature_review", "methodology", 
                       "study_area", "results", "discussion", "conclusion"]:
            if result.get(section):
                title = section.replace("_", " ").title()
                lines.append(f"## {title}\n")
                lines.append(result[section] + "\n")
        
        if result.get("content"):
            lines.append(result["content"])
        
        return "\n".join(lines)


# =============================================================================
# 편의 함수
# =============================================================================

def run_project(project_or_path, request: Optional[str] = None) -> Dict[str, Any]:
    """프로젝트 실행 (편의 함수)"""
    if isinstance(project_or_path, (str, Path)):
        from pathlib import Path
        project = Project.from_yaml(project_or_path)
    else:
        project = project_or_path
    
    runner = ProjectRunner()
    return runner.run(project, request)


def run_yaml(yaml_path: str, request: Optional[str] = None) -> Dict[str, Any]:
    """YAML 파일에서 프로젝트 실행"""
    from pathlib import Path
    project = Project.from_yaml(Path(yaml_path))
    runner = ProjectRunner()
    return runner.run(project, request)
