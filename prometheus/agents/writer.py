"""
PROMETHEUS WriterAgent (LangChain)

보고서/문서를 작성하는 Agent입니다.
실행 결과를 바탕으로 Markdown 형식의 보고서를 생성합니다.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from prometheus.agents.langchain_base import (
    BaseLangChainAgent,
    AgentConfig,
    AgentRole,
    StructuredOutputAgent,
)


# =============================================================================
# 출력 스키마
# =============================================================================

class Citation(BaseModel):
    """인용/근거"""
    source: str = Field(description="출처 (URL, 문서명 등)")
    content: str = Field(description="인용 내용")
    relevance: str = Field(default="", description="관련성 설명")


class ReportOutput(BaseModel):
    """Writer Agent 출력 스키마"""
    title: str = Field(description="보고서 제목")
    summary: str = Field(description="요약 (2-3문장)")
    content: str = Field(description="본문 (Markdown 형식)")
    conclusions: List[str] = Field(default_factory=list, description="주요 결론들")
    recommendations: List[str] = Field(default_factory=list, description="권장 사항")
    citations: List[Citation] = Field(default_factory=list, description="인용/참고 자료")
    word_count: int = Field(default=0, description="단어 수")
    language: str = Field(default="ko", description="언어 코드")


# =============================================================================
# WriterAgent
# =============================================================================

WRITER_SYSTEM_PROMPT = """당신은 PROMETHEUS의 Writer Agent입니다.
실행 결과를 바탕으로 전문적이고 명확한 보고서를 작성합니다.

## 역할
1. 실행 결과 분석 및 정리
2. 명확하고 읽기 쉬운 보고서 작성
3. 핵심 내용 요약 및 결론 도출
4. 적절한 인용 및 근거 제시

## 보고서 작성 원칙
1. 명확하고 간결한 문장 사용
2. 논리적인 구조와 흐름 유지
3. 기술적 내용도 이해하기 쉽게 설명
4. 근거에 기반한 결론 제시

## 보고서 구조
1. 제목: 핵심 내용을 반영하는 명확한 제목
2. 요약: 전체 내용을 2-3문장으로 요약
3. 본문: 상세한 분석 및 설명 (Markdown 형식)
4. 결론: 핵심 결론 목록
5. 권장사항: 후속 조치 제안 (해당 시)

반드시 지정된 JSON 스키마에 맞춰 응답하세요.
"""


class WriterAgent(StructuredOutputAgent):
    """
    Writer Agent
    
    실행 결과를 바탕으로 보고서를 작성합니다.
    구조화된 출력(ReportOutput)을 생성합니다.
    """
    
    role = AgentRole.WRITER
    
    def __init__(
        self,
        llm: BaseChatModel,
        config: Optional[AgentConfig] = None,
        **kwargs,
    ):
        """
        초기화
        
        Args:
            llm: LangChain LLM (Gemini 추천)
            config: Agent 설정
        """
        if config is None:
            config = AgentConfig(
                name="WriterAgent",
                role=AgentRole.WRITER,
                system_prompt=WRITER_SYSTEM_PROMPT,
            )
        
        super().__init__(
            llm=llm,
            output_schema=ReportOutput,
            config=config,
            **kwargs,
        )
    
    def _get_system_prompt(self) -> str:
        """시스템 프롬프트"""
        return self.config.system_prompt or WRITER_SYSTEM_PROMPT
    
    def write_report(
        self,
        request: str,
        plan: Dict[str, Any],
        execution_result: Dict[str, Any],
        additional_context: Optional[str] = None,
    ) -> ReportOutput:
        """
        보고서 작성
        
        Args:
            request: 원본 사용자 요청
            plan: 실행 계획
            execution_result: 실행 결과
            additional_context: 추가 컨텍스트
        
        Returns:
            ReportOutput
        """
        import json
        
        input_text = f"""## 원본 요청
{request}

## 실행 계획
{json.dumps(plan, ensure_ascii=False, indent=2)}

## 실행 결과
{json.dumps(execution_result, ensure_ascii=False, indent=2)}
"""
        
        if additional_context:
            input_text += f"\n## 추가 컨텍스트\n{additional_context}"
        
        input_text += "\n\n위 정보를 바탕으로 전문적인 보고서를 작성해주세요."
        
        try:
            # 새 Runnable 구조: invoke가 직접 결과 반환
            result = self.invoke(input_text)
            
            if isinstance(result, ReportOutput):
                return result
            elif isinstance(result, dict):
                return ReportOutput(**result)
            else:
                raise ValueError(f"Unexpected result type: {type(result)}")
                
        except Exception as e:
            # 실패 시 기본 보고서 반환
            return ReportOutput(
                title="실행 결과 보고서",
                summary=plan.get("task_summary", "작업 완료"),
                content=f"# 실행 결과\n\n{str(execution_result)}",
                conclusions=["작업이 완료되었습니다."],
                word_count=100,
            )
    
    def write_markdown(
        self,
        request: str,
        plan: Dict[str, Any],
        execution_result: Dict[str, Any],
    ) -> str:
        """
        Markdown 형식 보고서 생성
        
        Args:
            request: 원본 요청
            plan: 실행 계획
            execution_result: 실행 결과
        
        Returns:
            Markdown 문자열
        """
        report = self.write_report(request, plan, execution_result)
        
        md = f"# {report.title}\n\n"
        md += f"## 요약\n{report.summary}\n\n"
        md += f"## 상세 내용\n{report.content}\n\n"
        
        if report.conclusions:
            md += "## 결론\n"
            for c in report.conclusions:
                md += f"- {c}\n"
            md += "\n"
        
        if report.recommendations:
            md += "## 권장 사항\n"
            for r in report.recommendations:
                md += f"- {r}\n"
            md += "\n"
        
        if report.citations:
            md += "## 참고 자료\n"
            for c in report.citations:
                md += f"- [{c.source}] {c.content}\n"
            md += "\n"
        
        return md


# =============================================================================
# 팩토리 함수
# =============================================================================

def create_writer_agent(
    llm: Optional[BaseChatModel] = None,
    provider: str = "google",
    model: Optional[str] = None,
) -> WriterAgent:
    """
    WriterAgent 생성 팩토리
    
    Args:
        llm: LLM 인스턴스 (없으면 생성)
        provider: LLM 프로바이더 (google, anthropic, openai)
        model: 모델명
    
    Returns:
        WriterAgent
    """
    if llm is None:
        if provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model=model or "gemini-2.0-flash",
                temperature=0.7,
            )
        elif provider == "anthropic":
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
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    return WriterAgent(llm=llm)
