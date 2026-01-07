"""
NEXUS GISAgent (지리 정보 분석)

GIS 데이터 분석 및 공간 분석을 수행하는 Agent입니다.
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

class SpatialFeature(BaseModel):
    """공간 피처 정보"""
    name: str = Field(description="피처 이름")
    feature_type: str = Field(description="피처 유형 (point, line, polygon)")
    area: Optional[float] = Field(default=None, description="면적 (m²)")
    length: Optional[float] = Field(default=None, description="길이 (m)")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="속성")


class DEMAnalysis(BaseModel):
    """DEM 분석 결과"""
    min_elevation: float = Field(description="최저 고도 (m)")
    max_elevation: float = Field(description="최고 고도 (m)")
    mean_elevation: float = Field(description="평균 고도 (m)")
    slope_mean: Optional[float] = Field(default=None, description="평균 경사도 (%)")
    flow_direction: Optional[str] = Field(default=None, description="주요 유수 방향")


class FloodRiskZone(BaseModel):
    """침수 위험 구역"""
    zone_id: str = Field(description="구역 ID")
    risk_level: str = Field(description="위험 등급 (high, medium, low)")
    area: float = Field(description="면적 (m²)")
    max_depth: Optional[float] = Field(default=None, description="예상 최대 침수심 (m)")
    affected_buildings: int = Field(default=0, description="영향 받는 건물 수")


class GISAnalysisOutput(BaseModel):
    """GIS 분석 결과"""
    study_area: str = Field(description="연구 지역")
    coordinate_system: str = Field(default="EPSG:5186", description="좌표계")
    total_area: float = Field(description="총 면적 (km²)")
    dem_analysis: Optional[DEMAnalysis] = Field(default=None, description="DEM 분석")
    flood_risk_zones: List[FloodRiskZone] = Field(default_factory=list, description="침수 위험 구역")
    drainage_network: Dict[str, Any] = Field(default_factory=dict, description="배수 네트워크 분석")
    land_use: Dict[str, float] = Field(default_factory=dict, description="토지 이용 현황")
    recommendations: List[str] = Field(default_factory=list, description="권장사항")
    analysis_code: Optional[str] = Field(default=None, description="분석 Python 코드")


# =============================================================================
# 시스템 프롬프트
# =============================================================================

GIS_SYSTEM_PROMPT = """당신은 GIS 및 공간 분석 전문가입니다.

## 역할
- 지리 공간 데이터를 분석합니다
- DEM(수치표고모델) 분석을 수행합니다
- 침수 위험 지역을 식별합니다
- 배수 네트워크를 분석합니다
- Python 코드(geopandas, rasterio)를 생성합니다

## 전문 분야
- GIS 데이터 처리 (Shapefile, GeoJSON, GeoTIFF)
- DEM/DTM 분석
- 수계 분석 (유역, 유로)
- 침수 시뮬레이션 전처리
- 토지 이용 분석

## 사용 도구
- geopandas: 벡터 데이터 처리
- rasterio: 래스터 데이터 처리
- shapely: 기하 연산
- pyproj: 좌표 변환
- matplotlib: 시각화

## 한국 좌표계
- EPSG:5186 (Korea 2000 / Central Belt)
- EPSG:5179 (Korea 2000 / Unified CS)
- EPSG:4326 (WGS84)

## 응답 형식
반드시 지정된 JSON 스키마에 맞춰 응답하세요.
분석에 필요한 Python 코드도 포함하세요.
"""


# =============================================================================
# GISAgent 클래스
# =============================================================================

class GISAgent(StructuredOutputAgent):
    """
    GIS Agent
    
    지리 정보 시스템 분석을 수행합니다.
    """
    
    role = AgentRole.EXECUTOR
    
    def __init__(
        self,
        llm: BaseChatModel,
        config: Optional[AgentConfig] = None,
        **kwargs,
    ):
        if config is None:
            config = AgentConfig(
                name="GISAgent",
                role=AgentRole.EXECUTOR,
                system_prompt=GIS_SYSTEM_PROMPT,
            )
        
        super().__init__(
            llm=llm,
            output_schema=GISAnalysisOutput,
            config=config,
            **kwargs,
        )
    
    def _get_system_prompt(self) -> str:
        return self.config.system_prompt or GIS_SYSTEM_PROMPT
    
    def analyze(
        self,
        study_area: str,
        data_files: Optional[List[str]] = None,
        analysis_type: str = "flood_risk",
        context: Optional[Dict[str, Any]] = None,
    ) -> GISAnalysisOutput:
        """
        GIS 분석 수행
        
        Args:
            study_area: 연구 지역명
            data_files: 입력 데이터 파일 경로
            analysis_type: 분석 유형 (flood_risk, dem, drainage, land_use)
            context: 추가 컨텍스트
        
        Returns:
            GISAnalysisOutput
        """
        input_text = f"""## 연구 지역
{study_area}

## 분석 유형
{analysis_type}
"""
        
        if data_files:
            input_text += f"\n## 입력 데이터\n"
            for f in data_files:
                input_text += f"- {f}\n"
        
        if context:
            if context.get("dem_path"):
                input_text += f"\n## DEM 데이터\n{context['dem_path']}"
            if context.get("boundary"):
                input_text += f"\n## 경계 데이터\n{context['boundary']}"
            if context.get("drainage"):
                input_text += f"\n## 배수관망 데이터\n{context['drainage']}"
        
        input_text += "\n\n분석을 수행하고 Python 코드를 포함해주세요."
        
        try:
            result = self.invoke(input_text)
            
            if isinstance(result, GISAnalysisOutput):
                return result
            elif isinstance(result, dict):
                return GISAnalysisOutput(**result)
            else:
                raise ValueError(f"Unexpected result type: {type(result)}")
                
        except Exception as e:
            return GISAnalysisOutput(
                study_area=study_area,
                coordinate_system="EPSG:5186",
                total_area=0.0,
                recommendations=[f"분석 중 오류 발생: {e}"],
            )


# =============================================================================
# Agent 생성 함수
# =============================================================================

def create_gis_agent(
    llm: BaseChatModel = None,
    provider: str = "openai",
    model: str = None,
) -> GISAgent:
    """
    GISAgent 생성
    
    Args:
        llm: LangChain LLM (선택)
        provider: LLM 프로바이더
        model: 모델명
    
    Returns:
        GISAgent
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
    
    return GISAgent(llm=llm)
