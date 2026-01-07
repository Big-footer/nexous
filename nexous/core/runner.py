"""
NEXOUS Core - Runner

Runner는 NEXOUS의 심장이다.
- GUI도 아니다
- CLI도 아니다  
- Agent도 아니다

Runner는 오직 아래만 책임진다:
    YAML → 실행 → Trace

Runner는 생각하지 않는다.
Runner는 실행하고 기록만 한다.

LEVEL 1 제약:
- Runner는 LLM을 직접 호출하지 않는다.
- LLM 호출은 Agent(GenericAgent)가 담당한다.
"""

from __future__ import annotations

import os
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import yaml

from .trace_writer import TraceWriter
from .state import RunStatus, AgentStatus
from .base_agent import BaseAgent, DummyAgent
from .preset_loader import PresetLoader, PresetNotFoundError
from .agent_factory import AgentFactory, AgentCreationError
from .exceptions import (
    YAMLParseError,
    SchemaValidationError,
    DependencyCycleError,
    AgentNotFoundError,
    AgentExecutionError,
    RunnerError
)

logger = logging.getLogger(__name__)


class Runner:
    """
    NEXOUS 실행 엔진
    
    LEVEL 1 제약:
    - Runner는 LLM을 직접 호출하지 않는다.
    - Runner는 Agent를 생성하고 execute()를 호출할 뿐이다.
    - LLM 호출 및 Trace 기록은 Agent(GenericAgent)가 담당한다.
    """
    
    def __init__(
        self,
        trace_dir: str = "traces",
        preset_dir: str = None,
        use_llm: bool = False
    ):
        """
        Args:
            trace_dir: Trace 저장 디렉토리
            preset_dir: Preset 디렉토리 (기본: nexous/presets)
            use_llm: 실제 LLM 사용 여부
        """
        self.trace_dir = trace_dir
        self.trace = TraceWriter(base_dir=trace_dir)
        self.use_llm = use_llm or os.getenv("NEXOUS_USE_LLM", "").lower() in ("true", "1", "yes")
        
        # Preset Loader
        self.preset_loader = PresetLoader(preset_dir)
        
        # Agent Factory
        # trace_callback을 전달하여 Agent가 LLM/Tool step을 기록할 수 있게 함
        self.agent_factory = AgentFactory(
            preset_loader=self.preset_loader,
            use_llm=self.use_llm,
            trace_callback=self.trace.log_step,
        )
    
    def run(self, project_yaml_path: str, run_id: str = None) -> str:
        """
        Project 실행
        
        Args:
            project_yaml_path: project.yaml 경로
            run_id: 실행 ID (없으면 자동 생성)
            
        Returns:
            trace.json 경로
        """
        if not run_id:
            run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        project = None
        project_id = "unknown"
        
        try:
            # 1. Project YAML 로드
            project = self._load_project(project_yaml_path)
            project_id = project.get("project_id", Path(project_yaml_path).stem)
            execution_mode = project.get("execution", {}).get("mode", "sequential")
            
            # 2. Preset 로드
            self.preset_loader.load_all()
            logger.info(f"[Runner] Presets loaded: {self.preset_loader.list_presets()}")
            logger.info(f"[Runner] LLM Mode: {self.use_llm}")
            
            # 3. Run 시작
            self.trace.start_run(
                project_id=project_id,
                run_id=run_id,
                execution_mode=execution_mode
            )
            
            # 4. Agent 실행 순서 결정
            agents_config = project.get("agents", [])
            ordered_agents = self._resolve_dependencies(agents_config)
            
            # 5. Agent 인스턴스 생성 (AgentFactory)
            agents = self._create_agents(ordered_agents)
            
            # 6. Agent 실행 루프
            results = {}
            
            for agent in agents:
                result = self._execute_agent(agent, results, project)
                results[agent.agent_id] = result
            
            # 7. Run 완료
            self.trace.end_run("COMPLETED")
            
            trace_path = self.trace.get_trace_path()
            logger.info(f"[Runner] Run completed: {trace_path}")
            return str(trace_path)
            
        except Exception as e:
            logger.error(f"[Runner] Run failed: {e}")
            
            if not self.trace._trace:
                self.trace.start_run(
                    project_id=project_id,
                    run_id=run_id,
                    execution_mode="sequential"
                )
            
            error_type = self._get_error_type(e)
            
            self.trace.log_error(
                agent_id="runner",
                step_id="runner.init",
                error_type=error_type,
                message=str(e),
                recoverable=False
            )
            
            self.trace.end_run("FAILED")
            
            trace_path = self.trace.get_trace_path()
            logger.error(f"[Runner] Trace saved: {trace_path}")
            
            raise
    
    def _get_error_type(self, e: Exception) -> str:
        """예외에 따른 에러 타입 결정"""
        error_map = {
            YAMLParseError: "YAML_PARSE_ERROR",
            SchemaValidationError: "SCHEMA_VALIDATION_ERROR",
            DependencyCycleError: "DEPENDENCY_CYCLE_ERROR",
            PresetNotFoundError: "PRESET_NOT_FOUND_ERROR",
            AgentCreationError: "AGENT_CREATION_ERROR",
            AgentExecutionError: "AGENT_EXECUTION_ERROR",
        }
        
        for error_class, error_type in error_map.items():
            if isinstance(e, error_class):
                return error_type
        
        return "RUNNER_ERROR"
    
    def _load_project(self, yaml_path: str) -> Dict[str, Any]:
        """Project YAML 로드"""
        path = Path(yaml_path)
        
        if not path.exists():
            raise YAMLParseError(f"Project file not found: {yaml_path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                project = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise YAMLParseError(f"YAML parsing failed: {e}")
        
        if not project:
            raise YAMLParseError("Empty project file")
        
        if "agents" not in project:
            raise SchemaValidationError("Missing required field: 'agents'")
        
        if not isinstance(project["agents"], list):
            raise SchemaValidationError("'agents' must be a list")
        
        for i, agent in enumerate(project["agents"]):
            if "id" not in agent:
                raise SchemaValidationError(f"Agent {i}: missing 'id'")
            if "preset" not in agent:
                raise SchemaValidationError(f"Agent {agent.get('id', i)}: missing 'preset'")
        
        return project
    
    def _resolve_dependencies(self, agents_config: List[Dict]) -> List[Dict]:
        """Agent 실행 순서 결정 (위상 정렬)"""
        agent_map = {a["id"]: a for a in agents_config}
        visited = {a["id"]: 0 for a in agents_config}
        result = []
        
        def visit(agent_id: str):
            if visited[agent_id] == 1:
                raise DependencyCycleError(f"Circular dependency detected at: {agent_id}")
            if visited[agent_id] == 2:
                return
            
            visited[agent_id] = 1
            
            agent = agent_map.get(agent_id)
            if not agent:
                raise AgentNotFoundError(f"Agent not found: {agent_id}")
            
            for dep_id in agent.get("dependencies", []):
                if dep_id not in agent_map:
                    raise AgentNotFoundError(f"Dependency not found: {dep_id} (required by {agent_id})")
                visit(dep_id)
            
            visited[agent_id] = 2
            result.append(agent)
        
        for agent_id in agent_map:
            visit(agent_id)
        
        return result
    
    def _create_agents(self, agents_config: List[Dict]) -> List[BaseAgent]:
        """Agent 인스턴스 생성 (AgentFactory 사용)"""
        agents = []
        
        for config in agents_config:
            try:
                agent = self.agent_factory.create(config)
                agents.append(agent)
            except PresetNotFoundError:
                raise
            except AgentCreationError:
                raise
        
        return agents
    
    def _execute_agent(
        self,
        agent: BaseAgent,
        previous_results: Dict[str, Any],
        project: Dict
    ) -> Dict[str, Any]:
        """
        단일 Agent 실행
        
        Runner는 Agent.execute()를 호출할 뿐이다.
        LLM 호출은 Agent 내부에서 이루어진다.
        """
        agent_id = agent.agent_id
        
        # Agent 시작
        self.trace.start_agent(
            agent_id=agent_id,
            preset=agent.preset,
            purpose=agent.purpose
        )
        
        try:
            # INPUT Step
            context = {
                "project": project,
                "previous_results": previous_results,
                "inputs": agent.config.get("inputs", {})
            }
            
            dependencies = agent.config.get("dependencies", [])
            dep_context = [dep for dep in dependencies if dep in previous_results]
            
            self.trace.log_step(
                agent_id=agent_id,
                step_type="INPUT",
                status="OK",
                payload={
                    "context": list(context.get("inputs", {}).keys()) or ["project_context"],
                    "previous_results": dep_context
                }
            )
            
            # Agent 실행 (LLM 호출은 Agent 내부에서)
            result = agent.execute(context)
            
            # OUTPUT Step
            output_keys = list(result.keys()) if isinstance(result, dict) else ["output"]
            artifact_ids = result.get("artifact_ids", []) if isinstance(result, dict) else []
            
            self.trace.log_step(
                agent_id=agent_id,
                step_type="OUTPUT",
                status="OK",
                payload={
                    "output_keys": output_keys,
                    "artifact_ids": artifact_ids
                }
            )
            
            # Agent 완료
            self.trace.end_agent(agent_id, "COMPLETED")
            
            return result
            
        except Exception as e:
            logger.error(f"[Runner] Agent {agent_id} failed: {e}")
            
            self.trace.log_error(
                agent_id=agent_id,
                step_id=f"{agent_id}.execute",
                error_type="AGENT_ERROR",
                message=str(e),
                recoverable=False
            )
            
            self.trace.end_agent(agent_id, "FAILED")
            raise AgentExecutionError(agent_id, str(e), e)


# 편의 함수
def run_project(
    project_yaml_path: str,
    run_id: str = None,
    trace_dir: str = "traces",
    preset_dir: str = None,
    use_llm: bool = False
) -> str:
    """Project 실행 편의 함수"""
    runner = Runner(trace_dir=trace_dir, preset_dir=preset_dir, use_llm=use_llm)
    return runner.run(project_yaml_path, run_id)
