"""
RAGTool - 벡터 검색 및 문서 처리 Tool

이 파일의 책임:
- 문서 임베딩 및 저장
- 벡터 유사도 검색
- 컨텍스트 검색
- 문서 청킹 및 처리
"""

from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from pydantic import BaseModel, Field
import hashlib

from prometheus.tools.base import (
    BaseTool,
    ToolSchema,
    ToolParameter,
    ToolParameterType,
    ToolResult,
    ToolConfig,
)


class ChunkingStrategy(str, Enum):
    """청킹 전략"""
    
    FIXED_SIZE = "fixed_size"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    SEMANTIC = "semantic"


class Document(BaseModel):
    """문서"""
    
    id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None
    
    def get_hash(self) -> str:
        """문서 해시"""
        return hashlib.md5(self.content.encode()).hexdigest()


class DocumentChunk(BaseModel):
    """문서 청크"""
    
    id: str
    document_id: str
    content: str
    chunk_index: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None


class SearchResult(BaseModel):
    """검색 결과"""
    
    chunk: DocumentChunk
    score: float
    rank: int


class RAGConfig(ToolConfig):
    """RAG Tool 설정"""
    
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
    chunk_size: int = 500
    chunk_overlap: int = 50
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.FIXED_SIZE
    top_k: int = 5
    min_score: float = 0.0
    persist_path: Optional[str] = None


class RAGTool(BaseTool):
    """
    RAG (Retrieval-Augmented Generation) Tool
    
    문서를 임베딩하고 벡터 검색을 수행합니다.
    검색된 컨텍스트를 LLM에 제공합니다.
    """
    
    name: str = "rag_search"
    description: str = "Search relevant documents and retrieve context for generation"
    
    def __init__(
        self,
        config: Optional[RAGConfig] = None,
        embedding_function: Optional[Any] = None,
    ) -> None:
        """
        RAGTool 초기화
        
        Args:
            config: 설정
            embedding_function: 임베딩 함수 (None이면 기본 사용)
        """
        super().__init__(config=config or RAGConfig())
        self._embedding_function = embedding_function
        self._documents: Dict[str, Document] = {}
        self._chunks: Dict[str, DocumentChunk] = {}
        self._index: Optional[Any] = None  # 벡터 인덱스
    
    def get_schema(self) -> ToolSchema:
        """Tool 스키마"""
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="query",
                    type=ToolParameterType.STRING,
                    description="Search query",
                    required=True,
                ),
                ToolParameter(
                    name="top_k",
                    type=ToolParameterType.INTEGER,
                    description="Number of results to return",
                    required=False,
                    default=5,
                ),
                ToolParameter(
                    name="filter",
                    type=ToolParameterType.OBJECT,
                    description="Metadata filter",
                    required=False,
                ),
            ],
            returns="List of relevant document chunks with scores",
            examples=[
                {
                    "query": "How to implement authentication?",
                    "top_k": 3,
                },
            ],
        )
    
    async def execute(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """
        문서 검색
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            filter: 메타데이터 필터
            
        Returns:
            검색 결과
        """
        k = top_k or self.config.top_k
        
        try:
            results = await self.search(query, k, filter)
            
            # 결과 포맷팅
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "content": result.chunk.content,
                    "score": result.score,
                    "rank": result.rank,
                    "document_id": result.chunk.document_id,
                    "metadata": result.chunk.metadata,
                })
            
            return ToolResult.success_result(
                output={
                    "query": query,
                    "results": formatted_results,
                    "total_found": len(formatted_results),
                },
            )
            
        except Exception as e:
            return ToolResult.error_result(str(e))
    
    async def add_document(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        document_id: Optional[str] = None,
    ) -> str:
        """
        문서 추가
        
        Args:
            content: 문서 내용
            metadata: 메타데이터
            document_id: 문서 ID (None이면 자동 생성)
            
        Returns:
            문서 ID
        """
        # 문서 ID 생성
        doc_id = document_id or f"doc_{len(self._documents)}_{hashlib.md5(content[:100].encode()).hexdigest()[:8]}"
        
        # 문서 생성
        document = Document(
            id=doc_id,
            content=content,
            metadata=metadata or {},
        )
        
        # 청킹
        chunks = self._chunk_document(document)
        
        # 임베딩 생성
        for chunk in chunks:
            embedding = await self._get_embedding(chunk.content)
            chunk.embedding = embedding
            self._chunks[chunk.id] = chunk
        
        # 문서 저장
        self._documents[doc_id] = document
        
        # 인덱스 업데이트
        await self._update_index(chunks)
        
        return doc_id
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
    ) -> List[str]:
        """
        여러 문서 추가
        
        Args:
            documents: 문서 목록 [{content, metadata, id?}]
            
        Returns:
            문서 ID 목록
        """
        doc_ids = []
        for doc in documents:
            doc_id = await self.add_document(
                content=doc["content"],
                metadata=doc.get("metadata"),
                document_id=doc.get("id"),
            )
            doc_ids.append(doc_id)
        return doc_ids
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        문서 검색
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            filter: 메타데이터 필터
            
        Returns:
            검색 결과 목록
        """
        # 쿼리 임베딩
        query_embedding = await self._get_embedding(query)
        
        # 유사도 계산
        results = []
        for chunk_id, chunk in self._chunks.items():
            if chunk.embedding is None:
                continue
            
            # 필터 적용
            if filter and not self._matches_filter(chunk.metadata, filter):
                continue
            
            # 코사인 유사도 계산
            score = self._cosine_similarity(query_embedding, chunk.embedding)
            
            if score >= self.config.min_score:
                results.append((chunk, score))
        
        # 정렬 및 상위 k개 선택
        results.sort(key=lambda x: x[1], reverse=True)
        results = results[:top_k]
        
        # SearchResult로 변환
        search_results = []
        for rank, (chunk, score) in enumerate(results, 1):
            search_results.append(SearchResult(
                chunk=chunk,
                score=score,
                rank=rank,
            ))
        
        return search_results
    
    async def get_context(
        self,
        query: str,
        max_tokens: int = 2000,
    ) -> str:
        """
        컨텍스트 조회 (프롬프트용)
        
        Args:
            query: 검색 쿼리
            max_tokens: 최대 토큰 수
            
        Returns:
            결합된 컨텍스트 문자열
        """
        results = await self.search(query, top_k=self.config.top_k)
        
        context_parts = []
        current_length = 0
        
        for result in results:
            chunk_length = len(result.chunk.content.split()) * 1.3  # 대략적인 토큰 추정
            if current_length + chunk_length > max_tokens:
                break
            
            context_parts.append(f"[Source {result.rank}]\n{result.chunk.content}")
            current_length += chunk_length
        
        return "\n\n".join(context_parts)
    
    def delete_document(
        self,
        document_id: str,
    ) -> bool:
        """
        문서 삭제
        
        Args:
            document_id: 문서 ID
            
        Returns:
            삭제 성공 여부
        """
        if document_id not in self._documents:
            return False
        
        # 관련 청크 삭제
        chunks_to_delete = [
            chunk_id for chunk_id, chunk in self._chunks.items()
            if chunk.document_id == document_id
        ]
        for chunk_id in chunks_to_delete:
            del self._chunks[chunk_id]
        
        # 문서 삭제
        del self._documents[document_id]
        
        return True
    
    def clear(self) -> None:
        """전체 데이터 삭제"""
        self._documents.clear()
        self._chunks.clear()
        self._index = None
    
    def _chunk_document(
        self,
        document: Document,
    ) -> List[DocumentChunk]:
        """
        문서 청킹
        
        Args:
            document: 문서
            
        Returns:
            청크 목록
        """
        content = document.content
        strategy = self.config.chunking_strategy
        
        if strategy == ChunkingStrategy.FIXED_SIZE:
            chunks = self._chunk_fixed_size(content)
        elif strategy == ChunkingStrategy.SENTENCE:
            chunks = self._chunk_by_sentence(content)
        elif strategy == ChunkingStrategy.PARAGRAPH:
            chunks = self._chunk_by_paragraph(content)
        else:
            chunks = self._chunk_fixed_size(content)
        
        # DocumentChunk 생성
        document_chunks = []
        for i, chunk_text in enumerate(chunks):
            chunk = DocumentChunk(
                id=f"{document.id}_chunk_{i}",
                document_id=document.id,
                content=chunk_text,
                chunk_index=i,
                metadata=document.metadata.copy(),
            )
            document_chunks.append(chunk)
        
        return document_chunks
    
    def _chunk_fixed_size(
        self,
        text: str,
    ) -> List[str]:
        """고정 크기 청킹"""
        chunks = []
        words = text.split()
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap
        
        i = 0
        while i < len(words):
            chunk_words = words[i:i + chunk_size]
            chunks.append(" ".join(chunk_words))
            i += chunk_size - overlap
        
        return chunks
    
    def _chunk_by_sentence(
        self,
        text: str,
    ) -> List[str]:
        """문장 단위 청킹"""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence.split())
            
            if current_length + sentence_length > self.config.chunk_size:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def _chunk_by_paragraph(
        self,
        text: str,
    ) -> List[str]:
        """단락 단위 청킹"""
        paragraphs = text.split("\n\n")
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_length = len(para.split())
            
            if current_length + para_length > self.config.chunk_size:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                current_chunk = [para]
                current_length = para_length
            else:
                current_chunk.append(para)
                current_length += para_length
        
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
        
        return chunks
    
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
            return await self._embedding_function(text)
        
        # 기본 임베딩 (간단한 TF-IDF 스타일)
        # 실제 사용 시에는 OpenAI 등의 임베딩 API 사용
        return self._simple_embedding(text)
    
    def _simple_embedding(
        self,
        text: str,
    ) -> List[float]:
        """
        간단한 임베딩 (테스트용)
        
        실제 사용 시에는 OpenAI, Sentence Transformers 등 사용
        """
        import hashlib
        
        # 단어 기반 해시 벡터 (데모용)
        words = text.lower().split()
        vector = [0.0] * 384  # 작은 차원
        
        for word in words:
            hash_val = int(hashlib.md5(word.encode()).hexdigest(), 16)
            for i in range(384):
                vector[i] += ((hash_val >> i) & 1) * 0.1
        
        # 정규화
        magnitude = sum(v**2 for v in vector) ** 0.5
        if magnitude > 0:
            vector = [v / magnitude for v in vector]
        
        return vector
    
    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float],
    ) -> float:
        """코사인 유사도 계산"""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a**2 for a in vec1) ** 0.5
        magnitude2 = sum(b**2 for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
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
    
    async def _update_index(
        self,
        chunks: List[DocumentChunk],
    ) -> None:
        """인덱스 업데이트 (확장 포인트)"""
        # 현재는 메모리 기반이므로 별도 인덱싱 불필요
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 조회"""
        base_stats = super().get_stats()
        base_stats.update({
            "document_count": len(self._documents),
            "chunk_count": len(self._chunks),
            "embedding_model": self.config.embedding_model,
        })
        return base_stats
