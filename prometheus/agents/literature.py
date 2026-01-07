"""
NEXUS LiteratureAgent (문헌 조사)

학술 논문 검색 및 문헌 조사를 수행하는 Agent입니다.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import tool

from prometheus.agents.langchain_base import (
    BaseLangChainAgent,
    StructuredOutputAgent,
    AgentConfig,
    AgentRole,
)


# =============================================================================
# 출력 스키마
# =============================================================================

class PaperInfo(BaseModel):
    """논문 정보"""
    title: str = Field(description="논문 제목")
    authors: List[str] = Field(default_factory=list, description="저자 목록")
    year: Optional[int] = Field(default=None, description="출판 연도")
    abstract: Optional[str] = Field(default=None, description="초록")
    keywords: List[str] = Field(default_factory=list, description="키워드")
    relevance: str = Field(default="", description="연구와의 관련성")


class LiteratureReviewOutput(BaseModel):
    """문헌 조사 결과"""
    topic: str = Field(description="조사 주제")
    search_keywords: List[str] = Field(description="검색 키워드")
    papers: List[PaperInfo] = Field(default_factory=list, description="관련 논문 목록")
    summary: str = Field(description="문헌 조사 요약")
    research_gaps: List[str] = Field(default_factory=list, description="연구 공백/기회")
    recommended_citations: List[str] = Field(default_factory=list, description="추천 인용")


# =============================================================================
# 시스템 프롬프트
# =============================================================================

LITERATURE_SYSTEM_PROMPT = """당신은 학술 문헌 조사 전문가입니다.

## 역할
- 연구 주제에 대한 관련 문헌을 조사합니다
- 핵심 논문과 연구 동향을 파악합니다
- 연구 공백(research gap)을 식별합니다
- 인용할 만한 문헌을 추천합니다

## 전문 분야
- 도시 침수 및 홍수 관리
- 저영향개발(LID) 기술
- 우수관리 시스템 (SWMM)
- 기후변화와 도시 방재
- 수문학 및 수리학

## 작업 방식
1. 연구 주제 분석
2. 검색 키워드 도출
3. 관련 문헌 탐색
4. 핵심 내용 요약
5. 연구 공백 식별
6. 인용 추천

## 응답 형식
반드시 지정된 JSON 스키마에 맞춰 응답하세요.
"""


# =============================================================================
# LiteratureAgent 클래스
# =============================================================================

class LiteratureAgent(StructuredOutputAgent):
    """
    Literature Agent
    
    학술 문헌 조사 및 논문 검색을 수행합니다.
    """
    
    role = AgentRole.META  # 커스텀 역할로 확장 가능
    
    def __init__(
        self,
        llm: BaseChatModel,
        config: Optional[AgentConfig] = None,
        **kwargs,
    ):
        if config is None:
            config = AgentConfig(
                name="LiteratureAgent",
                role=AgentRole.META,
                system_prompt=LITERATURE_SYSTEM_PROMPT,
            )
        
        super().__init__(
            llm=llm,
            output_schema=LiteratureReviewOutput,
            config=config,
            **kwargs,
        )
    
    def _get_system_prompt(self) -> str:
        return self.config.system_prompt or LITERATURE_SYSTEM_PROMPT
    
    def review(
        self,
        topic: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> LiteratureReviewOutput:
        """
        문헌 조사 수행
        
        Args:
            topic: 연구 주제
            context: 추가 컨텍스트 (연구 범위, 키워드 등)
        
        Returns:
            LiteratureReviewOutput
        """
        input_text = f"연구 주제: {topic}"
        
        if context:
            if context.get("keywords"):
                input_text += f"\n\n검색 키워드 힌트: {context['keywords']}"
            if context.get("scope"):
                input_text += f"\n\n연구 범위: {context['scope']}"
            if context.get("existing_papers"):
                input_text += f"\n\n이미 확보한 논문: {context['existing_papers']}"
        
        try:
            result = self.invoke(input_text)
            
            if isinstance(result, LiteratureReviewOutput):
                return result
            elif isinstance(result, dict):
                return LiteratureReviewOutput(**result)
            else:
                raise ValueError(f"Unexpected result type: {type(result)}")
                
        except Exception as e:
            # 폴백 결과
            return LiteratureReviewOutput(
                topic=topic,
                search_keywords=[topic],
                papers=[],
                summary=f"문헌 조사 중 오류 발생: {e}",
                research_gaps=[],
                recommended_citations=[],
            )


# =============================================================================
# Agent 생성 함수
# =============================================================================

def create_literature_agent(
    llm: BaseChatModel = None,
    provider: str = "anthropic",
    model: str = None,
) -> LiteratureAgent:
    """
    LiteratureAgent 생성
    
    Args:
        llm: LangChain LLM (선택)
        provider: LLM 프로바이더
        model: 모델명
    
    Returns:
        LiteratureAgent
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
    
    return LiteratureAgent(llm=llm)
