"""
BaseMemory - 모든 메모리의 기반 추상 클래스

이 파일의 책임:
- 메모리 저장/조회/삭제 공통 인터페이스 정의
- 대화 히스토리 관리
- 컨텍스트 윈도우 관리
- 메모리 타입 구분 (short-term, long-term)
- 직렬화/역직렬화 인터페이스
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """메모리 유형"""
    
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


class MemoryEntry(BaseModel):
    """메모리 항목"""
    
    entry_id: str
    content: Any
    memory_type: MemoryType = MemoryType.SHORT_TERM
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ttl: Optional[int] = None  # Time to live in seconds


class ConversationMessage(BaseModel):
    """대화 메시지"""
    
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryConfig(BaseModel):
    """메모리 설정"""
    
    max_entries: int = 1000
    max_context_length: int = 4096
    enable_persistence: bool = True
    storage_path: Optional[str] = None


class BaseMemory(ABC):
    """
    모든 메모리의 기반 추상 클래스
    
    Agent의 메모리 관리를 위한 공통 인터페이스를 제공합니다.
    대화 히스토리, 컨텍스트, 장/단기 메모리를 관리합니다.
    """
    
    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
    ) -> None:
        """
        BaseMemory 초기화
        
        Args:
            config: 메모리 설정
        """
        self.config = config or MemoryConfig()
        self._conversation_history: List[ConversationMessage] = []
    
    @abstractmethod
    async def save(
        self,
        key: str,
        value: Any,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        메모리 저장
        
        Args:
            key: 저장 키
            value: 저장 값
            memory_type: 메모리 유형
            ttl: 만료 시간 (초)
            
        Returns:
            저장 성공 여부
        """
        pass
    
    @abstractmethod
    async def load(
        self,
        key: str,
    ) -> Optional[Any]:
        """
        메모리 로드
        
        Args:
            key: 로드 키
            
        Returns:
            저장된 값 또는 None
        """
        pass
    
    @abstractmethod
    async def delete(
        self,
        key: str,
    ) -> bool:
        """
        메모리 삭제
        
        Args:
            key: 삭제 키
            
        Returns:
            삭제 성공 여부
        """
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """전체 메모리 초기화"""
        pass
    
    async def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        대화 메시지 추가
        
        Args:
            role: 역할 (user, assistant, system)
            content: 메시지 내용
            metadata: 추가 메타데이터
        """
        # TODO: 메시지 추가 로직
        pass
    
    async def get_conversation_history(
        self,
        limit: Optional[int] = None,
        conversation_id: Optional[str] = None,
    ) -> List[ConversationMessage]:
        """
        대화 히스토리 조회
        
        Args:
            limit: 최대 반환 개수
            conversation_id: 대화 ID
            
        Returns:
            대화 메시지 목록
        """
        # TODO: 히스토리 조회 로직
        pass
    
    async def get_context_window(
        self,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        컨텍스트 윈도우 생성
        
        Args:
            max_tokens: 최대 토큰 수
            
        Returns:
            컨텍스트 문자열
        """
        # TODO: 컨텍스트 윈도우 생성 로직
        pass
    
    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """
        메모리 검색
        
        Args:
            query: 검색 쿼리
            limit: 최대 결과 수
            
        Returns:
            검색된 메모리 항목 목록
        """
        # TODO: 검색 로직
        pass
    
    async def persist(self) -> bool:
        """
        메모리 영구 저장
        
        Returns:
            저장 성공 여부
        """
        # TODO: 영구 저장 로직
        pass
    
    async def restore(self) -> bool:
        """
        저장된 메모리 복원
        
        Returns:
            복원 성공 여부
        """
        # TODO: 복원 로직
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """
        메모리 직렬화
        
        Returns:
            직렬화된 딕셔너리
        """
        # TODO: 직렬화 로직
        pass
    
    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "BaseMemory":
        """
        메모리 역직렬화
        
        Args:
            data: 직렬화된 데이터
            
        Returns:
            BaseMemory 인스턴스
        """
        # TODO: 역직렬화 로직
        pass
