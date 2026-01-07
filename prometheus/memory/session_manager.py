"""
SessionManager - 세션 관리

이 파일의 책임:
- 세션 생성 및 관리
- 세션 상태 유지
- 세션 기반 메모리 격리
- 세션 만료 처리
"""

from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import uuid

from prometheus.llm.base import Message


class SessionStatus(str, Enum):
    """세션 상태"""
    
    ACTIVE = "active"
    PAUSED = "paused"
    EXPIRED = "expired"
    CLOSED = "closed"


class SessionData(BaseModel):
    """세션 데이터"""
    
    key: str
    value: Any
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Session(BaseModel):
    """세션"""
    
    id: str
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    status: SessionStatus = SessionStatus.ACTIVE
    data: Dict[str, SessionData] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    access_count: int = 0
    
    def is_expired(self) -> bool:
        """만료 여부"""
        if self.status == SessionStatus.EXPIRED:
            return True
        if self.expires_at and datetime.now() > self.expires_at:
            return True
        return False
    
    def touch(self) -> None:
        """접근 시간 업데이트"""
        self.updated_at = datetime.now()
        self.access_count += 1
    
    def set(
        self,
        key: str,
        value: Any,
    ) -> None:
        """값 설정"""
        if key in self.data:
            self.data[key].value = value
            self.data[key].updated_at = datetime.now()
        else:
            self.data[key] = SessionData(key=key, value=value)
        self.touch()
    
    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """값 조회"""
        if key in self.data:
            self.touch()
            return self.data[key].value
        return default
    
    def delete(
        self,
        key: str,
    ) -> bool:
        """값 삭제"""
        if key in self.data:
            del self.data[key]
            self.touch()
            return True
        return False
    
    def clear(self) -> None:
        """데이터 클리어"""
        self.data.clear()
        self.touch()


class SessionManagerConfig(BaseModel):
    """세션 관리자 설정"""
    
    default_ttl: int = 3600  # 초
    max_sessions: int = 1000
    auto_cleanup: bool = True
    cleanup_interval: int = 300  # 초
    persist_sessions: bool = False


class SessionManager:
    """
    세션 관리자
    
    세션을 생성하고 관리합니다.
    세션 기반 메모리 격리를 제공합니다.
    """
    
    def __init__(
        self,
        config: Optional[SessionManagerConfig] = None,
    ) -> None:
        """
        SessionManager 초기화
        
        Args:
            config: 설정
        """
        self.config = config or SessionManagerConfig()
        self._sessions: Dict[str, Session] = {}
        self._user_sessions: Dict[str, List[str]] = {}  # user_id -> session_ids
        self._last_cleanup = datetime.now()
    
    def create_session(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """
        세션 생성
        
        Args:
            user_id: 사용자 ID
            project_id: 프로젝트 ID
            ttl: 만료 시간 (초)
            metadata: 메타데이터
            
        Returns:
            생성된 세션
        """
        # 자동 정리
        if self.config.auto_cleanup:
            self._auto_cleanup()
        
        # 세션 ID 생성
        session_id = f"sess_{uuid.uuid4().hex[:16]}"
        
        # 만료 시간 계산
        ttl_seconds = ttl or self.config.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
        
        # 세션 생성
        session = Session(
            id=session_id,
            user_id=user_id,
            project_id=project_id,
            expires_at=expires_at,
            metadata=metadata or {},
        )
        
        self._sessions[session_id] = session
        
        # 사용자-세션 매핑
        if user_id:
            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = []
            self._user_sessions[user_id].append(session_id)
        
        return session
    
    def get_session(
        self,
        session_id: str,
    ) -> Optional[Session]:
        """
        세션 조회
        
        Args:
            session_id: 세션 ID
            
        Returns:
            세션 또는 None
        """
        session = self._sessions.get(session_id)
        
        if session is None:
            return None
        
        if session.is_expired():
            session.status = SessionStatus.EXPIRED
            return None
        
        session.touch()
        return session
    
    def get_user_sessions(
        self,
        user_id: str,
        include_expired: bool = False,
    ) -> List[Session]:
        """
        사용자 세션 목록
        
        Args:
            user_id: 사용자 ID
            include_expired: 만료 세션 포함 여부
            
        Returns:
            세션 목록
        """
        session_ids = self._user_sessions.get(user_id, [])
        sessions = []
        
        for session_id in session_ids:
            session = self._sessions.get(session_id)
            if session:
                if include_expired or not session.is_expired():
                    sessions.append(session)
        
        return sessions
    
    def close_session(
        self,
        session_id: str,
    ) -> bool:
        """
        세션 종료
        
        Args:
            session_id: 세션 ID
            
        Returns:
            종료 성공 여부
        """
        session = self._sessions.get(session_id)
        if session is None:
            return False
        
        session.status = SessionStatus.CLOSED
        return True
    
    def delete_session(
        self,
        session_id: str,
    ) -> bool:
        """
        세션 삭제
        
        Args:
            session_id: 세션 ID
            
        Returns:
            삭제 성공 여부
        """
        session = self._sessions.get(session_id)
        if session is None:
            return False
        
        # 사용자-세션 매핑 제거
        if session.user_id and session.user_id in self._user_sessions:
            if session_id in self._user_sessions[session.user_id]:
                self._user_sessions[session.user_id].remove(session_id)
        
        del self._sessions[session_id]
        return True
    
    def extend_session(
        self,
        session_id: str,
        additional_seconds: int,
    ) -> bool:
        """
        세션 연장
        
        Args:
            session_id: 세션 ID
            additional_seconds: 추가 시간 (초)
            
        Returns:
            연장 성공 여부
        """
        session = self._sessions.get(session_id)
        if session is None:
            return False
        
        if session.expires_at:
            session.expires_at += timedelta(seconds=additional_seconds)
        else:
            session.expires_at = datetime.now() + timedelta(seconds=additional_seconds)
        
        session.touch()
        return True
    
    def pause_session(
        self,
        session_id: str,
    ) -> bool:
        """
        세션 일시정지
        
        Args:
            session_id: 세션 ID
            
        Returns:
            성공 여부
        """
        session = self._sessions.get(session_id)
        if session is None:
            return False
        
        session.status = SessionStatus.PAUSED
        return True
    
    def resume_session(
        self,
        session_id: str,
    ) -> bool:
        """
        세션 재개
        
        Args:
            session_id: 세션 ID
            
        Returns:
            성공 여부
        """
        session = self._sessions.get(session_id)
        if session is None:
            return False
        
        if session.status == SessionStatus.PAUSED:
            session.status = SessionStatus.ACTIVE
            session.touch()
            return True
        return False
    
    def set_session_data(
        self,
        session_id: str,
        key: str,
        value: Any,
    ) -> bool:
        """
        세션 데이터 설정
        
        Args:
            session_id: 세션 ID
            key: 키
            value: 값
            
        Returns:
            성공 여부
        """
        session = self.get_session(session_id)
        if session is None:
            return False
        
        session.set(key, value)
        return True
    
    def get_session_data(
        self,
        session_id: str,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        세션 데이터 조회
        
        Args:
            session_id: 세션 ID
            key: 키
            default: 기본값
            
        Returns:
            값 또는 기본값
        """
        session = self.get_session(session_id)
        if session is None:
            return default
        
        return session.get(key, default)
    
    def cleanup_expired(self) -> int:
        """
        만료된 세션 정리
        
        Returns:
            정리된 세션 수
        """
        expired_ids = [
            id for id, session in self._sessions.items()
            if session.is_expired()
        ]
        
        for session_id in expired_ids:
            self.delete_session(session_id)
        
        self._last_cleanup = datetime.now()
        return len(expired_ids)
    
    def _auto_cleanup(self) -> None:
        """자동 정리"""
        elapsed = (datetime.now() - self._last_cleanup).total_seconds()
        if elapsed >= self.config.cleanup_interval:
            self.cleanup_expired()
    
    def list_sessions(
        self,
        status: Optional[SessionStatus] = None,
    ) -> List[Session]:
        """
        세션 목록
        
        Args:
            status: 필터링할 상태
            
        Returns:
            세션 목록
        """
        sessions = list(self._sessions.values())
        
        if status:
            sessions = [s for s in sessions if s.status == status]
        
        return sessions
    
    def count_sessions(
        self,
        status: Optional[SessionStatus] = None,
    ) -> int:
        """
        세션 수
        
        Args:
            status: 필터링할 상태
            
        Returns:
            세션 수
        """
        return len(self.list_sessions(status))
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 조회"""
        status_counts = {}
        for session in self._sessions.values():
            s = session.status.value
            status_counts[s] = status_counts.get(s, 0) + 1
        
        return {
            "total_sessions": len(self._sessions),
            "active_users": len(self._user_sessions),
            "by_status": status_counts,
            "max_sessions": self.config.max_sessions,
            "default_ttl": self.config.default_ttl,
        }


class ConversationMemory(BaseModel):
    """
    대화 기록 메모리
    
    대화 기록을 저장하고 관리합니다.
    """
    
    session_id: str
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    max_messages: int = 100
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    
    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        메시지 추가
        
        Args:
            role: 역할
            content: 내용
            metadata: 메타데이터
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self.messages.append(message)
        
        # 최대 개수 초과 시 오래된 메시지 제거
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def add_user_message(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """사용자 메시지 추가"""
        self.add_message("user", content, metadata)
    
    def add_assistant_message(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """어시스턴트 메시지 추가"""
        self.add_message("assistant", content, metadata)
    
    def add_system_message(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """시스템 메시지 추가"""
        self.add_message("system", content, metadata)
    
    def get_messages(
        self,
        last_n: Optional[int] = None,
        role: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        메시지 조회
        
        Args:
            last_n: 최근 N개
            role: 역할 필터
            
        Returns:
            메시지 목록
        """
        messages = self.messages
        
        if role:
            messages = [m for m in messages if m["role"] == role]
        
        if last_n:
            messages = messages[-last_n:]
        
        return messages
    
    def to_llm_messages(self) -> List[Message]:
        """LLM Message 형식으로 변환"""
        llm_messages = []
        for msg in self.messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                llm_messages.append(Message.system(content))
            elif role == "assistant":
                llm_messages.append(Message.assistant(content))
            else:
                llm_messages.append(Message.user(content))
        
        return llm_messages
    
    def clear(self) -> None:
        """메시지 클리어"""
        self.messages.clear()
    
    def get_summary(self) -> str:
        """대화 요약"""
        if not self.messages:
            return "No conversation history."
        
        return f"Conversation with {len(self.messages)} messages"
