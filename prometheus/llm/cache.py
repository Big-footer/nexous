"""
PROMETHEUS LLM Response Cache

LLM 응답을 캐싱하여 동일한 요청에 대한 반복 호출을 방지합니다.
"""

import hashlib
import json
import time
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import threading
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """캐시 엔트리"""
    key: str
    value: Any
    created_at: float
    ttl: float  # Time To Live (초)
    hit_count: int = 0
    
    @property
    def is_expired(self) -> bool:
        """만료 여부"""
        if self.ttl <= 0:  # TTL이 0 이하면 영구 캐시
            return False
        return time.time() - self.created_at > self.ttl
    
    def touch(self):
        """히트 카운트 증가"""
        self.hit_count += 1


@dataclass
class CacheStats:
    """캐시 통계"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0
    
    @property
    def hit_rate(self) -> float:
        """캐시 히트율"""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests * 100


class LLMResponseCache:
    """
    LLM 응답 캐시
    
    동일한 프롬프트에 대한 LLM 응답을 캐싱합니다.
    메모리 기반 캐시로, 프로세스 종료 시 초기화됩니다.
    
    Features:
    - TTL 기반 만료
    - LRU 스타일 eviction
    - 최대 크기 제한
    - 통계 추적
    
    Example:
        ```python
        cache = LLMResponseCache(max_size=1000, default_ttl=3600)
        
        # 캐시 확인 및 저장
        key = cache.make_key(provider="anthropic", prompt="Hello")
        if cached := cache.get(key):
            return cached
        
        response = llm.invoke(prompt)
        cache.set(key, response)
        ```
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: float = 3600,  # 1시간
        enable_stats: bool = True,
    ):
        """
        초기화
        
        Args:
            max_size: 최대 캐시 크기
            default_ttl: 기본 TTL (초)
            enable_stats: 통계 수집 여부
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.enable_stats = enable_stats
        
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._stats = CacheStats()
    
    def make_key(
        self,
        provider: str,
        model: str = "",
        messages: Optional[List[Dict]] = None,
        prompt: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """
        캐시 키 생성
        
        Args:
            provider: LLM 프로바이더
            model: 모델명
            messages: 메시지 리스트
            prompt: 단순 프롬프트
            temperature: 온도
            **kwargs: 추가 파라미터
        
        Returns:
            해시된 캐시 키
        """
        key_data = {
            "provider": provider,
            "model": model,
            "temperature": temperature,
        }
        
        if messages:
            # 메시지 리스트를 문자열로 변환
            key_data["messages"] = json.dumps(messages, sort_keys=True, ensure_ascii=False)
        elif prompt:
            key_data["prompt"] = prompt
        
        # 추가 파라미터 (정렬하여 일관성 유지)
        for k, v in sorted(kwargs.items()):
            if v is not None:
                key_data[k] = str(v)
        
        # JSON 직렬화 후 해시
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(key_str.encode()).hexdigest()[:32]
    
    def get(self, key: str) -> Optional[Any]:
        """
        캐시에서 값 조회
        
        Args:
            key: 캐시 키
        
        Returns:
            캐시된 값 또는 None
        """
        with self._lock:
            if self.enable_stats:
                self._stats.total_requests += 1
            
            entry = self._cache.get(key)
            
            if entry is None:
                if self.enable_stats:
                    self._stats.cache_misses += 1
                return None
            
            if entry.is_expired:
                # 만료된 엔트리 제거
                del self._cache[key]
                if self.enable_stats:
                    self._stats.cache_misses += 1
                    self._stats.evictions += 1
                return None
            
            # 히트
            entry.touch()
            if self.enable_stats:
                self._stats.cache_hits += 1
            
            logger.debug(f"캐시 히트: {key[:8]}... (hits: {entry.hit_count})")
            return entry.value
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
    ) -> None:
        """
        캐시에 값 저장
        
        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: TTL (초), None이면 기본값 사용
        """
        with self._lock:
            # 최대 크기 초과 시 eviction
            if len(self._cache) >= self.max_size:
                self._evict_oldest()
            
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                ttl=ttl if ttl is not None else self.default_ttl,
            )
            
            self._cache[key] = entry
            logger.debug(f"캐시 저장: {key[:8]}...")
    
    def delete(self, key: str) -> bool:
        """
        캐시에서 값 삭제
        
        Args:
            key: 캐시 키
        
        Returns:
            삭제 성공 여부
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """캐시 전체 초기화"""
        with self._lock:
            self._cache.clear()
            self._stats = CacheStats()
            logger.info("LLM 응답 캐시가 초기화되었습니다.")
    
    def _evict_oldest(self) -> None:
        """가장 오래된 엔트리 제거 (LRU 스타일)"""
        if not self._cache:
            return
        
        # 가장 오래된 엔트리 찾기
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].created_at
        )
        
        del self._cache[oldest_key]
        
        if self.enable_stats:
            self._stats.evictions += 1
        
        logger.debug(f"캐시 eviction: {oldest_key[:8]}...")
    
    def cleanup_expired(self) -> int:
        """만료된 엔트리 정리"""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if self.enable_stats:
                self._stats.evictions += len(expired_keys)
            
            if expired_keys:
                logger.info(f"만료된 캐시 {len(expired_keys)}개 정리됨")
            
            return len(expired_keys)
    
    @property
    def stats(self) -> CacheStats:
        """캐시 통계 반환"""
        return self._stats
    
    @property
    def size(self) -> int:
        """현재 캐시 크기"""
        return len(self._cache)
    
    def get_info(self) -> Dict[str, Any]:
        """캐시 정보 반환"""
        return {
            "size": self.size,
            "max_size": self.max_size,
            "default_ttl": self.default_ttl,
            "hit_rate": f"{self._stats.hit_rate:.1f}%",
            "total_requests": self._stats.total_requests,
            "cache_hits": self._stats.cache_hits,
            "cache_misses": self._stats.cache_misses,
            "evictions": self._stats.evictions,
        }


# =============================================================================
# 전역 캐시 인스턴스
# =============================================================================

_global_cache: Optional[LLMResponseCache] = None


def get_response_cache() -> LLMResponseCache:
    """전역 응답 캐시 반환"""
    global _global_cache
    if _global_cache is None:
        _global_cache = LLMResponseCache()
    return _global_cache


def set_response_cache(cache: LLMResponseCache) -> None:
    """전역 응답 캐시 설정"""
    global _global_cache
    _global_cache = cache


def clear_response_cache() -> None:
    """전역 응답 캐시 초기화"""
    global _global_cache
    if _global_cache:
        _global_cache.clear()


# =============================================================================
# LangChain 캐시 통합
# =============================================================================

def setup_langchain_cache(cache_type: str = "memory") -> None:
    """
    LangChain 전역 캐시 설정
    
    Args:
        cache_type: "memory" 또는 "sqlite"
    
    Example:
        ```python
        setup_langchain_cache("memory")
        # 이후 모든 LLM 호출이 자동으로 캐싱됨
        ```
    """
    try:
        from langchain.globals import set_llm_cache
        
        if cache_type == "memory":
            from langchain_community.cache import InMemoryCache
            set_llm_cache(InMemoryCache())
            logger.info("LangChain InMemoryCache 설정됨")
            
        elif cache_type == "sqlite":
            from langchain_community.cache import SQLiteCache
            cache_path = Path.home() / ".prometheus" / "llm_cache.db"
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            set_llm_cache(SQLiteCache(database_path=str(cache_path)))
            logger.info(f"LangChain SQLiteCache 설정됨: {cache_path}")
            
        else:
            raise ValueError(f"Unknown cache type: {cache_type}")
            
    except ImportError as e:
        logger.warning(f"LangChain 캐시 설정 실패: {e}")


def disable_langchain_cache() -> None:
    """LangChain 전역 캐시 비활성화"""
    try:
        from langchain.globals import set_llm_cache
        set_llm_cache(None)
        logger.info("LangChain 캐시 비활성화됨")
    except ImportError:
        pass
