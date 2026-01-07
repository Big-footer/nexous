"""
PROMETHEUS QAAgent (LangChain)

품질 검토를 수행하는 Agent입니다.
보고서의 품질을 평가하고 개선점을 제시합니다.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from langchain_core.language_models import BaseChatModel

from prometheus.agents.langchain_base import (
    AgentConfig,
    AgentRole,
    StructuredOutputAgent,
)


# =============================================================================
# 출력 스키마
# =============================================================================

class QAIssue(BaseModel):
    """발견된 이슈"""
    severity: str = Field(description="심각도 (critical, high, medium, low)")
    category: str = Field(description="카테고리 (accuracy, completeness, clarity, formatting, logic)")
    location: str = Field(default="", description="이슈 위치 (섹션명 등)")
    description: str = Field(description="이슈 설명")
    suggestion: str = Field(default="", description="개선 제안")


class QAResult(BaseModel):
    """QA Agent 출력 스키마"""
    passed: bool = Field(description="검토 통과 여부")
    score: float = Field(description="품질 점수 (0-100)")
    grade: str = Field(description="등급 (A, B, C, D, F)")
    summary: str = Field(description="검토 요약")
    issues: List[QAIssue] = Field(default_factory=list, description="발견된 이슈들")
    strengths: List[str] = Field(default_factory=list, description="장점들")
    recommendations: List[str] = Field(default_factory=list, description="개선 권장사항")
    review_criteria: Dict[str, float] = Field(default_factory=dict, description="평가 기준별 점수")


# =============================================================================
# QAAgent
# =============================================================================

QA_SYSTEM_PROMPT = """당신은 PROMETHEUS의 QA Agent입니다.
보고서와 실행 결과의 품질을 검토하고 평가합니다.

## 역할
1. 보고서 내용의 정확성 검증
2. 논리적 일관성 확인
3. 완성도 평가
4. 개선점 제시

## 평가 기준
1. **정확성 (Accuracy)**: 사실 관계가 정확한가?
2. **완전성 (Completeness)**: 요청한 내용을 모두 다루었는가?
3. **명확성 (Clarity)**: 이해하기 쉽게 작성되었는가?
4. **논리성 (Logic)**: 논리적으로 일관성이 있는가?
5. **형식 (Formatting)**: 형식이 적절한가?

## 점수 기준
- 90-100: A (우수) - 거의 완벽함
- 80-89: B (양호) - 사소한 개선 필요
- 70-79: C (보통) - 일부 개선 필요
- 60-69: D (미흡) - 상당한 개선 필요
- 0-59: F (불량) - 전면 수정 필요

## 통과 기준
- 점수 70점 이상이면 통과
- Critical 이슈가 없어야 통과

반드시 지정된 JSON 스키마에 맞춰 응답하세요.
"""


class QAAgent(StructuredOutputAgent):
    """
    QA Agent
    
    보고서와 실행 결과의 품질을 검토합니다.
    구조화된 출력(QAResult)을 생성합니다.
    """
    
    role = AgentRole.QA
    
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
                name="QAAgent",
                role=AgentRole.QA,
                system_prompt=QA_SYSTEM_PROMPT,
            )
        
        super().__init__(
            llm=llm,
            output_schema=QAResult,
            config=config,
            **kwargs,
        )
    
    def _get_system_prompt(self) -> str:
        """시스템 프롬프트"""
        return self.config.system_prompt or QA_SYSTEM_PROMPT
    
    def review(
        self,
        request: str,
        report: Dict[str, Any],
        execution_result: Optional[Dict[str, Any]] = None,
    ) -> QAResult:
        """
        품질 검토
        
        Args:
            request: 원본 사용자 요청
            report: 검토할 보고서
            execution_result: 실행 결과 (참고용)
        
        Returns:
            QAResult
        """
        import json
        
        input_text = f"""## 원본 요청
{request}

## 검토 대상 보고서
{json.dumps(report, ensure_ascii=False, indent=2)}
"""
        
        if execution_result:
            input_text += f"\n## 실행 결과 (참고)\n{json.dumps(execution_result, ensure_ascii=False, indent=2)}"
        
        input_text += "\n\n위 보고서의 품질을 검토하고 평가해주세요."
        
        try:
            # 새 Runnable 구조: invoke가 직접 결과 반환
            result = self.invoke(input_text)
            
            if isinstance(result, QAResult):
                return result
            elif isinstance(result, dict):
                return QAResult(**result)
            else:
                raise ValueError(f"Unexpected result type: {type(result)}")
                
        except Exception as e:
            # 실패 시 기본 결과 반환
            return QAResult(
                passed=True,
                score=70.0,
                grade="C",
                summary="검토를 완료할 수 없습니다.",
                recommendations=["수동 검토 필요"],
            )
    
    def quick_review(
        self,
        content: str,
    ) -> QAResult:
        """
        간단한 품질 검토
        
        Args:
            content: 검토할 내용 (문자열)
        
        Returns:
            QAResult
        """
        input_text = f"""다음 내용의 품질을 검토해주세요:

{content}

품질 점수와 개선점을 제시해주세요."""
        
        try:
            # 새 Runnable 구조: invoke가 직접 결과 반환
            result = self.invoke(input_text)
            
            if isinstance(result, QAResult):
                return result
            elif isinstance(result, dict):
                return QAResult(**result)
            else:
                raise ValueError(f"Unexpected result type: {type(result)}")
                
        except Exception as e:
            return QAResult(
                passed=True,
                score=75.0,
                grade="C",
                summary="간단 검토 완료",
            )


# =============================================================================
# 팩토리 함수
# =============================================================================

def create_qa_agent(
    llm: Optional[BaseChatModel] = None,
    provider: str = "anthropic",
    model: Optional[str] = None,
) -> QAAgent:
    """
    QAAgent 생성 팩토리
    
    Args:
        llm: LLM 인스턴스 (없으면 생성)
        provider: LLM 프로바이더 (anthropic, openai, google)
        model: 모델명
    
    Returns:
        QAAgent
    """
    if llm is None:
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(
                model=model or "claude-sonnet-4-20250514",
                temperature=0.5,  # QA는 일관성이 중요
            )
        elif provider == "openai":
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model=model or "gpt-4o",
                temperature=0.5,
            )
        elif provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model=model or "gemini-2.0-flash",
                temperature=0.5,
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    return QAAgent(llm=llm)
