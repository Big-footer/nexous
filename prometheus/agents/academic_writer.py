"""
NEXUS AcademicWriterAgent (학술 논문 작성)

학술 논문 및 연구 보고서 작성을 수행하는 Agent입니다.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from langchain_core.language_models import BaseChatModel

from prometheus.agents.langchain_base import (
    StructuredOutputAgent,
    AgentConfig,
    AgentRole,
)


# =============================================================================
# 출력 스키마
# =============================================================================

class Citation(BaseModel):
    """인용 정보"""
    key: str = Field(description="인용 키 (예: Kim2024)")
    authors: str = Field(description="저자")
    year: int = Field(description="연도")
    title: str = Field(description="제목")
    journal: Optional[str] = Field(default=None, description="저널명")
    volume: Optional[str] = Field(default=None, description="권호")
    pages: Optional[str] = Field(default=None, description="페이지")


class Section(BaseModel):
    """논문 섹션"""
    title: str = Field(description="섹션 제목")
    content: str = Field(description="섹션 내용")
    subsections: List["Section"] = Field(default_factory=list, description="하위 섹션")


class AcademicPaperOutput(BaseModel):
    """학술 논문 출력"""
    # 메타 정보
    title: str = Field(description="논문 제목")
    title_en: Optional[str] = Field(default=None, description="영문 제목")
    authors: List[str] = Field(default_factory=list, description="저자 목록")
    affiliations: List[str] = Field(default_factory=list, description="소속")
    keywords: List[str] = Field(default_factory=list, description="키워드")
    keywords_en: List[str] = Field(default_factory=list, description="영문 키워드")
    
    # 초록
    abstract_ko: str = Field(description="국문 초록")
    abstract_en: str = Field(description="영문 초록")
    
    # 본문 섹션
    introduction: str = Field(description="서론")
    literature_review: str = Field(description="문헌 고찰")
    methodology: str = Field(description="연구 방법")
    study_area: str = Field(description="연구 지역")
    results: str = Field(description="결과")
    discussion: str = Field(description="고찰")
    conclusion: str = Field(description="결론")
    
    # 추가 요소
    acknowledgments: Optional[str] = Field(default=None, description="감사의 글")
    references: List[Citation] = Field(default_factory=list, description="참고문헌")
    
    # 부록
    figures: List[str] = Field(default_factory=list, description="그림 목록")
    tables: List[str] = Field(default_factory=list, description="표 목록")
    
    # LaTeX 출력
    latex_content: Optional[str] = Field(default=None, description="LaTeX 소스")


# =============================================================================
# 시스템 프롬프트
# =============================================================================

ACADEMIC_WRITER_SYSTEM_PROMPT = """당신은 학술 논문 작성 전문가입니다.

## 역할
- 학술 논문을 체계적으로 작성합니다
- 연구 결과를 논리적으로 서술합니다
- 적절한 인용과 참고문헌을 관리합니다
- 한글 및 영문 논문을 작성합니다

## 전문 분야
- 도시 침수 및 홍수 관리
- 수문학 및 수리학
- 저영향개발(LID) 기술
- 기후변화 적응
- 도시 계획 및 방재

## 논문 구조
1. **서론**: 연구 배경, 필요성, 목적
2. **문헌 고찰**: 선행 연구 검토
3. **연구 방법**: 연구 지역, 모델, 분석 방법
4. **결과**: 분석 결과 제시
5. **고찰**: 결과 해석, 의의, 한계
6. **결론**: 요약, 정책 제언

## 작성 스타일
- 객관적이고 학술적인 문체
- 논리적 흐름 유지
- 정량적 데이터 제시
- 적절한 인용 (APA, IEEE 등)
- 그림/표 번호 참조

## 한국어 논문 특성
- 초록: 국문 + 영문
- 키워드: 5-7개
- 참고문헌: 국내/국외 구분
- 연구비 지원 명시

## 응답 형식
반드시 지정된 JSON 스키마에 맞춰 응답하세요.
"""


# =============================================================================
# AcademicWriterAgent 클래스
# =============================================================================

class AcademicWriterAgent(StructuredOutputAgent):
    """
    Academic Writer Agent
    
    학술 논문 및 연구 보고서를 작성합니다.
    """
    
    role = AgentRole.WRITER
    
    def __init__(
        self,
        llm: BaseChatModel,
        config: Optional[AgentConfig] = None,
        **kwargs,
    ):
        if config is None:
            config = AgentConfig(
                name="AcademicWriterAgent",
                role=AgentRole.WRITER,
                system_prompt=ACADEMIC_WRITER_SYSTEM_PROMPT,
            )
        
        super().__init__(
            llm=llm,
            output_schema=AcademicPaperOutput,
            config=config,
            **kwargs,
        )
    
    def _get_system_prompt(self) -> str:
        return self.config.system_prompt or ACADEMIC_WRITER_SYSTEM_PROMPT
    
    def write_paper(
        self,
        topic: str,
        research_data: Optional[Dict[str, Any]] = None,
        literature: Optional[List[Dict]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AcademicPaperOutput:
        """
        학술 논문 작성
        
        Args:
            topic: 연구 주제
            research_data: 연구 데이터 (분석 결과, 시뮬레이션 결과 등)
            literature: 문헌 조사 결과
            context: 추가 컨텍스트
        
        Returns:
            AcademicPaperOutput
        """
        input_text = f"""## 연구 주제
{topic}
"""
        
        if research_data:
            input_text += f"\n## 연구 데이터\n"
            if research_data.get("gis_analysis"):
                input_text += f"### GIS 분석\n{research_data['gis_analysis']}\n"
            if research_data.get("swmm_results"):
                input_text += f"### SWMM 시뮬레이션\n{research_data['swmm_results']}\n"
            if research_data.get("statistics"):
                input_text += f"### 통계 분석\n{research_data['statistics']}\n"
        
        if literature:
            input_text += f"\n## 선행 연구\n"
            for lit in literature[:10]:  # 최대 10개
                input_text += f"- {lit.get('title', '')} ({lit.get('year', '')})\n"
        
        if context:
            if context.get("study_area"):
                input_text += f"\n## 연구 지역\n{context['study_area']}"
            if context.get("methodology"):
                input_text += f"\n## 연구 방법\n{context['methodology']}"
            if context.get("target_journal"):
                input_text += f"\n## 목표 학술지\n{context['target_journal']}"
        
        input_text += "\n\n위 내용을 바탕으로 학술 논문을 작성해주세요."
        
        try:
            result = self.invoke(input_text)
            
            if isinstance(result, AcademicPaperOutput):
                return result
            elif isinstance(result, dict):
                return AcademicPaperOutput(**result)
            else:
                raise ValueError(f"Unexpected result type: {type(result)}")
                
        except Exception as e:
            return AcademicPaperOutput(
                title=f"연구 주제: {topic}",
                abstract_ko=f"논문 작성 중 오류 발생: {e}",
                abstract_en="Error occurred during paper generation.",
                introduction="",
                literature_review="",
                methodology="",
                study_area="",
                results="",
                discussion="",
                conclusion="",
            )


# =============================================================================
# Agent 생성 함수
# =============================================================================

def create_academic_writer_agent(
    llm: BaseChatModel = None,
    provider: str = "anthropic",
    model: str = None,
) -> AcademicWriterAgent:
    """
    AcademicWriterAgent 생성
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
    
    return AcademicWriterAgent(llm=llm)
