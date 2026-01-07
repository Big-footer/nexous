"""
PROMETHEUS LLM 모듈

LLM 인스턴스 생성, Fallback 체인, 응답 캐싱을 관리합니다.
"""

from prometheus.llm.factory import (
    # Enums & Config
    LLMProvider,
    LLMConfig,
    AgentLLMConfig,
    
    # Factory
    LLMFactory,
    get_llm_factory,
    set_llm_factory,
    
    # Functions
    create_llm,
    create_llm_with_fallback,
    create_robust_llm,
    get_llm,
    clear_llm_cache,
    
    # Constants
    DEFAULT_MODELS,
    FALLBACK_PRIORITY,
)

from prometheus.llm.cache import (
    # Cache Classes
    LLMResponseCache,
    CacheEntry,
    CacheStats,
    
    # Global Cache
    get_response_cache,
    set_response_cache,
    clear_response_cache,
    
    # LangChain Integration
    setup_langchain_cache,
    disable_langchain_cache,
)

from prometheus.llm.streaming import (
    # Event Types
    StreamEventType,
    StreamEvent,
    
    # Handler
    StreamingHandler,
    create_console_handler,
    
    # Utilities
    stream_to_string,
    astream_to_string,
    stream_workflow,
)

from prometheus.llm.parallel import (
    # Classes
    ParallelExecutor,
    ParallelResult,
    ParallelExecutionSummary,
    
    # Functions
    run_agents_parallel,
    run_tools_parallel,
    batch_invoke_async,
    batch_invoke_sync,
)

# Legacy 클래스 (하위 호환성)
from prometheus.llm.base import (
    BaseLLMClient,
    LLMResponse,
    Message,
    MessageRole,
    TokenUsage,
    LLMError,
)

# Legacy LLM Clients
from prometheus.llm.openai_client import OpenAIClient, OpenAIConfig
from prometheus.llm.anthropic_client import AnthropicClient, AnthropicConfig
from prometheus.llm.gemini_client import GeminiClient, GeminiConfig

__all__ = [
    # Enums & Config
    "LLMProvider",
    "LLMConfig",
    "AgentLLMConfig",
    
    # Factory
    "LLMFactory",
    "get_llm_factory",
    "set_llm_factory",
    
    # Functions
    "create_llm",
    "create_llm_with_fallback",
    "create_robust_llm",
    "get_llm",
    "clear_llm_cache",
    
    # Constants
    "DEFAULT_MODELS",
    "FALLBACK_PRIORITY",
    
    # Cache
    "LLMResponseCache",
    "CacheEntry",
    "CacheStats",
    "get_response_cache",
    "set_response_cache",
    "clear_response_cache",
    "setup_langchain_cache",
    "disable_langchain_cache",
    
    # Streaming
    "StreamEventType",
    "StreamEvent",
    "StreamingHandler",
    "create_console_handler",
    "stream_to_string",
    "astream_to_string",
    "stream_workflow",
    
    # Parallel Execution
    "ParallelExecutor",
    "ParallelResult",
    "ParallelExecutionSummary",
    "run_agents_parallel",
    "run_tools_parallel",
    "batch_invoke_async",
    "batch_invoke_sync",
    
    # Legacy (하위 호환성)
    "BaseLLMClient",
    "LLMResponse",
    "Message",
    "MessageRole",
    "TokenUsage",
    "LLMError",
    "OpenAIClient",
    "AnthropicClient",
    "GeminiClient",
    "OpenAIConfig",
    "AnthropicConfig",
    "GeminiConfig",
]


# Legacy 함수 (하위 호환성)
def create_llm_client(provider: str, **kwargs):
    """
    레거시 LLM 클라이언트 생성 함수 (Deprecated)
    
    새 코드에서는 create_llm() 또는 LLMFactory를 사용하세요.
    """
    import warnings
    warnings.warn(
        "create_llm_client is deprecated. Use create_llm() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    provider = provider.lower()
    if provider == "openai":
        config = OpenAIConfig(**kwargs)
        return OpenAIClient(config)
    elif provider == "anthropic":
        config = AnthropicConfig(**kwargs)
        return AnthropicClient(config)
    elif provider in ("google", "gemini"):
        config = GeminiConfig(**kwargs)
        return GeminiClient(config)
    else:
        raise ValueError(f"Unknown provider: {provider}")
