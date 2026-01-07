"""
AnthropicClient - Anthropic Claude 클라이언트

이 파일의 책임:
- Anthropic API 호출
- Claude 모델 관리
- Anthropic 형식 메시지 변환
- Tool Use 지원
- 토큰 카운팅
"""

from typing import Any, AsyncIterator, Dict, List, Optional, Tuple
import os

from prometheus.llm.base import (
    BaseLLMClient,
    LLMConfig,
    LLMResponse,
    LLMError,
    RateLimitError,
    AuthenticationError,
    Message,
    MessageRole,
    TokenUsage,
)


class AnthropicConfig(LLMConfig):
    """Anthropic 전용 설정"""
    
    model: str = "claude-3-opus-20240229"
    max_tokens: int = 4096
    base_url: Optional[str] = None


class AnthropicClient(BaseLLMClient):
    """
    Anthropic Claude 클라이언트
    
    Anthropic의 Claude 모델들을 사용하기 위한 클라이언트입니다.
    Tool Use 및 스트리밍을 지원합니다.
    """
    
    provider: str = "anthropic"
    
    # Claude 모델별 컨텍스트 윈도우
    MODEL_CONTEXT_WINDOWS = {
        "claude-3-opus": 200000,
        "claude-3-sonnet": 200000,
        "claude-3-haiku": 200000,
        "claude-2.1": 100000,
        "claude-2.0": 100000,
        "claude-instant": 100000,
    }
    
    def __init__(
        self,
        config: Optional[AnthropicConfig] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """
        AnthropicClient 초기화
        
        Args:
            config: Anthropic 설정
            api_key: API 키 (None이면 환경변수에서 로드)
        """
        super().__init__(config=config or AnthropicConfig(), api_key=api_key)
        
        # API 키 설정
        if self.api_key is None:
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        
        self._client = None
        self._async_client = None
    
    def _get_client(self):
        """동기 클라이언트 획득 (lazy initialization)"""
        if self._client is None:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(
                    api_key=self.api_key,
                    base_url=getattr(self.config, 'base_url', None),
                )
                self._is_connected = True
            except Exception as e:
                raise LLMError(f"Failed to initialize Anthropic client: {e}", self.provider, e)
        return self._client
    
    def _get_async_client(self):
        """비동기 클라이언트 획득 (lazy initialization)"""
        if self._async_client is None:
            try:
                from anthropic import AsyncAnthropic
                self._async_client = AsyncAnthropic(
                    api_key=self.api_key,
                    base_url=getattr(self.config, 'base_url', None),
                )
                self._is_connected = True
            except Exception as e:
                raise LLMError(f"Failed to initialize AsyncAnthropic client: {e}", self.provider, e)
        return self._async_client
    
    async def generate(
        self,
        messages: List[Message],
        **kwargs: Any,
    ) -> LLMResponse:
        """
        텍스트 생성
        
        Args:
            messages: 대화 메시지 목록
            **kwargs: 추가 옵션
            
        Returns:
            LLM 응답
        """
        client = self._get_async_client()
        system_prompt, formatted_messages = self._format_messages(messages)
        
        # 파라미터 준비
        params = {
            "model": kwargs.get("model", self.config.model),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "messages": formatted_messages,
        }
        
        # temperature 설정
        if "temperature" in kwargs:
            params["temperature"] = kwargs["temperature"]
        elif self.config.temperature != 0.7:  # 기본값이 아닌 경우만
            params["temperature"] = self.config.temperature
        
        # system prompt 설정
        if system_prompt:
            params["system"] = system_prompt
        
        # tools 처리
        tools = kwargs.get("tools")
        if tools:
            params["tools"] = self._format_tools(tools)
        
        try:
            response = await client.messages.create(**params)
            return self._parse_response(response)
            
        except Exception as e:
            error_str = str(e).lower()
            if "rate limit" in error_str:
                raise RateLimitError(f"Anthropic rate limit exceeded: {e}", self.provider, e)
            elif "authentication" in error_str or "api key" in error_str:
                raise AuthenticationError(f"Anthropic authentication failed: {e}", self.provider, e)
            else:
                raise LLMError(f"Anthropic API error: {e}", self.provider, e)
    
    async def stream(
        self,
        messages: List[Message],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        스트리밍 생성
        
        Args:
            messages: 대화 메시지 목록
            **kwargs: 추가 옵션
            
        Yields:
            스트리밍 응답 청크
        """
        client = self._get_async_client()
        system_prompt, formatted_messages = self._format_messages(messages)
        
        params = {
            "model": kwargs.get("model", self.config.model),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "messages": formatted_messages,
        }
        
        if system_prompt:
            params["system"] = system_prompt
        
        try:
            async with client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            raise LLMError(f"Anthropic streaming error: {e}", self.provider, e)
    
    def count_tokens(
        self,
        text: str,
    ) -> int:
        """
        토큰 수 계산 (근사치)
        
        Anthropic은 공식 토크나이저를 제공하지 않으므로 근사치 사용
        
        Args:
            text: 텍스트
            
        Returns:
            토큰 수 (근사치)
        """
        # Claude는 대략 4자당 1토큰 (영어 기준)
        # 한글은 대략 2자당 1토큰
        # 여기서는 보수적으로 3자당 1토큰으로 계산
        return len(text) // 3 + 1
    
    async def generate_with_tools(
        self,
        messages: List[Message],
        tools: List[Dict[str, Any]],
        tool_choice: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Tool Use를 사용한 생성
        
        Args:
            messages: 대화 메시지 목록
            tools: Tool 정의 목록
            tool_choice: Tool 선택 옵션
            **kwargs: 추가 옵션
            
        Returns:
            LLM 응답 (tool_use 포함 가능)
        """
        if tool_choice:
            kwargs["tool_choice"] = tool_choice
        return await self.generate(messages, tools=tools, **kwargs)
    
    def _format_messages(
        self,
        messages: List[Message],
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """
        Anthropic 형식으로 메시지 변환
        
        Anthropic은 system 메시지를 별도 파라미터로 받음
        
        Args:
            messages: 표준 메시지 목록
            
        Returns:
            (system_prompt, messages) 튜플
        """
        system_prompt = None
        formatted = []
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                # system 메시지는 별도로 추출
                system_prompt = msg.content
            elif msg.role == MessageRole.TOOL:
                # Tool 결과는 user 역할로 변환
                formatted.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": msg.content,
                        }
                    ]
                })
            else:
                # user, assistant
                role = "user" if msg.role == MessageRole.USER else "assistant"
                
                # tool_calls가 있는 경우 (assistant)
                if msg.tool_calls:
                    content = []
                    if msg.content:
                        content.append({"type": "text", "text": msg.content})
                    for tc in msg.tool_calls:
                        content.append({
                            "type": "tool_use",
                            "id": tc.get("id"),
                            "name": tc.get("function", {}).get("name"),
                            "input": tc.get("function", {}).get("arguments", {}),
                        })
                    formatted.append({"role": role, "content": content})
                else:
                    formatted.append({
                        "role": role,
                        "content": msg.content,
                    })
        
        return system_prompt, formatted
    
    def _format_tools(
        self,
        tools: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Anthropic Tool 형식으로 변환
        
        Args:
            tools: Tool 정의 목록
            
        Returns:
            Anthropic Tool 형식 목록
        """
        formatted = []
        for tool in tools:
            if "input_schema" in tool:
                # 이미 Anthropic 형식
                formatted.append(tool)
            elif "function" in tool:
                # OpenAI 형식에서 변환
                func = tool["function"]
                formatted.append({
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
                })
            else:
                # 표준 형식에서 변환
                formatted.append({
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("parameters", {"type": "object", "properties": {}}),
                })
        return formatted
    
    def _parse_response(
        self,
        response: Any,
    ) -> LLMResponse:
        """
        Anthropic 응답 파싱
        
        Args:
            response: Anthropic API 응답
            
        Returns:
            표준 LLM 응답
        """
        # 컨텐츠 추출
        content = ""
        tool_calls = None
        
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                if tool_calls is None:
                    tool_calls = []
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": block.input if isinstance(block.input, str) else str(block.input),
                    }
                })
        
        # 토큰 사용량
        usage = TokenUsage(
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
        )
        self._update_usage(usage)
        
        return LLMResponse(
            content=content,
            role=MessageRole.ASSISTANT,
            model=response.model,
            usage=usage,
            finish_reason=response.stop_reason,
            tool_calls=tool_calls,
            metadata={
                "id": response.id,
            }
        )
