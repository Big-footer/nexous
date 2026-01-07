"""
IDGenerator - ID 생성 유틸리티

이 파일의 책임:
- 고유 ID 생성
- 다양한 ID 형식 지원 (UUID, ULID, 커스텀)
- 엔티티별 ID 프리픽스 관리
- ID 검증
"""

from typing import Optional
from enum import Enum
import uuid


class IDFormat(str, Enum):
    """ID 형식"""
    
    UUID4 = "uuid4"
    UUID7 = "uuid7"
    ULID = "ulid"
    SHORT = "short"
    CUSTOM = "custom"


class IDPrefix(str, Enum):
    """엔티티별 ID 프리픽스"""
    
    PROJECT = "proj"
    AGENT = "agent"
    TOOL = "tool"
    TASK = "task"
    SPAN = "span"
    SESSION = "sess"
    DOC = "doc"
    PLAN = "plan"
    STEP = "step"


class IDGenerator:
    """
    ID 생성 유틸리티
    
    다양한 형식의 고유 ID를 생성합니다.
    엔티티별 프리픽스를 지원합니다.
    """
    
    def __init__(
        self,
        default_format: IDFormat = IDFormat.UUID4,
        separator: str = "_",
    ) -> None:
        """
        IDGenerator 초기화
        
        Args:
            default_format: 기본 ID 형식
            separator: 프리픽스 구분자
        """
        self.default_format = default_format
        self.separator = separator
    
    def generate(
        self,
        prefix: Optional[IDPrefix] = None,
        format: Optional[IDFormat] = None,
    ) -> str:
        """
        ID 생성
        
        Args:
            prefix: ID 프리픽스
            format: ID 형식
            
        Returns:
            생성된 ID
        """
        # TODO: ID 생성 로직
        pass
    
    def generate_uuid4(self) -> str:
        """
        UUID4 생성
        
        Returns:
            UUID4 문자열
        """
        # TODO: UUID4 생성 로직
        pass
    
    def generate_uuid7(self) -> str:
        """
        UUID7 생성 (시간 기반)
        
        Returns:
            UUID7 문자열
        """
        # TODO: UUID7 생성 로직
        pass
    
    def generate_ulid(self) -> str:
        """
        ULID 생성
        
        Returns:
            ULID 문자열
        """
        # TODO: ULID 생성 로직
        pass
    
    def generate_short(
        self,
        length: int = 8,
    ) -> str:
        """
        짧은 ID 생성
        
        Args:
            length: ID 길이
            
        Returns:
            짧은 ID 문자열
        """
        # TODO: 짧은 ID 생성 로직
        pass
    
    def validate(
        self,
        id_str: str,
        expected_prefix: Optional[IDPrefix] = None,
    ) -> bool:
        """
        ID 유효성 검증
        
        Args:
            id_str: 검증할 ID
            expected_prefix: 예상 프리픽스
            
        Returns:
            유효성 여부
        """
        # TODO: ID 검증 로직
        pass
    
    def extract_prefix(
        self,
        id_str: str,
    ) -> Optional[IDPrefix]:
        """
        ID에서 프리픽스 추출
        
        Args:
            id_str: ID 문자열
            
        Returns:
            프리픽스 또는 None
        """
        # TODO: 프리픽스 추출 로직
        pass
    
    def extract_timestamp(
        self,
        id_str: str,
    ) -> Optional[float]:
        """
        ID에서 타임스탬프 추출 (시간 기반 ID의 경우)
        
        Args:
            id_str: ID 문자열
            
        Returns:
            타임스탬프 또는 None
        """
        # TODO: 타임스탬프 추출 로직
        pass


# 전역 인스턴스
_generator = IDGenerator()


def generate_id(
    prefix: Optional[IDPrefix] = None,
    format: Optional[IDFormat] = None,
) -> str:
    """
    ID 생성 함수 (편의 함수)
    
    Args:
        prefix: ID 프리픽스
        format: ID 형식
        
    Returns:
        생성된 ID
    """
    # TODO: 전역 생성기 사용
    return _generator.generate(prefix=prefix, format=format)
