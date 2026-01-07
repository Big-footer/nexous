"""
ContextManager - 컨텍스트 관리

이 파일의 책임:
- 대화 컨텍스트 관리
- 컨텍스트 윈도우 관리
- 토큰 제한 처리
- 컨텍스트 압축
"""

from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field

from prometheus.memory.base import (
    BaseMemory,
    MemoryConfig,
    MemoryEntry,
    MemoryType,
    MemoryQuery,
    MemorySearchResult,
)
from prometheus.llm.base import Message, MessageRole


class ContextPriority(str, Enum):
    """컨텍스트 우선순위"""
    
    CRITICAL = "critical"      # 반드시 포함
    HIGH = "high"             # 높은 우선순위
    MEDIUM = "medium"         # 중간 우선순위
    LOW = "low"               # 낮은 우선순위
    OPTIONAL = "optional"     # 선택적


class ContextEntry(BaseModel):
    """컨텍스트 항목"""
    
    id: str
    content: str
    priority: ContextPriority = ContextPriority.MEDIUM
    token_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """만료 여부"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


class ContextWindow(BaseModel):
    """컨텍스트 윈도우"""
    
    system_prompt: Optional[str] = None
    entries: List[ContextEntry] = Field(default_factory=list)
    max_tokens: int = 4000
    current_tokens: int = 0
    
    def add_entry(self, entry: ContextEntry) -> bool:
        """항목 추가"""
        if self.current_tokens + entry.token_count > self.max_tokens:
            return False
        self.entries.append(entry)
        self.current_tokens += entry.token_count
        return True
    
    def remove_entry(self, entry_id: str) -> bool:
        """항목 제거"""
        for i, entry in enumerate(self.entries):
            if entry.id == entry_id:
                self.current_tokens -= entry.token_count
                self.entries.pop(i)
                return True
        return False
    
    def get_available_tokens(self) -> int:
        """사용 가능한 토큰 수"""
        return self.max_tokens - self.current_tokens
    
    def to_messages(self) -> List[Message]:
        """Message 리스트로 변환"""
        messages = []
        if self.system_prompt:
            messages.append(Message.system(self.system_prompt))
        
        for entry in self.entries:
            # metadata에서 role 추출
            role = entry.metadata.get("role", "user")
            if role == "system":
                messages.append(Message.system(entry.content))
            elif role == "assistant":
                messages.append(Message.assistant(entry.content))
            else:
                messages.append(Message.user(entry.content))
        
        return messages


class ContextManagerConfig(MemoryConfig):
    """컨텍스트 관리자 설정"""
    
    max_context_tokens: int = 8000
    reserved_output_tokens: int = 2000
    compression_threshold: float = 0.9
    auto_compress: bool = True
    include_system_prompt: bool = True


class ContextManager(BaseMemory):
    """
    컨텍스트 관리자
    
    대화 컨텍스트를 관리하고 토큰 제한을 처리합니다.
    우선순위 기반으로 컨텍스트를 최적화합니다.
    """
    
    def __init__(
        self,
        config: Optional[ContextManagerConfig] = None,
    ) -> None:
        """
        ContextManager 초기화
        
        Args:
            config: 설정
        """
        super().__init__(config=config or ContextManagerConfig())
        self._context_window = ContextWindow(
            max_tokens=self.config.max_context_tokens - self.config.reserved_output_tokens
        )
        self._system_prompt: Optional[str] = None
        self._context_entries: Dict[str, ContextEntry] = {}
    
    async def store(
        self,
        content: Any,
        memory_type: Optional[MemoryType] = None,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
        priority: ContextPriority = ContextPriority.MEDIUM,
    ) -> str:
        """
        컨텍스트 저장
        
        Args:
            content: 내용
            memory_type: 메모리 타입
            metadata: 메타데이터
            importance: 중요도
            priority: 우선순위
            
        Returns:
            컨텍스트 ID
        """
        content_str = str(content)
        token_count = self._estimate_tokens(content_str)
        
        context_id = self._generate_id(content)
        
        entry = ContextEntry(
            id=context_id,
            content=content_str,
            priority=priority,
            token_count=token_count,
            metadata=metadata or {},
        )
        self._context_entries[context_id] = entry
        
        # 메모리 항목도 저장
        memory_entry = MemoryEntry(
            id=context_id,
            content=content,
            memory_type=memory_type or MemoryType.WORKING,
            metadata=metadata or {},
            importance=importance,
        )
        self._entries[context_id] = memory_entry
        
        return context_id
    
    async def retrieve(
        self,
        query: Any,
        max_results: int = 10,
    ) -> List[MemorySearchResult]:
        """
        컨텍스트 검색
        
        Args:
            query: 검색 쿼리
            max_results: 최대 결과 수
            
        Returns:
            검색 결과
        """
        # 간단한 키워드 매칭
        query_str = str(query).lower()
        results = []
        
        for id, entry in self._entries.items():
            content_str = str(entry.content).lower()
            # 간단한 점수 계산 (키워드 일치도)
            score = sum(1 for word in query_str.split() if word in content_str)
            if score > 0:
                results.append((entry, score / len(query_str.split())))
        
        results.sort(key=lambda x: x[1], reverse=True)
        
        return [
            MemorySearchResult(entry=entry, score=score, rank=i+1)
            for i, (entry, score) in enumerate(results[:max_results])
        ]
    
    async def delete(
        self,
        memory_id: str,
    ) -> bool:
        """
        컨텍스트 삭제
        
        Args:
            memory_id: 메모리 ID
            
        Returns:
            삭제 성공 여부
        """
        deleted = False
        
        if memory_id in self._context_entries:
            del self._context_entries[memory_id]
            deleted = True
        
        if memory_id in self._entries:
            del self._entries[memory_id]
            deleted = True
        
        self._context_window.remove_entry(memory_id)
        
        return deleted
    
    def set_system_prompt(
        self,
        prompt: str,
    ) -> None:
        """
        시스템 프롬프트 설정
        
        Args:
            prompt: 시스템 프롬프트
        """
        self._system_prompt = prompt
        self._context_window.system_prompt = prompt
    
    def get_system_prompt(self) -> Optional[str]:
        """시스템 프롬프트 조회"""
        return self._system_prompt
    
    async def add_message(
        self,
        role: str,
        content: str,
        priority: ContextPriority = ContextPriority.MEDIUM,
    ) -> str:
        """
        메시지 추가
        
        Args:
            role: 역할 (user, assistant, system)
            content: 내용
            priority: 우선순위
            
        Returns:
            컨텍스트 ID
        """
        return await self.store(
            content=content,
            metadata={"role": role},
            priority=priority,
        )
    
    def build_context(
        self,
        max_tokens: Optional[int] = None,
    ) -> ContextWindow:
        """
        컨텍스트 윈도우 구축
        
        Args:
            max_tokens: 최대 토큰 수
            
        Returns:
            구축된 컨텍스트 윈도우
        """
        max_tokens = max_tokens or (
            self.config.max_context_tokens - self.config.reserved_output_tokens
        )
        
        window = ContextWindow(
            system_prompt=self._system_prompt,
            max_tokens=max_tokens,
        )
        
        # 우선순위별 정렬
        sorted_entries = sorted(
            self._context_entries.values(),
            key=lambda e: (
                self._priority_value(e.priority),
                e.created_at.timestamp(),
            ),
            reverse=True,
        )
        
        # 만료되지 않은 항목 추가
        for entry in sorted_entries:
            if not entry.is_expired():
                if not window.add_entry(entry):
                    # 공간 부족 시 압축 시도
                    if self.config.auto_compress:
                        self._compress_window(window, entry.token_count)
                        window.add_entry(entry)
                    else:
                        break
        
        return window
    
    def get_messages(
        self,
        max_tokens: Optional[int] = None,
    ) -> List[Message]:
        """
        Message 리스트 조회
        
        Args:
            max_tokens: 최대 토큰 수
            
        Returns:
            Message 리스트
        """
        window = self.build_context(max_tokens)
        return window.to_messages()
    
    async def compress_context(
        self,
        target_tokens: int,
    ) -> int:
        """
        컨텍스트 압축
        
        Args:
            target_tokens: 목표 토큰 수
            
        Returns:
            압축 후 토큰 수
        """
        current_tokens = sum(e.token_count for e in self._context_entries.values())
        
        if current_tokens <= target_tokens:
            return current_tokens
        
        # 낮은 우선순위부터 제거
        entries_by_priority = sorted(
            self._context_entries.items(),
            key=lambda x: self._priority_value(x[1].priority),
        )
        
        for entry_id, entry in entries_by_priority:
            if entry.priority == ContextPriority.CRITICAL:
                continue
            
            await self.delete(entry_id)
            current_tokens -= entry.token_count
            
            if current_tokens <= target_tokens:
                break
        
        return current_tokens
    
    def _compress_window(
        self,
        window: ContextWindow,
        needed_tokens: int,
    ) -> None:
        """윈도우 내 압축"""
        # 가장 낮은 우선순위 항목부터 제거
        entries_to_remove = []
        freed_tokens = 0
        
        sorted_entries = sorted(
            window.entries,
            key=lambda e: self._priority_value(e.priority),
        )
        
        for entry in sorted_entries:
            if entry.priority == ContextPriority.CRITICAL:
                continue
            
            entries_to_remove.append(entry.id)
            freed_tokens += entry.token_count
            
            if freed_tokens >= needed_tokens:
                break
        
        for entry_id in entries_to_remove:
            window.remove_entry(entry_id)
    
    def _priority_value(
        self,
        priority: ContextPriority,
    ) -> int:
        """우선순위 값"""
        values = {
            ContextPriority.CRITICAL: 5,
            ContextPriority.HIGH: 4,
            ContextPriority.MEDIUM: 3,
            ContextPriority.LOW: 2,
            ContextPriority.OPTIONAL: 1,
        }
        return values.get(priority, 0)
    
    def _estimate_tokens(
        self,
        text: str,
    ) -> int:
        """토큰 수 추정 (단어 수 * 1.3)"""
        return int(len(text.split()) * 1.3)
    
    def get_token_count(self) -> int:
        """현재 토큰 수"""
        return sum(e.token_count for e in self._context_entries.values())
    
    def get_available_tokens(self) -> int:
        """사용 가능한 토큰 수"""
        max_tokens = self.config.max_context_tokens - self.config.reserved_output_tokens
        return max_tokens - self.get_token_count()
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 조회"""
        base_stats = super().get_stats()
        
        priority_counts = {}
        for entry in self._context_entries.values():
            p = entry.priority.value
            priority_counts[p] = priority_counts.get(p, 0) + 1
        
        base_stats.update({
            "context_entries": len(self._context_entries),
            "current_tokens": self.get_token_count(),
            "available_tokens": self.get_available_tokens(),
            "by_priority": priority_counts,
            "has_system_prompt": self._system_prompt is not None,
        })
        return base_stats
