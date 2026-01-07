"""
BaseMemory - 모든 Memory의 기반 추상 클래스

이 파일의 책임:
- Memory 공통 인터페이스 정의
- 메모리 저장/조회/삭제
- 메모리 타입 정의
- 직렬화/역직렬화
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
import json
import hashlib


class MemoryType(str, Enum):
    """메모리 타입"""
    
    SHORT_TERM = "short_term"      # 단기 메모리 (세션 내)
    LONG_TERM = "long_term"        # 장기 메모리 (영구 저장)
    WORKING = "working"            # 작업 메모리 (현재 컨텍스트)
    EPISODIC = "episodic"          # 에피소드 메모리 (경험)
    SEMANTIC = "semantic"          # 의미 메모리 (지식)


class MemoryEntry(BaseModel):
    """메모리 항목"""
    
    id: str
    content: Any
    memory_type: MemoryType = MemoryType.SHORT_TERM
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    access_count: int = 0
    importance: float = 0.5  # 0.0 ~ 1.0
    
    def get_hash(self) -> str:
        """콘텐츠 해시"""
        content_str = json.dumps(self.content, sort_keys=True, default=str)
        return hashlib.md5(content_str.encode()).hexdigest()
    
    def touch(self) -> None:
        """접근 시간 및 횟수 업데이트"""
        self.updated_at = datetime.now()
        self.access_count += 1


class MemoryQuery(BaseModel):
    """메모리 조회 쿼리"""
    
    query: Optional[str] = None
    embedding: Optional[List[float]] = None
    memory_type: Optional[MemoryType] = None
    metadata_filter: Dict[str, Any] = Field(default_factory=dict)
    min_importance: float = 0.0
    max_results: int = 10
    include_metadata: bool = True


class MemorySearchResult(BaseModel):
    """메모리 검색 결과"""
    
    entry: MemoryEntry
    score: float = 0.0
    rank: int = 0


class MemoryConfig(BaseModel):
    """메모리 설정"""
    
    max_entries: int = 10000
    default_memory_type: MemoryType = MemoryType.SHORT_TERM
    auto_cleanup: bool = True
    cleanup_threshold: int = 9000
    persist_path: Optional[str] = None
    embedding_dim: int = 384


class BaseMemory(ABC):
    """
    모든 Memory의 기반 추상 클래스
    
    PROMETHEUS의 모든 Memory가 상속하는 기반 클래스입니다.
    저장, 조회, 삭제 등의 공통 인터페이스를 제공합니다.
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
        self._entries: Dict[str, MemoryEntry] = {}
    
    @abstractmethod
    async def store(
        self,
        content: Any,
        memory_type: Optional[MemoryType] = None,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
    ) -> str:
        """
        메모리 저장
        
        Args:
            content: 저장할 내용
            memory_type: 메모리 타입
            metadata: 메타데이터
            importance: 중요도
            
        Returns:
            메모리 ID
        """
        pass
    
    @abstractmethod
    async def retrieve(
        self,
        query: Union[str, MemoryQuery],
        max_results: int = 10,
    ) -> List[MemorySearchResult]:
        """
        메모리 조회
        
        Args:
            query: 조회 쿼리
            max_results: 최대 결과 수
            
        Returns:
            검색 결과 목록
        """
        pass
    
    @abstractmethod
    async def delete(
        self,
        memory_id: str,
    ) -> bool:
        """
        메모리 삭제
        
        Args:
            memory_id: 메모리 ID
            
        Returns:
            삭제 성공 여부
        """
        pass
    
    def get(
        self,
        memory_id: str,
    ) -> Optional[MemoryEntry]:
        """
        ID로 메모리 조회
        
        Args:
            memory_id: 메모리 ID
            
        Returns:
            메모리 항목 또는 None
        """
        entry = self._entries.get(memory_id)
        if entry:
            entry.touch()
        return entry
    
    def exists(
        self,
        memory_id: str,
    ) -> bool:
        """메모리 존재 여부"""
        return memory_id in self._entries
    
    def count(
        self,
        memory_type: Optional[MemoryType] = None,
    ) -> int:
        """
        메모리 개수
        
        Args:
            memory_type: 필터링할 타입 (None이면 전체)
            
        Returns:
            메모리 개수
        """
        if memory_type is None:
            return len(self._entries)
        return sum(
            1 for e in self._entries.values()
            if e.memory_type == memory_type
        )
    
    def list_ids(
        self,
        memory_type: Optional[MemoryType] = None,
    ) -> List[str]:
        """
        메모리 ID 목록
        
        Args:
            memory_type: 필터링할 타입
            
        Returns:
            ID 목록
        """
        if memory_type is None:
            return list(self._entries.keys())
        return [
            id for id, entry in self._entries.items()
            if entry.memory_type == memory_type
        ]
    
    async def update(
        self,
        memory_id: str,
        content: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        importance: Optional[float] = None,
    ) -> bool:
        """
        메모리 업데이트
        
        Args:
            memory_id: 메모리 ID
            content: 새 내용
            metadata: 새 메타데이터
            importance: 새 중요도
            
        Returns:
            업데이트 성공 여부
        """
        entry = self._entries.get(memory_id)
        if entry is None:
            return False
        
        if content is not None:
            entry.content = content
        if metadata is not None:
            entry.metadata.update(metadata)
        if importance is not None:
            entry.importance = importance
        
        entry.updated_at = datetime.now()
        return True
    
    async def clear(
        self,
        memory_type: Optional[MemoryType] = None,
    ) -> int:
        """
        메모리 클리어
        
        Args:
            memory_type: 클리어할 타입 (None이면 전체)
            
        Returns:
            삭제된 항목 수
        """
        if memory_type is None:
            count = len(self._entries)
            self._entries.clear()
            return count
        
        to_delete = [
            id for id, entry in self._entries.items()
            if entry.memory_type == memory_type
        ]
        for id in to_delete:
            del self._entries[id]
        return len(to_delete)
    
    async def cleanup(
        self,
        max_entries: Optional[int] = None,
        min_importance: float = 0.0,
        older_than: Optional[datetime] = None,
    ) -> int:
        """
        메모리 정리
        
        Args:
            max_entries: 유지할 최대 항목 수
            min_importance: 최소 중요도
            older_than: 이 시간 이전 항목 삭제
            
        Returns:
            삭제된 항목 수
        """
        to_delete = []
        
        for id, entry in self._entries.items():
            # 중요도 기준
            if entry.importance < min_importance:
                to_delete.append(id)
                continue
            
            # 시간 기준
            if older_than and entry.updated_at < older_than:
                to_delete.append(id)
                continue
        
        # 최대 항목 수 기준
        if max_entries and len(self._entries) - len(to_delete) > max_entries:
            # 중요도와 접근 횟수 기준으로 정렬
            remaining = [
                (id, entry) for id, entry in self._entries.items()
                if id not in to_delete
            ]
            remaining.sort(
                key=lambda x: (x[1].importance, x[1].access_count),
                reverse=True,
            )
            
            # 초과분 삭제
            excess = len(remaining) - max_entries
            if excess > 0:
                to_delete.extend([id for id, _ in remaining[-excess:]])
        
        # 삭제 실행
        for id in to_delete:
            if id in self._entries:
                del self._entries[id]
        
        return len(to_delete)
    
    def _generate_id(self, content: Any) -> str:
        """메모리 ID 생성"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        content_hash = hashlib.md5(str(content).encode()).hexdigest()[:8]
        return f"mem_{timestamp}_{content_hash}"
    
    def get_stats(self) -> Dict[str, Any]:
        """
        메모리 통계
        
        Returns:
            통계 딕셔너리
        """
        type_counts = {}
        for entry in self._entries.values():
            t = entry.memory_type.value
            type_counts[t] = type_counts.get(t, 0) + 1
        
        return {
            "total_entries": len(self._entries),
            "by_type": type_counts,
            "max_entries": self.config.max_entries,
        }
    
    async def save(
        self,
        path: Optional[str] = None,
    ) -> bool:
        """
        메모리 저장 (영구화)
        
        Args:
            path: 저장 경로
            
        Returns:
            저장 성공 여부
        """
        save_path = path or self.config.persist_path
        if not save_path:
            return False
        
        try:
            data = {
                id: entry.model_dump()
                for id, entry in self._entries.items()
            }
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            return True
        except Exception:
            return False
    
    async def load(
        self,
        path: Optional[str] = None,
    ) -> bool:
        """
        메모리 로드
        
        Args:
            path: 로드 경로
            
        Returns:
            로드 성공 여부
        """
        load_path = path or self.config.persist_path
        if not load_path:
            return False
        
        try:
            with open(load_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._entries.clear()
            for id, entry_data in data.items():
                # datetime 변환
                if 'created_at' in entry_data:
                    entry_data['created_at'] = datetime.fromisoformat(entry_data['created_at'])
                if 'updated_at' in entry_data:
                    entry_data['updated_at'] = datetime.fromisoformat(entry_data['updated_at'])
                
                self._entries[id] = MemoryEntry(**entry_data)
            
            return True
        except Exception:
            return False
