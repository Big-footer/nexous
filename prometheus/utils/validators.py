"""
Validators - 검증 유틸리티

이 파일의 책임:
- 프로젝트 설정 검증
- Agent 설정 검증
- Tool 설정 검증
- 입력 데이터 검증
- 검증 오류 보고
"""

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel

from prometheus.config.project_schema import (
    ProjectConfig,
    AgentConfig,
    ToolConfig,
)


class ValidationError(BaseModel):
    """검증 오류"""
    
    field: str
    message: str
    value: Optional[Any] = None
    suggestion: Optional[str] = None


class ValidationResult(BaseModel):
    """검증 결과"""
    
    is_valid: bool
    errors: List[ValidationError] = []
    warnings: List[str] = []


def validate_project_config(
    config: ProjectConfig,
) -> ValidationResult:
    """
    프로젝트 설정 검증
    
    Args:
        config: 검증할 프로젝트 설정
        
    Returns:
        검증 결과
    """
    # TODO: 프로젝트 설정 검증 로직
    pass


def validate_agent_config(
    config: AgentConfig,
    available_tools: Optional[List[str]] = None,
) -> ValidationResult:
    """
    Agent 설정 검증
    
    Args:
        config: 검증할 Agent 설정
        available_tools: 사용 가능한 Tool 목록
        
    Returns:
        검증 결과
    """
    # TODO: Agent 설정 검증 로직
    pass


def validate_tool_config(
    config: ToolConfig,
) -> ValidationResult:
    """
    Tool 설정 검증
    
    Args:
        config: 검증할 Tool 설정
        
    Returns:
        검증 결과
    """
    # TODO: Tool 설정 검증 로직
    pass


def validate_llm_config(
    provider: str,
    model: str,
    api_key: Optional[str] = None,
) -> ValidationResult:
    """
    LLM 설정 검증
    
    Args:
        provider: LLM 프로바이더
        model: 모델 이름
        api_key: API 키
        
    Returns:
        검증 결과
    """
    # TODO: LLM 설정 검증 로직
    pass


def validate_path(
    path: str,
    must_exist: bool = False,
    must_be_file: bool = False,
    must_be_directory: bool = False,
) -> ValidationResult:
    """
    파일 경로 검증
    
    Args:
        path: 검증할 경로
        must_exist: 존재해야 하는지
        must_be_file: 파일이어야 하는지
        must_be_directory: 디렉토리이어야 하는지
        
    Returns:
        검증 결과
    """
    # TODO: 경로 검증 로직
    pass


def validate_yaml_structure(
    yaml_content: str,
    required_fields: Optional[List[str]] = None,
) -> ValidationResult:
    """
    YAML 구조 검증
    
    Args:
        yaml_content: YAML 문자열
        required_fields: 필수 필드 목록
        
    Returns:
        검증 결과
    """
    # TODO: YAML 구조 검증 로직
    pass


def validate_api_key(
    provider: str,
    api_key: str,
) -> Tuple[bool, Optional[str]]:
    """
    API 키 유효성 검증 (형식만)
    
    Args:
        provider: 프로바이더
        api_key: API 키
        
    Returns:
        (유효 여부, 오류 메시지)
    """
    # TODO: API 키 형식 검증 로직
    pass


def validate_message_format(
    messages: List[Dict[str, Any]],
) -> ValidationResult:
    """
    메시지 형식 검증
    
    Args:
        messages: 메시지 목록
        
    Returns:
        검증 결과
    """
    # TODO: 메시지 형식 검증 로직
    pass


class ConfigValidator:
    """
    설정 검증기 클래스
    
    다양한 설정의 종합적인 검증을 수행합니다.
    """
    
    def __init__(self) -> None:
        """ConfigValidator 초기화"""
        self._custom_validators: Dict[str, Any] = {}
    
    def validate(
        self,
        config: Any,
        config_type: str,
    ) -> ValidationResult:
        """
        설정 검증
        
        Args:
            config: 검증할 설정
            config_type: 설정 유형
            
        Returns:
            검증 결과
        """
        # TODO: 범용 검증 로직
        pass
    
    def register_validator(
        self,
        config_type: str,
        validator: Any,
    ) -> None:
        """
        커스텀 검증기 등록
        
        Args:
            config_type: 설정 유형
            validator: 검증기 함수
        """
        # TODO: 검증기 등록 로직
        pass
    
    def validate_all(
        self,
        project_config: ProjectConfig,
    ) -> ValidationResult:
        """
        프로젝트 전체 검증
        
        Args:
            project_config: 프로젝트 설정
            
        Returns:
            종합 검증 결과
        """
        # TODO: 전체 검증 로직
        pass
