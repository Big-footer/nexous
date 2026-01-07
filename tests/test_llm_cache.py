"""
LLM 캐시 테스트
"""

import pytest
import time
from prometheus.llm.cache import (
    LLMResponseCache,
    CacheEntry,
    CacheStats,
    get_response_cache,
    clear_response_cache,
)


class TestCacheEntry:
    """CacheEntry 테스트"""
    
    def test_cache_entry_creation(self):
        """캐시 엔트리 생성"""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=time.time(),
            ttl=3600,
        )
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.hit_count == 0
    
    def test_cache_entry_not_expired(self):
        """만료되지 않은 엔트리"""
        entry = CacheEntry(
            key="test",
            value="value",
            created_at=time.time(),
            ttl=3600,
        )
        assert not entry.is_expired
    
    def test_cache_entry_expired(self):
        """만료된 엔트리"""
        entry = CacheEntry(
            key="test",
            value="value",
            created_at=time.time() - 100,  # 100초 전
            ttl=50,  # 50초 TTL
        )
        assert entry.is_expired
    
    def test_cache_entry_touch(self):
        """히트 카운트 증가"""
        entry = CacheEntry(
            key="test",
            value="value",
            created_at=time.time(),
            ttl=3600,
        )
        assert entry.hit_count == 0
        entry.touch()
        assert entry.hit_count == 1
        entry.touch()
        assert entry.hit_count == 2


class TestLLMResponseCache:
    """LLMResponseCache 테스트"""
    
    @pytest.fixture
    def cache(self):
        """캐시 fixture"""
        return LLMResponseCache(max_size=100, default_ttl=3600)
    
    def test_cache_creation(self, cache):
        """캐시 생성"""
        assert cache.max_size == 100
        assert cache.default_ttl == 3600
        assert cache.size == 0
    
    def test_make_key_with_prompt(self, cache):
        """프롬프트로 키 생성"""
        key1 = cache.make_key(provider="anthropic", prompt="Hello")
        key2 = cache.make_key(provider="anthropic", prompt="Hello")
        key3 = cache.make_key(provider="anthropic", prompt="World")
        
        assert key1 == key2  # 같은 입력 -> 같은 키
        assert key1 != key3  # 다른 입력 -> 다른 키
    
    def test_make_key_with_messages(self, cache):
        """메시지로 키 생성"""
        messages = [{"role": "user", "content": "Hello"}]
        key = cache.make_key(provider="openai", messages=messages)
        
        assert len(key) == 32
    
    def test_set_and_get(self, cache):
        """저장 및 조회"""
        key = cache.make_key(provider="test", prompt="hello")
        cache.set(key, "response_value")
        
        result = cache.get(key)
        assert result == "response_value"
    
    def test_get_nonexistent(self, cache):
        """존재하지 않는 키 조회"""
        result = cache.get("nonexistent_key")
        assert result is None
    
    def test_cache_expiration(self):
        """캐시 만료"""
        cache = LLMResponseCache(max_size=100, default_ttl=0.1)  # 0.1초 TTL
        
        key = cache.make_key(provider="test", prompt="hello")
        cache.set(key, "value")
        
        # 즉시 조회 - 히트
        assert cache.get(key) == "value"
        
        # TTL 대기 후 조회 - 만료
        time.sleep(0.2)
        assert cache.get(key) is None
    
    def test_cache_delete(self, cache):
        """캐시 삭제"""
        key = cache.make_key(provider="test", prompt="hello")
        cache.set(key, "value")
        
        assert cache.get(key) == "value"
        assert cache.delete(key) == True
        assert cache.get(key) is None
        assert cache.delete(key) == False  # 이미 삭제됨
    
    def test_cache_clear(self, cache):
        """캐시 전체 초기화"""
        for i in range(10):
            key = cache.make_key(provider="test", prompt=f"hello{i}")
            cache.set(key, f"value{i}")
        
        assert cache.size == 10
        cache.clear()
        assert cache.size == 0
    
    def test_cache_eviction(self):
        """캐시 eviction (최대 크기 초과)"""
        cache = LLMResponseCache(max_size=5, default_ttl=3600)
        
        # 5개 저장
        for i in range(5):
            key = cache.make_key(provider="test", prompt=f"hello{i}")
            cache.set(key, f"value{i}")
        
        assert cache.size == 5
        
        # 1개 더 저장 -> eviction 발생
        key = cache.make_key(provider="test", prompt="hello_new")
        cache.set(key, "value_new")
        
        assert cache.size == 5  # 여전히 5개


class TestCacheStats:
    """캐시 통계 테스트"""
    
    def test_stats_hit_rate(self):
        """히트율 계산"""
        cache = LLMResponseCache(max_size=100, default_ttl=3600)
        
        key = cache.make_key(provider="test", prompt="hello")
        cache.set(key, "value")
        
        # 히트 2번, 미스 1번
        cache.get(key)
        cache.get(key)
        cache.get("nonexistent")
        
        stats = cache.stats
        assert stats.total_requests == 3
        assert stats.cache_hits == 2
        assert stats.cache_misses == 1
        assert stats.hit_rate == pytest.approx(66.67, rel=0.1)
    
    def test_get_info(self):
        """캐시 정보"""
        cache = LLMResponseCache(max_size=100, default_ttl=3600)
        
        for i in range(5):
            key = cache.make_key(provider="test", prompt=f"hello{i}")
            cache.set(key, f"value{i}")
        
        info = cache.get_info()
        assert info["size"] == 5
        assert info["max_size"] == 100
        assert info["default_ttl"] == 3600


class TestGlobalCache:
    """전역 캐시 테스트"""
    
    def test_get_response_cache(self):
        """전역 캐시 반환"""
        cache = get_response_cache()
        assert cache is not None
        assert isinstance(cache, LLMResponseCache)
    
    def test_clear_response_cache(self):
        """전역 캐시 초기화"""
        cache = get_response_cache()
        key = cache.make_key(provider="test", prompt="hello")
        cache.set(key, "value")
        
        clear_response_cache()
        assert cache.size == 0
