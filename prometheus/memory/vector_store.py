"""
VectorStore - 벡터 저장소

이 파일의 책임:
- 벡터 임베딩 저장 및 검색
- 유사도 기반 검색
- 인덱스 관리
- 영구 저장 지원
"""

from typing import Any, Dict, List, Optional, Tuple, Callable
from pydantic import BaseModel, Field
import hashlib
import math

from prometheus.memory.base import (
    BaseMemory,
    MemoryConfig,
    MemoryEntry,
    MemoryType,
    MemoryQuery,
    MemorySearchResult,
)


class VectorEntry(BaseModel):
    """벡터 항목"""
    
    id: str
    vector: List[float]
    content: Any
    metadata: Dict[str, Any] = Field(default_factory=dict)
    norm: float = 0.0  # 벡터 노름 (캐싱용)
    
    def compute_norm(self) -> float:
        """노름 계산"""
        self.norm = math.sqrt(sum(v ** 2 for v in self.vector))
        return self.norm


class VectorStoreConfig(MemoryConfig):
    """벡터 저장소 설정"""
    
    embedding_dim: int = 384
    distance_metric: str = "cosine"  # cosine, euclidean, dot
    normalize_vectors: bool = True
    index_type: str = "flat"  # flat, hnsw (확장용)


class VectorStore(BaseMemory):
    """
    벡터 저장소
    
    벡터 임베딩을 저장하고 유사도 기반 검색을 수행합니다.
    메모리 기반으로 동작하며, 영구 저장을 지원합니다.
    """
    
    def __init__(
        self,
        config: Optional[VectorStoreConfig] = None,
        embedding_function: Optional[Callable[[str], List[float]]] = None,
    ) -> None:
        """
        VectorStore 초기화
        
        Args:
            config: 저장소 설정
            embedding_function: 임베딩 함수
        """
        super().__init__(config=config or VectorStoreConfig())
        self._vectors: Dict[str, VectorEntry] = {}
        self._embedding_function = embedding_function
    
    async def store(
        self,
        content: Any,
        memory_type: Optional[MemoryType] = None,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
        vector: Optional[List[float]] = None,
    ) -> str:
        """
        벡터 저장
        
        Args:
            content: 저장할 내용
            memory_type: 메모리 타입
            metadata: 메타데이터
            importance: 중요도
            vector: 벡터 (None이면 자동 생성)
            
        Returns:
            메모리 ID
        """
        # ID 생성
        memory_id = self._generate_id(content)
        
        # 벡터 생성
        if vector is None:
            if isinstance(content, str):
                vector = await self._get_embedding(content)
            else:
                vector = await self._get_embedding(str(content))
        
        # 정규화
        if self.config.normalize_vectors:
            vector = self._normalize_vector(vector)
        
        # VectorEntry 생성
        vec_entry = VectorEntry(
            id=memory_id,
            vector=vector,
            content=content,
            metadata=metadata or {},
        )
        vec_entry.compute_norm()
        self._vectors[memory_id] = vec_entry
        
        # MemoryEntry 생성
        entry = MemoryEntry(
            id=memory_id,
            content=content,
            memory_type=memory_type or self.config.default_memory_type,
            metadata=metadata or {},
            embedding=vector,
            importance=importance,
        )
        self._entries[memory_id] = entry
        
        return memory_id
    
    async def retrieve(
        self,
        query: Any,
        max_results: int = 10,
        min_score: float = 0.0,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[MemorySearchResult]:
        """
        유사도 검색
        
        Args:
            query: 검색 쿼리 (문자열 또는 벡터)
            max_results: 최대 결과 수
            min_score: 최소 유사도
            filter_metadata: 메타데이터 필터
            
        Returns:
            검색 결과 목록
        """
        # 쿼리 벡터 생성
        if isinstance(query, list):
            query_vector = query
        elif isinstance(query, str):
            query_vector = await self._get_embedding(query)
        elif isinstance(query, MemoryQuery):
            if query.embedding:
                query_vector = query.embedding
            else:
                query_vector = await self._get_embedding(query.query or "")
            max_results = query.max_results
            filter_metadata = query.metadata_filter
        else:
            query_vector = await self._get_embedding(str(query))
        
        # 정규화
        if self.config.normalize_vectors:
            query_vector = self._normalize_vector(query_vector)
        
        # 유사도 계산
        scores: List[Tuple[str, float]] = []
        for id, vec_entry in self._vectors.items():
            # 메타데이터 필터
            if filter_metadata:
                if not self._matches_filter(vec_entry.metadata, filter_metadata):
                    continue
            
            # 유사도 계산
            score = self._compute_similarity(query_vector, vec_entry.vector)
            if score >= min_score:
                scores.append((id, score))
        
        # 정렬
        scores.sort(key=lambda x: x[1], reverse=True)
        scores = scores[:max_results]
        
        # 결과 생성
        results = []
        for rank, (id, score) in enumerate(scores, 1):
            entry = self._entries.get(id)
            if entry:
                results.append(MemorySearchResult(
                    entry=entry,
                    score=score,
                    rank=rank,
                ))
        
        return results
    
    async def delete(
        self,
        memory_id: str,
    ) -> bool:
        """
        벡터 삭제
        
        Args:
            memory_id: 메모리 ID
            
        Returns:
            삭제 성공 여부
        """
        if memory_id in self._vectors:
            del self._vectors[memory_id]
        
        if memory_id in self._entries:
            del self._entries[memory_id]
            return True
        
        return False
    
    async def update_vector(
        self,
        memory_id: str,
        vector: List[float],
    ) -> bool:
        """
        벡터 업데이트
        
        Args:
            memory_id: 메모리 ID
            vector: 새 벡터
            
        Returns:
            업데이트 성공 여부
        """
        if memory_id not in self._vectors:
            return False
        
        if self.config.normalize_vectors:
            vector = self._normalize_vector(vector)
        
        self._vectors[memory_id].vector = vector
        self._vectors[memory_id].compute_norm()
        
        if memory_id in self._entries:
            self._entries[memory_id].embedding = vector
        
        return True
    
    async def batch_store(
        self,
        items: List[Dict[str, Any]],
    ) -> List[str]:
        """
        배치 저장
        
        Args:
            items: [{content, metadata?, importance?, vector?}]
            
        Returns:
            메모리 ID 목록
        """
        ids = []
        for item in items:
            id = await self.store(
                content=item["content"],
                metadata=item.get("metadata"),
                importance=item.get("importance", 0.5),
                vector=item.get("vector"),
            )
            ids.append(id)
        return ids
    
    def get_vector(
        self,
        memory_id: str,
    ) -> Optional[List[float]]:
        """
        벡터 조회
        
        Args:
            memory_id: 메모리 ID
            
        Returns:
            벡터 또는 None
        """
        vec_entry = self._vectors.get(memory_id)
        return vec_entry.vector if vec_entry else None
    
    async def find_similar(
        self,
        memory_id: str,
        max_results: int = 5,
        exclude_self: bool = True,
    ) -> List[MemorySearchResult]:
        """
        유사한 항목 찾기
        
        Args:
            memory_id: 기준 메모리 ID
            max_results: 최대 결과 수
            exclude_self: 자기 자신 제외
            
        Returns:
            유사한 항목 목록
        """
        vector = self.get_vector(memory_id)
        if vector is None:
            return []
        
        results = await self.retrieve(vector, max_results + (1 if exclude_self else 0))
        
        if exclude_self:
            results = [r for r in results if r.entry.id != memory_id]
        
        return results[:max_results]
    
    async def _get_embedding(
        self,
        text: str,
    ) -> List[float]:
        """
        임베딩 생성
        
        Args:
            text: 텍스트
            
        Returns:
            임베딩 벡터
        """
        if self._embedding_function:
            result = self._embedding_function(text)
            # async 함수인 경우
            if hasattr(result, '__await__'):
                return await result
            return result
        
        # 기본 임베딩 (해시 기반, 테스트용)
        return self._simple_embedding(text)
    
    def _simple_embedding(
        self,
        text: str,
    ) -> List[float]:
        """간단한 임베딩 (테스트용)"""
        dim = self.config.embedding_dim
        vector = [0.0] * dim
        
        words = text.lower().split()
        for word in words:
            hash_val = int(hashlib.md5(word.encode()).hexdigest(), 16)
            for i in range(dim):
                vector[i] += ((hash_val >> (i % 128)) & 1) * 0.1
        
        return self._normalize_vector(vector)
    
    def _normalize_vector(
        self,
        vector: List[float],
    ) -> List[float]:
        """벡터 정규화"""
        magnitude = math.sqrt(sum(v ** 2 for v in vector))
        if magnitude > 0:
            return [v / magnitude for v in vector]
        return vector
    
    def _compute_similarity(
        self,
        vec1: List[float],
        vec2: List[float],
    ) -> float:
        """
        유사도 계산
        
        Args:
            vec1: 벡터 1
            vec2: 벡터 2
            
        Returns:
            유사도 점수
        """
        metric = self.config.distance_metric
        
        if metric == "cosine":
            return self._cosine_similarity(vec1, vec2)
        elif metric == "euclidean":
            return self._euclidean_similarity(vec1, vec2)
        elif metric == "dot":
            return self._dot_product(vec1, vec2)
        else:
            return self._cosine_similarity(vec1, vec2)
    
    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float],
    ) -> float:
        """코사인 유사도"""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = math.sqrt(sum(a ** 2 for a in vec1))
        mag2 = math.sqrt(sum(b ** 2 for b in vec2))
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)
    
    def _euclidean_similarity(
        self,
        vec1: List[float],
        vec2: List[float],
    ) -> float:
        """유클리드 유사도 (거리의 역수)"""
        distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(vec1, vec2)))
        return 1.0 / (1.0 + distance)
    
    def _dot_product(
        self,
        vec1: List[float],
        vec2: List[float],
    ) -> float:
        """내적"""
        return sum(a * b for a, b in zip(vec1, vec2))
    
    def _matches_filter(
        self,
        metadata: Dict[str, Any],
        filter: Dict[str, Any],
    ) -> bool:
        """메타데이터 필터 매칭"""
        for key, value in filter.items():
            if key not in metadata:
                return False
            if metadata[key] != value:
                return False
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 조회"""
        base_stats = super().get_stats()
        base_stats.update({
            "vector_count": len(self._vectors),
            "embedding_dim": self.config.embedding_dim,
            "distance_metric": self.config.distance_metric,
        })
        return base_stats
