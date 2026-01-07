"""
PROMETHEUS LLM Factory with Fallback Support

LLM 인스턴스 생성 및 Fallback 체인을 관리합니다.
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import os

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """LLM 프로바이더"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


@dataclass
class LLMConfig:
    """LLM 설정"""
    provider: LLMProvider
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: float = 60.0
    max_retries: int = 3


# =============================================================================
# 기본 모델 설정
# =============================================================================

DEFAULT_MODELS = {
    LLMProvider.OPENAI: "gpt-4o-mini",
    LLMProvider.ANTHROPIC: "claude-sonnet-4-20250514",
    LLMProvider.GOOGLE: "gemini-2.0-flash",
}

# Fallback 우선순위 (provider -> fallback list)
FALLBACK_PRIORITY = {
    LLMProvider.ANTHROPIC: [LLMProvider.OPENAI, LLMProvider.GOOGLE],
    LLMProvider.OPENAI: [LLMProvider.ANTHROPIC, LLMProvider.GOOGLE],
    LLMProvider.GOOGLE: [LLMProvider.ANTHROPIC, LLMProvider.OPENAI],
}


# =============================================================================
# LLM 인스턴스 캐시
# =============================================================================

_llm_cache: Dict[str, BaseChatModel] = {}


def _get_cache_key(provider: str, model: str, temperature: float) -> str:
    """캐시 키 생성"""
    return f"{provider}:{model}:{temperature}"


def clear_llm_cache():
    """LLM 캐시 초기화"""
    global _llm_cache
    _llm_cache.clear()
    logger.info("LLM 캐시가 초기화되었습니다.")


# =============================================================================
# LLM 생성 함수
# =============================================================================

def create_llm(
    provider: str,
    model: Optional[str] = None,
    temperature: float = 0.7,
    use_cache: bool = True,
    **kwargs,
) -> BaseChatModel:
    """
    LLM 인스턴스 생성
    
    Args:
        provider: openai, anthropic, google
        model: 모델명 (없으면 기본값)
        temperature: 온도
        use_cache: 캐시 사용 여부
        **kwargs: 추가 설정
    
    Returns:
        LangChain LLM 인스턴스
    """
    # Provider enum 변환
    if isinstance(provider, str):
        provider = LLMProvider(provider.lower())
    
    # 기본 모델 설정
    if model is None:
        model = DEFAULT_MODELS.get(provider)
    
    # 캐시 확인
    cache_key = _get_cache_key(provider.value, model, temperature)
    if use_cache and cache_key in _llm_cache:
        logger.debug(f"캐시에서 LLM 반환: {cache_key}")
        return _llm_cache[cache_key]
    
    # LLM 생성
    llm = _create_llm_instance(provider, model, temperature, **kwargs)
    
    # 캐시 저장
    if use_cache:
        _llm_cache[cache_key] = llm
    
    return llm


def _create_llm_instance(
    provider: LLMProvider,
    model: str,
    temperature: float,
    **kwargs,
) -> BaseChatModel:
    """LLM 인스턴스 실제 생성"""
    
    if provider == LLMProvider.OPENAI:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            **kwargs,
        )
    
    elif provider == LLMProvider.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model,
            temperature=temperature,
            **kwargs,
        )
    
    elif provider == LLMProvider.GOOGLE:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            **kwargs,
        )
    
    else:
        raise ValueError(f"Unknown provider: {provider}")


# =============================================================================
# Fallback LLM 생성
# =============================================================================

def create_llm_with_fallback(
    primary_provider: str,
    fallback_providers: Optional[List[str]] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    **kwargs,
) -> Runnable:
    """
    Fallback이 설정된 LLM 생성
    
    Args:
        primary_provider: 주 프로바이더
        fallback_providers: 대체 프로바이더 리스트 (없으면 기본 우선순위 사용)
        model: 모델명
        temperature: 온도
        **kwargs: 추가 설정
    
    Returns:
        Fallback이 설정된 Runnable LLM
    
    Example:
        ```python
        # Claude가 실패하면 GPT -> Gemini 순으로 시도
        llm = create_llm_with_fallback("anthropic")
        
        # 커스텀 fallback 순서
        llm = create_llm_with_fallback("openai", ["anthropic"])
        ```
    """
    # Provider enum 변환
    if isinstance(primary_provider, str):
        primary_provider = LLMProvider(primary_provider.lower())
    
    # Fallback 프로바이더 결정
    if fallback_providers is None:
        fallback_providers = FALLBACK_PRIORITY.get(primary_provider, [])
    else:
        fallback_providers = [
            LLMProvider(p.lower()) if isinstance(p, str) else p 
            for p in fallback_providers
        ]
    
    # Primary LLM 생성
    primary_llm = create_llm(primary_provider.value, model, temperature, **kwargs)
    
    # Fallback LLM 리스트 생성
    fallback_llms = []
    for fb_provider in fallback_providers:
        try:
            fb_llm = create_llm(fb_provider.value, None, temperature, **kwargs)
            fallback_llms.append(fb_llm)
            logger.debug(f"Fallback LLM 추가: {fb_provider.value}")
        except Exception as e:
            logger.warning(f"Fallback LLM 생성 실패 ({fb_provider.value}): {e}")
    
    # Fallback 체인 구성
    if fallback_llms:
        return primary_llm.with_fallbacks(fallback_llms)
    else:
        return primary_llm


def create_robust_llm(
    provider: str,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_retries: int = 3,
    with_fallback: bool = True,
    **kwargs,
) -> Runnable:
    """
    견고한 LLM 생성 (Fallback + Retry)
    
    Args:
        provider: 프로바이더
        model: 모델명
        temperature: 온도
        max_retries: 최대 재시도 횟수
        with_fallback: Fallback 사용 여부
        **kwargs: 추가 설정
    
    Returns:
        Fallback과 Retry가 설정된 견고한 LLM
    
    Example:
        ```python
        # 3번 재시도 + Fallback
        llm = create_robust_llm("anthropic", max_retries=3)
        ```
    """
    # 기본 LLM 또는 Fallback LLM 생성
    if with_fallback:
        llm = create_llm_with_fallback(provider, model=model, temperature=temperature, **kwargs)
    else:
        llm = create_llm(provider, model, temperature, **kwargs)
    
    # Retry 설정
    if max_retries > 1:
        llm = llm.with_retry(
            stop_after_attempt=max_retries,
            wait_exponential_jitter=True,
        )
    
    return llm


# =============================================================================
# Agent별 LLM 팩토리
# =============================================================================

@dataclass
class AgentLLMConfig:
    """Agent별 LLM 설정"""
    planner: LLMConfig = field(default_factory=lambda: LLMConfig(LLMProvider.ANTHROPIC))
    executor: LLMConfig = field(default_factory=lambda: LLMConfig(LLMProvider.OPENAI))
    writer: LLMConfig = field(default_factory=lambda: LLMConfig(LLMProvider.GOOGLE))
    qa: LLMConfig = field(default_factory=lambda: LLMConfig(LLMProvider.ANTHROPIC))
    meta: LLMConfig = field(default_factory=lambda: LLMConfig(LLMProvider.ANTHROPIC))


class LLMFactory:
    """
    Agent용 LLM 팩토리
    
    각 Agent에 적합한 LLM을 생성하고 관리합니다.
    Fallback과 Retry가 자동으로 설정됩니다.
    
    Example:
        ```python
        factory = LLMFactory()
        
        # Fallback이 설정된 Planner LLM
        planner_llm = factory.get_planner_llm()
        
        # 커스텀 설정
        factory.update_config("planner", provider="openai")
        ```
    """
    
    def __init__(
        self,
        config: Optional[AgentLLMConfig] = None,
        enable_fallback: bool = True,
        enable_retry: bool = True,
        max_retries: int = 3,
    ):
        """
        초기화
        
        Args:
            config: Agent별 LLM 설정
            enable_fallback: Fallback 활성화
            enable_retry: Retry 활성화
            max_retries: 최대 재시도 횟수
        """
        self.config = config or AgentLLMConfig()
        self.enable_fallback = enable_fallback
        self.enable_retry = enable_retry
        self.max_retries = max_retries
        
        # LLM 인스턴스 캐시
        self._instances: Dict[str, Runnable] = {}
    
    def _create_agent_llm(self, agent_config: LLMConfig) -> Runnable:
        """Agent용 LLM 생성"""
        return create_robust_llm(
            provider=agent_config.provider.value,
            model=agent_config.model,
            temperature=agent_config.temperature,
            max_retries=self.max_retries if self.enable_retry else 1,
            with_fallback=self.enable_fallback,
        )
    
    def get_planner_llm(self) -> Runnable:
        """Planner용 LLM 반환"""
        if "planner" not in self._instances:
            self._instances["planner"] = self._create_agent_llm(self.config.planner)
            logger.info(f"Planner LLM 생성: {self.config.planner.provider.value}")
        return self._instances["planner"]
    
    def get_executor_llm(self) -> Runnable:
        """Executor용 LLM 반환"""
        if "executor" not in self._instances:
            self._instances["executor"] = self._create_agent_llm(self.config.executor)
            logger.info(f"Executor LLM 생성: {self.config.executor.provider.value}")
        return self._instances["executor"]
    
    def get_writer_llm(self) -> Runnable:
        """Writer용 LLM 반환"""
        if "writer" not in self._instances:
            self._instances["writer"] = self._create_agent_llm(self.config.writer)
            logger.info(f"Writer LLM 생성: {self.config.writer.provider.value}")
        return self._instances["writer"]
    
    def get_qa_llm(self) -> Runnable:
        """QA용 LLM 반환"""
        if "qa" not in self._instances:
            self._instances["qa"] = self._create_agent_llm(self.config.qa)
            logger.info(f"QA LLM 생성: {self.config.qa.provider.value}")
        return self._instances["qa"]
    
    def get_meta_llm(self) -> Runnable:
        """Meta Agent용 LLM 반환"""
        if "meta" not in self._instances:
            self._instances["meta"] = self._create_agent_llm(self.config.meta)
            logger.info(f"Meta LLM 생성: {self.config.meta.provider.value}")
        return self._instances["meta"]
    
    def get_llm(self, agent_name: str, provider: Optional[str] = None) -> Runnable:
        """
        Agent 이름으로 LLM 반환
        
        Args:
            agent_name: planner, executor, writer, qa, meta
            provider: 프로바이더 오버라이드 (선택)
        
        Returns:
            LLM 인스턴스
        """
        if provider:
            # 동적 프로바이더 사용
            return create_robust_llm(
                provider=provider,
                max_retries=self.max_retries if self.enable_retry else 1,
                with_fallback=self.enable_fallback,
            )
        
        agent_methods = {
            "planner": self.get_planner_llm,
            "executor": self.get_executor_llm,
            "writer": self.get_writer_llm,
            "qa": self.get_qa_llm,
            "meta": self.get_meta_llm,
        }
        
        if agent_name not in agent_methods:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        return agent_methods[agent_name]()
    
    def update_config(self, agent_name: str, **kwargs):
        """
        Agent 설정 업데이트
        
        Args:
            agent_name: planner, executor, writer, qa, meta
            **kwargs: provider, model, temperature 등
        """
        config_map = {
            "planner": self.config.planner,
            "executor": self.config.executor,
            "writer": self.config.writer,
            "qa": self.config.qa,
            "meta": self.config.meta,
        }
        
        if agent_name not in config_map:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        agent_config = config_map[agent_name]
        
        for key, value in kwargs.items():
            if key == "provider" and isinstance(value, str):
                value = LLMProvider(value.lower())
            if hasattr(agent_config, key):
                setattr(agent_config, key, value)
        
        # 캐시 무효화
        if agent_name in self._instances:
            del self._instances[agent_name]
            logger.info(f"{agent_name} LLM 설정 업데이트됨")
    
    def clear_cache(self):
        """인스턴스 캐시 초기화"""
        self._instances.clear()
        logger.info("LLM Factory 캐시가 초기화되었습니다.")


# =============================================================================
# 전역 팩토리 인스턴스
# =============================================================================

_global_factory: Optional[LLMFactory] = None


def get_llm_factory() -> LLMFactory:
    """전역 LLM Factory 반환"""
    global _global_factory
    if _global_factory is None:
        _global_factory = LLMFactory()
    return _global_factory


def set_llm_factory(factory: LLMFactory):
    """전역 LLM Factory 설정"""
    global _global_factory
    _global_factory = factory


# =============================================================================
# 편의 함수 (하위 호환성)
# =============================================================================

def get_llm(provider: str, model: str = None, temperature: float = 0.7) -> BaseChatModel:
    """
    LLM 인스턴스 생성 (하위 호환성)
    
    Args:
        provider: openai, anthropic, google
        model: 모델명
        temperature: 온도
    
    Returns:
        LangChain LLM 인스턴스
    """
    return create_llm(provider, model, temperature)
