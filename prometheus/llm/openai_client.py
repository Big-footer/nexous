"""
OpenAIClient - OpenAI GPT 클라이언트

이 파일의 책임:
- OpenAI API 호출
- GPT 모델 관리
- OpenAI 형식 메시지 변환
- Function Calling 지원
- 토큰 카운팅 (tiktoken)
"""

from typing import Any, AsyncIterator, Dict, List, Optional
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


class OpenAIConfig(LLMConfig):
    """OpenAI 전용 설정"""
    
    model: str = "gpt-4-turbo-preview"
    organization: Optional[str] = None
    base_url: Optional[str] = None


class OpenAIClient(BaseLLMClient):
    """
    OpenAI GPT 클라이언트
    
    OpenAI의 GPT 모델들을 사용하기 위한 클라이언트입니다.
    Function Calling 및 스트리밍을 지원합니다.
    """
    
    provider: str = "openai"
    
    def __init__(
        self,
        config: Optional[OpenAIConfig] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """
        OpenAIClient 초기화
        
        Args:
            config: OpenAI 설정
            api_key: API 키 (None이면 환경변수에서 로드)
        """
        super().__init__(config=config or OpenAIConfig(), api_key=api_key)
        
        # API 키 설정
        if self.api_key is None:
            self.api_key = os.environ.get("OPENAI_API_KEY")
        
        self._client = None
        self._async_client = None
        self._tokenizer = None
    
    def _get_client(self):
        """동기 클라이언트 획득 (lazy initialization)"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    organization=getattr(self.config, 'organization', None),
                    base_url=getattr(self.config, 'base_url', None),
                )
                self._is_connected = True
            except Exception as e:
                raise LLMError(f"Failed to initialize OpenAI client: {e}", self.provider, e)
        return self._client
    
    def _get_async_client(self):
        """비동기 클라이언트 획득 (lazy initialization)"""
        if self._async_client is None:
            try:
                from openai import AsyncOpenAI
                self._async_client = AsyncOpenAI(
                    api_key=self.api_key,
                    organization=getattr(self.config, 'organization', None),
                    base_url=getattr(self.config, 'base_url', None),
                )
                self._is_connected = True
            except Exception as e:
                raise LLMError(f"Failed to initialize AsyncOpenAI client: {e}", self.provider, e)
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
        formatted_messages = self._format_messages(messages)
        params = self._merge_config(**kwargs)
        
        # tools 처리
        tools = kwargs.get("tools")
        if tools:
            params["tools"] = self._format_tools(tools)
        
        try:
            response = await client.chat.completions.create(
                messages=formatted_messages,
                **params
            )
            return self._parse_response(response)
            
        except Exception as e:
            error_str = str(e).lower()
            if "rate limit" in error_str:
                raise RateLimitError(f"OpenAI rate limit exceeded: {e}", self.provider, e)
            elif "authentication" in error_str or "api key" in error_str:
                raise AuthenticationError(f"OpenAI authentication failed: {e}", self.provider, e)
            else:
                raise LLMError(f"OpenAI API error: {e}", self.provider, e)
    
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
        formatted_messages = self._format_messages(messages)
        params = self._merge_config(**kwargs)
        params["stream"] = True
        
        try:
            response = await client.chat.completions.create(
                messages=formatted_messages,
                **params
            )
            
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            raise LLMError(f"OpenAI streaming error: {e}", self.provider, e)
    
    def count_tokens(
        self,
        text: str,
    ) -> int:
        """
        토큰 수 계산 (tiktoken 사용)
        
        Args:
            text: 텍스트
            
        Returns:
            토큰 수
        """
        if self._tokenizer is None:
            try:
                import tiktoken
                # 모델에 맞는 인코딩 선택
                model = self.config.model
                try:
                    self._tokenizer = tiktoken.encoding_for_model(model)
                except KeyError:
                    # 모델을 찾을 수 없으면 기본 인코딩 사용
                    self._tokenizer = tiktoken.get_encoding("cl100k_base")
            except ImportError:
                # tiktoken이 없으면 대략적인 추정
                return len(text) // 4
        
        return len(self._tokenizer.encode(text))
    
    def count_messages_tokens(
        self,
        messages: List[Message],
    ) -> int:
        """
        메시지 목록의 토큰 수 계산
        
        Args:
            messages: 메시지 목록
            
        Returns:
            총 토큰 수
        """
        total = 0
        for msg in messages:
            # 메시지 오버헤드 (role 등)
            total += 4
            total += self.count_tokens(msg.content)
            if msg.name:
                total += self.count_tokens(msg.name) + 1
        total += 2  # 프라임 토큰
        return total
    
    async def generate_with_tools(
        self,
        messages: List[Message],
        tools: List[Dict[str, Any]],
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Function Calling을 사용한 생성
        
        Args:
            messages: 대화 메시지 목록
            tools: Tool/Function 정의 목록
            tool_choice: Tool 선택 옵션 ("auto", "none", 또는 특정 함수명)
            **kwargs: 추가 옵션
            
        Returns:
            LLM 응답 (tool_calls 포함 가능)
        """
        if tool_choice:
            kwargs["tool_choice"] = tool_choice
        return await self.generate(messages, tools=tools, **kwargs)
    
    async def create_embedding(
        self,
        text: str,
        model: str = "text-embedding-3-small",
    ) -> List[float]:
        """
        텍스트 임베딩 생성
        
        Args:
            text: 임베딩할 텍스트
            model: 임베딩 모델
            
        Returns:
            임베딩 벡터
        """
        client = self._get_async_client()
        
        try:
            response = await client.embeddings.create(
                input=text,
                model=model,
            )
            return response.data[0].embedding
            
        except Exception as e:
            raise LLMError(f"OpenAI embedding error: {e}", self.provider, e)
    
    def _format_messages(
        self,
        messages: List[Message],
    ) -> List[Dict[str, Any]]:
        """
        OpenAI 형식으로 메시지 변환
        
        Args:
            messages: 표준 메시지 목록
            
        Returns:
            OpenAI 형식 메시지 목록
        """
        formatted = []
        for msg in messages:
            item = {
                "role": msg.role.value,
                "content": msg.content,
            }
            if msg.name:
                item["name"] = msg.name
            if msg.tool_calls:
                item["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                item["tool_call_id"] = msg.tool_call_id
            formatted.append(item)
        return formatted
    
    def _format_tools(
        self,
        tools: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        OpenAI Function 형식으로 변환
        
        Args:
            tools: Tool 정의 목록
            
        Returns:
            OpenAI Function 형식 목록
        """
        formatted = []
        for tool in tools:
            if "function" in tool:
                # 이미 OpenAI 형식
                formatted.append(tool)
            else:
                # 표준 형식에서 변환
                formatted.append({
                    "type": "function",
                    "function": {
                        "name": tool.get("name", ""),
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
                    }
                })
        return formatted
    
    def _parse_response(
        self,
        response: Any,
    ) -> LLMResponse:
        """
        OpenAI 응답 파싱
        
        Args:
            response: OpenAI API 응답
            
        Returns:
            표준 LLM 응답
        """
        choice = response.choices[0]
        message = choice.message
        
        # Tool calls 파싱
        tool_calls = None
        if hasattr(message, 'tool_calls') and message.tool_calls:
            tool_calls = []
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                })
        
        # 토큰 사용량
        usage = TokenUsage()
        if response.usage:
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )
            self._update_usage(usage)
        
        return LLMResponse(
            content=message.content or "",
            role=MessageRole.ASSISTANT,
            model=response.model,
            usage=usage,
            finish_reason=choice.finish_reason,
            tool_calls=tool_calls,
            metadata={
                "id": response.id,
                "created": response.created,
            }
        )
