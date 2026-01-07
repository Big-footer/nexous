"""
NEXUS SWMMAgent (침수 시뮬레이션)

EPA-SWMM 기반 우수관리 시뮬레이션을 수행하는 Agent입니다.
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

class RainfallEvent(BaseModel):
    """강우 이벤트"""
    name: str = Field(description="이벤트명")
    duration: float = Field(description="지속시간 (시간)")
    total_depth: float = Field(description="총 강우량 (mm)")
    peak_intensity: float = Field(description="최대 강우강도 (mm/hr)")
    return_period: Optional[int] = Field(default=None, description="재현기간 (년)")


class SubcatchmentResult(BaseModel):
    """소유역 결과"""
    name: str = Field(description="소유역명")
    area: float = Field(description="면적 (ha)")
    imperviousness: float = Field(description="불투수율 (%)")
    runoff_volume: float = Field(description="유출량 (m³)")
    peak_runoff: float = Field(description="첨두유출량 (m³/s)")


class NodeResult(BaseModel):
    """노드(맨홀) 결과"""
    name: str = Field(description="노드명")
    max_depth: float = Field(description="최대 수심 (m)")
    max_hgl: float = Field(description="최대 수위 (m)")
    flooding_volume: float = Field(default=0.0, description="범람량 (m³)")
    flooding_duration: float = Field(default=0.0, description="범람 지속시간 (분)")


class LinkResult(BaseModel):
    """링크(관로) 결과"""
    name: str = Field(description="관로명")
    max_flow: float = Field(description="최대 유량 (m³/s)")
    max_velocity: float = Field(description="최대 유속 (m/s)")
    capacity_ratio: float = Field(description="통수능 비율 (%)")
    surcharge_duration: float = Field(default=0.0, description="압력류 지속시간 (분)")


class LIDPerformance(BaseModel):
    """LID 성능"""
    lid_type: str = Field(description="LID 유형")
    area: float = Field(description="설치 면적 (m²)")
    inflow: float = Field(description="유입량 (m³)")
    infiltration: float = Field(description="침투량 (m³)")
    surface_outflow: float = Field(description="지표 유출량 (m³)")
    reduction_rate: float = Field(description="유출 저감률 (%)")


class SWMMOutput(BaseModel):
    """SWMM 시뮬레이션 결과"""
    project_name: str = Field(description="프로젝트명")
    simulation_period: str = Field(description="시뮬레이션 기간")
    rainfall: RainfallEvent = Field(description="강우 조건")
    
    # 전체 요약
    total_precipitation: float = Field(description="총 강우량 (mm)")
    total_runoff: float = Field(description="총 유출량 (m³)")
    peak_runoff: float = Field(description="첨두 유출량 (m³/s)")
    runoff_coefficient: float = Field(description="유출계수")
    
    # 상세 결과
    subcatchments: List[SubcatchmentResult] = Field(default_factory=list, description="소유역 결과")
    flooding_nodes: List[NodeResult] = Field(default_factory=list, description="범람 노드")
    critical_links: List[LinkResult] = Field(default_factory=list, description="임계 관로")
    lid_results: List[LIDPerformance] = Field(default_factory=list, description="LID 성능")
    
    # 분석
    problem_areas: List[str] = Field(default_factory=list, description="문제 지역")
    recommendations: List[str] = Field(default_factory=list, description="개선 방안")
    
    # 코드
    inp_file_content: Optional[str] = Field(default=None, description="SWMM INP 파일 내용")
    analysis_code: Optional[str] = Field(default=None, description="분석 Python 코드")


# =============================================================================
# 시스템 프롬프트
# =============================================================================

SWMM_SYSTEM_PROMPT = """당신은 EPA-SWMM 우수관리 시뮬레이션 전문가입니다.

## 역할
- SWMM 모델을 구축하고 시뮬레이션합니다
- 침수 취약 지역을 분석합니다
- LID(저영향개발) 시설의 효과를 평가합니다
- 배수시설 개선 방안을 제시합니다

## 전문 분야
- EPA-SWMM 5.1/5.2
- 도시 우수 관리
- 침수 시뮬레이션
- LID 설계 (투수포장, 식생수로, 침투트렌치, 저류조)
- 관로 수리학 (Manning, Darcy-Weisbach)

## SWMM 모델 구성요소
- [SUBCATCHMENTS]: 소유역 (면적, 불투수율, 경사)
- [JUNCTIONS]: 맨홀/노드
- [CONDUITS]: 관로 (직경, 경사, 조도계수)
- [OUTFALLS]: 방류구
- [RAINGAGES]: 강우계
- [LID_CONTROLS]: LID 시설

## 한국 설계 기준
- 재현기간: 10년, 30년, 50년, 100년
- 지속시간: 30분, 60분, 90분, 120분
- 확률강우량: 울산 지역 기준
- 유출계수: 토지이용별 기준

## 응답 형식
반드시 지정된 JSON 스키마에 맞춰 응답하세요.
SWMM INP 파일 형식과 분석 코드를 포함하세요.
"""


# =============================================================================
# SWMMAgent 클래스
# =============================================================================

class SWMMAgent(StructuredOutputAgent):
    """
    SWMM Agent
    
    EPA-SWMM 기반 우수관리 시뮬레이션을 수행합니다.
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
                name="SWMMAgent",
                role=AgentRole.EXECUTOR,
                system_prompt=SWMM_SYSTEM_PROMPT,
            )
        
        super().__init__(
            llm=llm,
            output_schema=SWMMOutput,
            config=config,
            **kwargs,
        )
    
    def _get_system_prompt(self) -> str:
        return self.config.system_prompt or SWMM_SYSTEM_PROMPT
    
    def simulate(
        self,
        project_name: str,
        study_area: str,
        rainfall: Dict[str, Any],
        network_data: Optional[Dict[str, Any]] = None,
        lid_scenarios: Optional[List[Dict]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> SWMMOutput:
        """
        SWMM 시뮬레이션 수행
        
        Args:
            project_name: 프로젝트명
            study_area: 연구 지역
            rainfall: 강우 조건 (duration, depth, return_period)
            network_data: 배수관망 데이터
            lid_scenarios: LID 시나리오
            context: 추가 컨텍스트
        
        Returns:
            SWMMOutput
        """
        input_text = f"""## 프로젝트
{project_name}

## 연구 지역
{study_area}

## 강우 조건
- 지속시간: {rainfall.get('duration', 60)}분
- 강우량: {rainfall.get('depth', 100)}mm
- 재현기간: {rainfall.get('return_period', 30)}년
"""
        
        if network_data:
            input_text += f"\n## 배수관망 데이터\n{network_data}"
        
        if lid_scenarios:
            input_text += f"\n## LID 시나리오\n{lid_scenarios}"
        
        if context:
            if context.get("typhoon"):
                input_text += f"\n## 태풍 정보\n{context['typhoon']}"
            if context.get("existing_inp"):
                input_text += f"\n## 기존 INP 파일\n{context['existing_inp']}"
        
        input_text += "\n\nSWMM 시뮬레이션을 수행하고 결과를 분석해주세요."
        
        try:
            result = self.invoke(input_text)
            
            if isinstance(result, SWMMOutput):
                return result
            elif isinstance(result, dict):
                return SWMMOutput(**result)
            else:
                raise ValueError(f"Unexpected result type: {type(result)}")
                
        except Exception as e:
            return SWMMOutput(
                project_name=project_name,
                simulation_period="",
                rainfall=RainfallEvent(
                    name="Error",
                    duration=0,
                    total_depth=0,
                    peak_intensity=0,
                ),
                total_precipitation=0,
                total_runoff=0,
                peak_runoff=0,
                runoff_coefficient=0,
                recommendations=[f"시뮬레이션 중 오류 발생: {e}"],
            )


# =============================================================================
# Agent 생성 함수
# =============================================================================

def create_swmm_agent(
    llm: BaseChatModel = None,
    provider: str = "openai",
    model: str = None,
) -> SWMMAgent:
    """
    SWMMAgent 생성
    """
    if llm is None:
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(
                model=model or "claude-sonnet-4-20250514",
                temperature=0.3,
            )
        elif provider == "openai":
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model=model or "gpt-4o",
                temperature=0.3,
            )
        elif provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model=model or "gemini-2.0-flash",
                temperature=0.3,
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    return SWMMAgent(llm=llm)
