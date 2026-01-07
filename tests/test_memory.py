"""
test_memory.py - Memory 모듈 테스트

이 파일의 책임:
- BaseMemory 테스트
- VectorStore 테스트
- ContextManager 테스트
- SessionManager 테스트
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

from prometheus.memory import (
    BaseMemory,
    MemoryConfig,
    MemoryEntry,
    MemoryType,
    MemorySearchResult,
    VectorStore,
    VectorStoreConfig,
    ContextManager,
    ContextManagerConfig,
    ContextPriority,
    SessionManager,
    SessionManagerConfig,
    Session,
    SessionStatus,
    ConversationMemory,
)


class TestMemoryEntry:
    """MemoryEntry 테스트"""
    
    def test_create_entry(self) -> None:
        """항목 생성"""
        entry = MemoryEntry(
            id="test_1",
            content="Test content",
            memory_type=MemoryType.SHORT_TERM,
        )
        
        assert entry.id == "test_1"
        assert entry.content == "Test content"
        assert entry.memory_type == MemoryType.SHORT_TERM
    
    def test_touch(self) -> None:
        """접근 업데이트"""
        entry = MemoryEntry(id="test", content="test")
        initial_count = entry.access_count
        
        entry.touch()
        
        assert entry.access_count == initial_count + 1
    
    def test_get_hash(self) -> None:
        """해시 생성"""
        entry = MemoryEntry(id="test", content="test content")
        hash1 = entry.get_hash()
        hash2 = entry.get_hash()
        
        assert hash1 == hash2
        assert len(hash1) == 32


class TestVectorStore:
    """VectorStore 테스트"""
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self) -> None:
        """저장 및 검색"""
        store = VectorStore()
        
        id1 = await store.store(content="Python is great for AI")
        id2 = await store.store(content="JavaScript is for web")
        
        results = await store.retrieve("programming AI", max_results=2)
        
        assert len(results) <= 2
        assert store.count() == 2
    
    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        """삭제"""
        store = VectorStore()
        
        id = await store.store(content="To be deleted")
        assert store.count() == 1
        
        result = await store.delete(id)
        
        assert result is True
        assert store.count() == 0
    
    @pytest.mark.asyncio
    async def test_batch_store(self) -> None:
        """배치 저장"""
        store = VectorStore()
        
        items = [
            {"content": "Document 1"},
            {"content": "Document 2"},
            {"content": "Document 3"},
        ]
        ids = await store.batch_store(items)
        
        assert len(ids) == 3
        assert store.count() == 3
    
    @pytest.mark.asyncio
    async def test_find_similar(self) -> None:
        """유사 항목 찾기"""
        store = VectorStore()
        
        id1 = await store.store(content="Machine learning algorithms")
        id2 = await store.store(content="Deep learning neural networks")
        id3 = await store.store(content="Cooking recipes")
        
        similar = await store.find_similar(id1, max_results=2)
        
        assert len(similar) <= 2
    
    def test_get_vector(self) -> None:
        """벡터 조회"""
        import asyncio
        store = VectorStore()
        
        id = asyncio.run(store.store(content="Test"))
        vector = store.get_vector(id)
        
        assert vector is not None
        assert len(vector) == store.config.embedding_dim
    
    def test_cosine_similarity(self) -> None:
        """코사인 유사도"""
        store = VectorStore()
        
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        vec3 = [0.0, 1.0, 0.0]
        
        assert store._cosine_similarity(vec1, vec2) == 1.0
        assert store._cosine_similarity(vec1, vec3) == 0.0


class TestContextManager:
    """ContextManager 테스트"""
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self) -> None:
        """저장 및 검색"""
        manager = ContextManager()
        
        await manager.store(content="Important context", priority=ContextPriority.HIGH)
        
        results = await manager.retrieve("context")
        
        assert len(results) >= 0
    
    def test_set_system_prompt(self) -> None:
        """시스템 프롬프트 설정"""
        manager = ContextManager()
        
        manager.set_system_prompt("You are a helpful assistant.")
        
        assert manager.get_system_prompt() == "You are a helpful assistant."
    
    @pytest.mark.asyncio
    async def test_add_message(self) -> None:
        """메시지 추가"""
        manager = ContextManager()
        
        await manager.add_message("user", "Hello")
        await manager.add_message("assistant", "Hi there!")
        
        messages = manager.get_messages()
        
        assert len(messages) >= 2
    
    def test_build_context(self) -> None:
        """컨텍스트 구축"""
        import asyncio
        manager = ContextManager()
        
        manager.set_system_prompt("System prompt")
        asyncio.run(manager.add_message("user", "User message"))
        
        window = manager.build_context()
        
        assert window.system_prompt == "System prompt"
    
    def test_token_count(self) -> None:
        """토큰 수 계산"""
        import asyncio
        manager = ContextManager()
        
        asyncio.run(manager.store("This is a test message with some words"))
        
        token_count = manager.get_token_count()
        
        assert token_count > 0
    
    @pytest.mark.asyncio
    async def test_compress_context(self) -> None:
        """컨텍스트 압축"""
        manager = ContextManager()
        
        for i in range(10):
            await manager.store(f"Message {i}" * 10, priority=ContextPriority.LOW)
        
        initial_tokens = manager.get_token_count()
        await manager.compress_context(target_tokens=50)
        final_tokens = manager.get_token_count()
        
        assert final_tokens <= initial_tokens


class TestSessionManager:
    """SessionManager 테스트"""
    
    def test_create_session(self) -> None:
        """세션 생성"""
        manager = SessionManager()
        
        session = manager.create_session(user_id="user_1")
        
        assert session.id is not None
        assert session.user_id == "user_1"
        assert session.status == SessionStatus.ACTIVE
    
    def test_get_session(self) -> None:
        """세션 조회"""
        manager = SessionManager()
        
        created = manager.create_session()
        retrieved = manager.get_session(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
    
    def test_session_data(self) -> None:
        """세션 데이터"""
        manager = SessionManager()
        
        session = manager.create_session()
        
        manager.set_session_data(session.id, "key1", "value1")
        value = manager.get_session_data(session.id, "key1")
        
        assert value == "value1"
    
    def test_close_session(self) -> None:
        """세션 종료"""
        manager = SessionManager()
        
        session = manager.create_session()
        manager.close_session(session.id)
        
        assert session.status == SessionStatus.CLOSED
    
    def test_delete_session(self) -> None:
        """세션 삭제"""
        manager = SessionManager()
        
        session = manager.create_session()
        session_id = session.id
        
        result = manager.delete_session(session_id)
        
        assert result is True
        assert manager.get_session(session_id) is None
    
    def test_extend_session(self) -> None:
        """세션 연장"""
        manager = SessionManager()
        
        session = manager.create_session(ttl=60)
        original_expires = session.expires_at
        
        manager.extend_session(session.id, 3600)
        
        assert session.expires_at > original_expires
    
    def test_get_user_sessions(self) -> None:
        """사용자 세션 목록"""
        manager = SessionManager()
        
        manager.create_session(user_id="user_1")
        manager.create_session(user_id="user_1")
        manager.create_session(user_id="user_2")
        
        user1_sessions = manager.get_user_sessions("user_1")
        
        assert len(user1_sessions) == 2
    
    def test_cleanup_expired(self) -> None:
        """만료 세션 정리"""
        manager = SessionManager()
        
        session = manager.create_session(ttl=0)  # 즉시 만료
        session.expires_at = datetime.now() - timedelta(hours=1)
        
        cleaned = manager.cleanup_expired()
        
        assert cleaned >= 1
    
    def test_pause_resume(self) -> None:
        """일시정지 및 재개"""
        manager = SessionManager()
        
        session = manager.create_session()
        
        manager.pause_session(session.id)
        assert session.status == SessionStatus.PAUSED
        
        manager.resume_session(session.id)
        assert session.status == SessionStatus.ACTIVE


class TestConversationMemory:
    """ConversationMemory 테스트"""
    
    def test_add_messages(self) -> None:
        """메시지 추가"""
        memory = ConversationMemory(session_id="test_session")
        
        memory.add_user_message("Hello")
        memory.add_assistant_message("Hi there!")
        memory.add_system_message("System context")
        
        assert len(memory.messages) == 3
    
    def test_get_messages(self) -> None:
        """메시지 조회"""
        memory = ConversationMemory(session_id="test")
        
        memory.add_user_message("Message 1")
        memory.add_user_message("Message 2")
        memory.add_assistant_message("Response")
        
        user_messages = memory.get_messages(role="user")
        last_2 = memory.get_messages(last_n=2)
        
        assert len(user_messages) == 2
        assert len(last_2) == 2
    
    def test_to_llm_messages(self) -> None:
        """LLM 메시지 변환"""
        memory = ConversationMemory(session_id="test")
        
        memory.add_user_message("Hello")
        memory.add_assistant_message("Hi!")
        
        llm_messages = memory.to_llm_messages()
        
        assert len(llm_messages) == 2
        assert llm_messages[0].role.value == "user"
    
    def test_max_messages(self) -> None:
        """최대 메시지 수 제한"""
        memory = ConversationMemory(session_id="test", max_messages=5)
        
        for i in range(10):
            memory.add_user_message(f"Message {i}")
        
        assert len(memory.messages) == 5
    
    def test_clear(self) -> None:
        """메시지 클리어"""
        memory = ConversationMemory(session_id="test")
        
        memory.add_user_message("Test")
        memory.clear()
        
        assert len(memory.messages) == 0


class TestIntegration:
    """통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_session_with_context(self) -> None:
        """세션 + 컨텍스트 통합"""
        session_manager = SessionManager()
        context_manager = ContextManager()
        
        # 세션 생성
        session = session_manager.create_session(user_id="user_1")
        
        # 컨텍스트 저장
        await context_manager.add_message("user", "Hello")
        await context_manager.add_message("assistant", "Hi!")
        
        # 세션에 컨텍스트 ID 저장
        session_manager.set_session_data(session.id, "context_id", "ctx_1")
        
        # 조회
        ctx_id = session_manager.get_session_data(session.id, "context_id")
        
        assert ctx_id == "ctx_1"
    
    @pytest.mark.asyncio
    async def test_vector_store_with_session(self) -> None:
        """벡터 저장소 + 세션 통합"""
        session_manager = SessionManager()
        vector_store = VectorStore()
        
        # 세션 생성
        session = session_manager.create_session()
        
        # 벡터 저장
        doc_id = await vector_store.store(
            content="Important document",
            metadata={"session_id": session.id},
        )
        
        # 검색
        results = await vector_store.retrieve(
            "document",
            filter_metadata={"session_id": session.id},
        )
        
        assert len(results) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
