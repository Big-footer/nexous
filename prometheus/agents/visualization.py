"""
NEXUS VisualizationAgent (시각화)

데이터 시각화 및 그래프 생성을 수행하는 Agent입니다.
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

class ChartSpec(BaseModel):
    """차트 명세"""
    chart_type: str = Field(description="차트 유형 (line, bar, scatter, heatmap, map)")
    title: str = Field(description="차트 제목")
    x_label: str = Field(default="", description="X축 라벨")
    y_label: str = Field(default="", description="Y축 라벨")
    data_source: str = Field(description="데이터 소스")
    description: str = Field(default="", description="차트 설명")


class VisualizationOutput(BaseModel):
    """시각화 결과"""
    title: str = Field(description="시각화 제목")
    charts: List[ChartSpec] = Field(default_factory=list, description="생성할 차트 목록")
    
    # 생성 코드
    python_code: str = Field(description="시각화 Python 코드")
    required_libraries: List[str] = Field(default_factory=list, description="필요 라이브러리")
    
    # 출력
    output_files: List[str] = Field(default_factory=list, description="출력 파일명")
    figure_captions: List[str] = Field(default_factory=list, description="그림 캡션")
    
    # 논문용
    academic_style: bool = Field(default=True, description="학술 스타일 여부")
    color_scheme: str = Field(default="scientific", description="색상 스키마")


# =============================================================================
# 시스템 프롬프트
# =============================================================================

VISUALIZATION_SYSTEM_PROMPT = """당신은 데이터 시각화 전문가입니다.

## 역할
- 데이터를 효과적으로 시각화합니다
- 학술 논문에 적합한 그래프를 생성합니다
- 침수 관련 지도와 차트를 만듭니다
- Python 코드를 생성합니다

## 시각화 유형
1. **시계열 그래프**: 강우량, 수위 변화
2. **막대 그래프**: 지역별 비교, 시나리오 비교
3. **히트맵**: 침수 위험도, 공간 분포
4. **지도**: 침수 범위, GIS 데이터
5. **산점도**: 상관관계 분석
6. **박스플롯**: 데이터 분포

## 사용 라이브러리
- matplotlib: 기본 시각화
- seaborn: 통계 시각화
- plotly: 인터랙티브 시각화
- folium: 지도 시각화
- geopandas: GIS 시각화

## 학술 스타일 가이드
- 폰트: Times New Roman 또는 Malgun Gothic
- 크기: Figure 크기 적절히 (single column: 8cm, double: 16cm)
- DPI: 300 이상
- 색상: 컬러블라인드 친화적
- 범례: 명확하게 표시
- 단위: SI 단위 사용

## 응답 형식
반드시 지정된 JSON 스키마에 맞춰 응답하세요.
실행 가능한 Python 코드를 포함하세요.
"""


# =============================================================================
# VisualizationAgent 클래스
# =============================================================================

class VisualizationAgent(StructuredOutputAgent):
    """
    Visualization Agent
    
    데이터 시각화 및 그래프 생성을 수행합니다.
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
                name="VisualizationAgent",
                role=AgentRole.WRITER,
                system_prompt=VISUALIZATION_SYSTEM_PROMPT,
            )
        
        super().__init__(
            llm=llm,
            output_schema=VisualizationOutput,
            config=config,
            **kwargs,
        )
    
    def _get_system_prompt(self) -> str:
        return self.config.system_prompt or VISUALIZATION_SYSTEM_PROMPT
    
    def visualize(
        self,
        data_description: str,
        chart_types: Optional[List[str]] = None,
        academic_style: bool = True,
        context: Optional[Dict[str, Any]] = None,
    ) -> VisualizationOutput:
        """
        시각화 생성
        
        Args:
            data_description: 데이터 설명
            chart_types: 원하는 차트 유형
            academic_style: 학술 스타일 여부
            context: 추가 컨텍스트 (데이터 파일 경로 등)
        
        Returns:
            VisualizationOutput
        """
        input_text = f"""## 데이터 설명
{data_description}

## 스타일
- 학술 스타일: {'예' if academic_style else '아니오'}
"""
        
        if chart_types:
            input_text += f"\n## 원하는 차트 유형\n"
            for ct in chart_types:
                input_text += f"- {ct}\n"
        
        if context:
            if context.get("data_file"):
                input_text += f"\n## 데이터 파일\n{context['data_file']}"
            if context.get("output_dir"):
                input_text += f"\n## 출력 디렉토리\n{context['output_dir']}"
            if context.get("language"):
                input_text += f"\n## 언어\n{context['language']}"
        
        input_text += "\n\n시각화 코드를 생성해주세요."
        
        try:
            result = self.invoke(input_text)
            
            if isinstance(result, VisualizationOutput):
                return result
            elif isinstance(result, dict):
                return VisualizationOutput(**result)
            else:
                raise ValueError(f"Unexpected result type: {type(result)}")
                
        except Exception as e:
            return VisualizationOutput(
                title="시각화 오류",
                charts=[],
                python_code=f"# 오류 발생: {e}",
                required_libraries=["matplotlib"],
            )


# =============================================================================
# Agent 생성 함수
# =============================================================================

def create_visualization_agent(
    llm: BaseChatModel = None,
    provider: str = "google",
    model: str = None,
) -> VisualizationAgent:
    """
    VisualizationAgent 생성
    """
    if llm is None:
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(
                model=model or "claude-sonnet-4-20250514",
                temperature=0.5,
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
    
    return VisualizationAgent(llm=llm)
