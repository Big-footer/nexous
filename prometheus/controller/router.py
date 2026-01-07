"""
Router - 작업 분배/라우팅

이 파일의 책임:
- 요청 분석 및 분류
- 적절한 Agent로 라우팅
- 작업 분해 결정
- 라우팅 전략 관리
"""

from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field
import json

from prometheus.config.project_schema import AgentType
from prometheus.llm.base import BaseLLMClient, Message


class TaskType(str, Enum):
    """작업 유형"""
    
    PLANNING = "planning"
    EXECUTION = "execution"
    WRITING = "writing"
    QA = "qa"
    COMPLEX = "complex"
    SIMPLE = "simple"
    UNKNOWN = "unknown"


class RoutingStrategy(str, Enum):
    """라우팅 전략"""
    
    DIRECT = "direct"           # 단일 Agent로 직접 라우팅
    SEQUENTIAL = "sequential"   # 순차적 Agent 처리
    PARALLEL = "parallel"       # 병렬 Agent 처리
    ADAPTIVE = "adaptive"       # 적응형 라우팅


class RouteDecision(BaseModel):
    """라우팅 결정"""
    
    task_type: TaskType
    target_agent: AgentType
    strategy: RoutingStrategy = RoutingStrategy.DIRECT
    requires_planning: bool = False
    sub_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = 1.0
    reasoning: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RouterConfig(BaseModel):
    """라우터 설정"""
    
    default_strategy: RoutingStrategy = RoutingStrategy.ADAPTIVE
    planning_threshold: int = 100  # 이 길이 이상이면 계획 필요
    use_llm_routing: bool = True
    fallback_agent: AgentType = AgentType.EXECUTOR


class Router:
    """
    작업 라우터
    
    요청을 분석하고 적절한 Agent로 라우팅합니다.
    작업의 복잡도에 따라 분해 여부를 결정합니다.
    """
    
    # 키워드 기반 라우팅 규칙
    KEYWORD_RULES: Dict[str, AgentType] = {
        # Planning 키워드
        "계획": AgentType.PLANNER,
        "plan": AgentType.PLANNER,
        "설계": AgentType.PLANNER,
        "분석": AgentType.PLANNER,
        "전략": AgentType.PLANNER,
        
        # Execution 키워드
        "실행": AgentType.EXECUTOR,
        "execute": AgentType.EXECUTOR,
        "run": AgentType.EXECUTOR,
        "수행": AgentType.EXECUTOR,
        "처리": AgentType.EXECUTOR,
        
        # Writing 키워드
        "작성": AgentType.WRITER,
        "write": AgentType.WRITER,
        "문서": AgentType.WRITER,
        "보고서": AgentType.WRITER,
        "번역": AgentType.WRITER,
        "요약": AgentType.WRITER,
        
        # QA 키워드
        "검토": AgentType.QA,
        "review": AgentType.QA,
        "검증": AgentType.QA,
        "품질": AgentType.QA,
        "평가": AgentType.QA,
    }
    
    ROUTING_PROMPT = """Analyze the following request and determine the best routing.

Request: {request}

Available Agents:
- planner: For planning, analysis, and breaking down complex tasks
- executor: For executing tasks, running code, using tools
- writer: For writing documents, reports, translations, summaries
- qa: For quality review, validation, feedback

Respond with a JSON object:
{{
    "task_type": "planning|execution|writing|qa|complex|simple",
    "target_agent": "planner|executor|writer|qa",
    "requires_planning": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation"
}}

Analyze and respond:"""

    def __init__(
        self,
        config: Optional[RouterConfig] = None,
        llm: Optional[BaseLLMClient] = None,
    ) -> None:
        """
        Router 초기화
        
        Args:
            config: 라우터 설정
            llm: LLM 클라이언트 (LLM 기반 라우팅용)
        """
        self.config = config or RouterConfig()
        self._llm = llm
    
    def bind_llm(
        self,
        llm: BaseLLMClient,
    ) -> "Router":
        """
        LLM 바인딩
        
        Args:
            llm: LLM 클라이언트
            
        Returns:
            self
        """
        self._llm = llm
        return self
    
    async def route(
        self,
        request: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> RouteDecision:
        """
        요청 라우팅
        
        Args:
            request: 사용자 요청
            context: 추가 컨텍스트
            
        Returns:
            라우팅 결정
        """
        # LLM 기반 라우팅
        if self.config.use_llm_routing and self._llm:
            return await self._route_with_llm(request, context)
        
        # 규칙 기반 라우팅
        return self._route_with_rules(request, context)
    
    def route_sync(
        self,
        request: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> RouteDecision:
        """
        동기 라우팅 (규칙 기반만 사용)
        
        Args:
            request: 사용자 요청
            context: 추가 컨텍스트
            
        Returns:
            라우팅 결정
        """
        return self._route_with_rules(request, context)
    
    async def _route_with_llm(
        self,
        request: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> RouteDecision:
        """
        LLM 기반 라우팅
        
        Args:
            request: 사용자 요청
            context: 추가 컨텍스트
            
        Returns:
            라우팅 결정
        """
        prompt = self.ROUTING_PROMPT.format(request=request)
        
        messages = [
            Message.system("You are a routing expert. Analyze requests and determine the best agent to handle them."),
            Message.user(prompt),
        ]
        
        try:
            response = await self._llm.generate(messages, temperature=0.2)
            return self._parse_routing_response(response.content, request)
        except Exception:
            # LLM 실패 시 규칙 기반으로 폴백
            return self._route_with_rules(request, context)
    
    def _route_with_rules(
        self,
        request: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> RouteDecision:
        """
        규칙 기반 라우팅
        
        Args:
            request: 사용자 요청
            context: 추가 컨텍스트
            
        Returns:
            라우팅 결정
        """
        request_lower = request.lower()
        
        # 키워드 매칭
        matched_agent = None
        for keyword, agent_type in self.KEYWORD_RULES.items():
            if keyword in request_lower:
                matched_agent = agent_type
                break
        
        # 매칭 실패 시 기본 Agent
        if matched_agent is None:
            matched_agent = self.config.fallback_agent
        
        # 복잡도 판단
        requires_planning = len(request) > self.config.planning_threshold
        
        # 작업 유형 결정
        task_type = self._determine_task_type(matched_agent, request)
        
        # 전략 결정
        strategy = self._determine_strategy(task_type, requires_planning)
        
        return RouteDecision(
            task_type=task_type,
            target_agent=matched_agent,
            strategy=strategy,
            requires_planning=requires_planning,
            confidence=0.7,  # 규칙 기반은 낮은 신뢰도
            reasoning=f"Matched by keyword rules to {matched_agent.value}",
        )
    
    def _parse_routing_response(
        self,
        response: str,
        original_request: str,
    ) -> RouteDecision:
        """
        LLM 응답 파싱
        
        Args:
            response: LLM 응답
            original_request: 원래 요청
            
        Returns:
            라우팅 결정
        """
        try:
            # JSON 추출
            json_str = self._extract_json(response)
            data = json.loads(json_str)
            
            return RouteDecision(
                task_type=TaskType(data.get("task_type", "unknown")),
                target_agent=AgentType(data.get("target_agent", "executor")),
                requires_planning=data.get("requires_planning", False),
                confidence=data.get("confidence", 0.8),
                reasoning=data.get("reasoning", ""),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            # 파싱 실패 시 규칙 기반으로 폴백
            return self._route_with_rules(original_request, None)
    
    def _extract_json(self, text: str) -> str:
        """텍스트에서 JSON 추출"""
        import re
        
        # ```json ... ``` 패턴
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            return json_match.group(1).strip()
        
        # { ... } 패턴
        brace_match = re.search(r'(\{[\s\S]*\})', text)
        if brace_match:
            return brace_match.group(1)
        
        return text
    
    def _determine_task_type(
        self,
        agent_type: AgentType,
        request: str,
    ) -> TaskType:
        """
        작업 유형 결정
        
        Args:
            agent_type: Agent 타입
            request: 요청
            
        Returns:
            작업 유형
        """
        type_map = {
            AgentType.PLANNER: TaskType.PLANNING,
            AgentType.EXECUTOR: TaskType.EXECUTION,
            AgentType.WRITER: TaskType.WRITING,
            AgentType.QA: TaskType.QA,
        }
        return type_map.get(agent_type, TaskType.UNKNOWN)
    
    def _determine_strategy(
        self,
        task_type: TaskType,
        requires_planning: bool,
    ) -> RoutingStrategy:
        """
        라우팅 전략 결정
        
        Args:
            task_type: 작업 유형
            requires_planning: 계획 필요 여부
            
        Returns:
            라우팅 전략
        """
        if requires_planning:
            return RoutingStrategy.SEQUENTIAL
        
        if task_type == TaskType.COMPLEX:
            return RoutingStrategy.ADAPTIVE
        
        return RoutingStrategy.DIRECT
    
    async def decompose_task(
        self,
        request: str,
        max_subtasks: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        작업 분해
        
        Args:
            request: 요청
            max_subtasks: 최대 하위 작업 수
            
        Returns:
            하위 작업 목록
        """
        if not self._llm:
            return [{"task": request, "agent": self.config.fallback_agent.value}]
        
        prompt = f"""Break down this task into smaller subtasks (max {max_subtasks}):

Task: {request}

Respond with a JSON array:
[
    {{"task": "subtask description", "agent": "planner|executor|writer|qa"}}
]"""
        
        messages = [
            Message.system("You are a task decomposition expert."),
            Message.user(prompt),
        ]
        
        try:
            response = await self._llm.generate(messages, temperature=0.3)
            json_str = self._extract_json(response.content)
            return json.loads(json_str)
        except Exception:
            return [{"task": request, "agent": self.config.fallback_agent.value}]
    
    def add_routing_rule(
        self,
        keyword: str,
        agent_type: AgentType,
    ) -> None:
        """
        라우팅 규칙 추가
        
        Args:
            keyword: 키워드
            agent_type: Agent 타입
        """
        self.KEYWORD_RULES[keyword.lower()] = agent_type
    
    def remove_routing_rule(
        self,
        keyword: str,
    ) -> bool:
        """
        라우팅 규칙 제거
        
        Args:
            keyword: 키워드
            
        Returns:
            제거 성공 여부
        """
        if keyword.lower() in self.KEYWORD_RULES:
            del self.KEYWORD_RULES[keyword.lower()]
            return True
        return False
