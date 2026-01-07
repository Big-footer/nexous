"""
PROMETHEUS PlannerAgent (LangChain)

작업 계획을 수립하는 Agent입니다.
구조화된 출력(PlanOutput)을 생성합니다.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from prometheus.agents.langchain_base import (
    BaseLangChainAgent,
    AgentConfig,
    AgentRole,
    StructuredOutputAgent,
)


# =============================================================================
# 출력 스키마
# =============================================================================

class PlanStep(BaseModel):
    """계획 단계"""
    step_id: int = Field(description="단계 번호 (1부터 시작)")
    action: str = Field(description="수행할 작업 설명")
    tool: Optional[str] = Field(default=None, description="사용할 Tool (python_exec, rag_search, web_search, file_write 등)")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Tool에 전달할 입력 데이터")
    expected_output: str = Field(default="", description="예상 출력 설명")
    dependencies: List[int] = Field(default_factory=list, description="이 단계가 의존하는 이전 단계 ID들")


class PlanOutput(BaseModel):
    """Planner Agent 출력 스키마"""
    task_summary: str = Field(description="작업 요약 (한 문장)")
    analysis: str = Field(description="요청 분석 결과")
    steps: List[PlanStep] = Field(description="실행할 단계들의 목록")
    total_steps: int = Field(description="총 단계 수")
    estimated_time: str = Field(default="알 수 없음", description="예상 소요 시간")
    required_tools: List[str] = Field(default_factory=list, description="필요한 Tool 목록")
    fallback_plan: Optional[str] = Field(default=None, description="실패 시 대안 계획")
    notes: Optional[str] = Field(default=None, description="추가 참고사항")


# =============================================================================
# PlannerAgent
# =============================================================================

PLANNER_SYSTEM_PROMPT = """당신은 PROMETHEUS의 Planner Agent입니다.
사용자의 요청을 분석하고 실행 가능한 계획을 수립합니다.

## 역할
1. 요청을 분석하여 핵심 목표 파악
2. 목표 달성을 위한 단계별 계획 수립
3. 각 단계에서 사용할 Tool 지정
4. 단계 간 의존성 정의

## 사용 가능한 Tool
- python_exec: Python 코드 실행 (데이터 분석, 계산, 파일 처리 등)
- rag_search: 문서 검색 (RAG 기반 지식 검색)
- web_search: 웹 검색 (최신 정보 검색)
- file_write: 파일 작성 (결과물 저장)
- file_read: 파일 읽기 (기존 파일 분석)

## 계획 수립 원칙
1. 단계는 순차적으로 실행 가능해야 함
2. 각 단계는 명확한 입력과 출력을 가져야 함
3. 복잡한 작업은 작은 단계로 분해
4. 실패 가능성이 있는 단계에는 대안 제시

## 응답 형식
반드시 지정된 JSON 스키마에 맞춰 응답하세요.
"""


class PlannerAgent(StructuredOutputAgent):
    """
    Planner Agent
    
    사용자 요청을 분석하고 실행 계획을 수립합니다.
    구조화된 출력(PlanOutput)을 생성합니다.
    """
    
    role = AgentRole.PLANNER
    
    def __init__(
        self,
        llm: BaseChatModel,
        config: Optional[AgentConfig] = None,
        **kwargs,
    ):
        """
        초기화
        
        Args:
            llm: LangChain LLM (Claude 추천)
            config: Agent 설정
        """
        if config is None:
            config = AgentConfig(
                name="PlannerAgent",
                role=AgentRole.PLANNER,
                system_prompt=PLANNER_SYSTEM_PROMPT,
            )
        
        super().__init__(
            llm=llm,
            output_schema=PlanOutput,
            config=config,
            **kwargs,
        )
    
    def _get_system_prompt(self) -> str:
        """시스템 프롬프트"""
        return self.config.system_prompt or PLANNER_SYSTEM_PROMPT
    
    def plan(
        self,
        request: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> PlanOutput:
        """
        계획 수립
        
        Args:
            request: 사용자 요청
            context: 추가 컨텍스트 (이전 결과 등)
        
        Returns:
            PlanOutput
        """
        input_text = request
        if context:
            input_text += f"\n\n## 추가 컨텍스트\n{context}"
        
        try:
            # 새 Runnable 구조: invoke가 직접 결과 반환
            result = self.invoke(input_text)
            
            if isinstance(result, PlanOutput):
                return result
            elif isinstance(result, dict):
                return PlanOutput(**result)
            else:
                raise ValueError(f"Unexpected result type: {type(result)}")
                
        except Exception as e:
            # 실패 시 기본 계획 반환
            return PlanOutput(
                task_summary=request[:100],
                analysis="계획 수립 실패",
                steps=[
                    PlanStep(
                        step_id=1,
                        action="요청 직접 처리",
                        expected_output="처리 결과"
                    )
                ],
                total_steps=1,
                notes=f"오류: {str(e)}"
            )


# =============================================================================
# 팩토리 함수
# =============================================================================

def create_planner_agent(
    llm: Optional[BaseChatModel] = None,
    provider: str = "anthropic",
    model: Optional[str] = None,
) -> PlannerAgent:
    """
    PlannerAgent 생성 팩토리
    
    Args:
        llm: LLM 인스턴스 (없으면 생성)
        provider: LLM 프로바이더 (anthropic, openai, google)
        model: 모델명
    
    Returns:
        PlannerAgent
    """
    if llm is None:
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(
                model=model or "claude-sonnet-4-20250514",
                temperature=0.7,
            )
        elif provider == "openai":
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model=model or "gpt-4o",
                temperature=0.7,
            )
        elif provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model=model or "gemini-2.0-flash",
                temperature=0.7,
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    return PlannerAgent(llm=llm)
