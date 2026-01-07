"""
GeminiClient - Google Gemini 클라이언트

이 파일의 책임:
- Google Generative AI API 호출
- Gemini 모델 관리
- Gemini 형식 메시지 변환
- Function Calling 지원
- 토큰 카운팅
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


class GeminiConfig(LLMConfig):
    """Gemini 전용 설정"""
    
    model: str = "gemini-1.5-pro"
    max_tokens: int = 8192
    safety_settings: Optional[List[Dict[str, Any]]] = None
    generation_config: Optional[Dict[str, Any]] = None


class GeminiClient(BaseLLMClient):
    """
    Google Gemini 클라이언트
    
    Google의 Gemini 모델들을 사용하기 위한 클라이언트입니다.
    Function Calling 및 스트리밍을 지원합니다.
    """
    
    provider: str = "gemini"
    
    def __init__(
        self,
        config: Optional[GeminiConfig] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """
        GeminiClient 초기화
        
        Args:
            config: Gemini 설정
            api_key: API 키 (None이면 환경변수에서 로드)
        """
        super().__init__(config=config or GeminiConfig(), api_key=api_key)
        
        # API 키 설정
        if self.api_key is None:
            self.api_key = os.environ.get("GOOGLE_API_KEY")
        
        self._model = None
        self._genai = None
    
    def _get_genai(self):
        """genai 모듈 획득 및 설정"""
        if self._genai is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._genai = genai
                self._is_connected = True
            except Exception as e:
                raise LLMError(f"Failed to initialize Gemini: {e}", self.provider, e)
        return self._genai
    
    def _get_model(self, model_name: Optional[str] = None):
        """모델 인스턴스 획득"""
        genai = self._get_genai()
        name = model_name or self.config.model
        
        # 모델 설정
        generation_config = {
            "temperature": self.config.temperature,
            "max_output_tokens": self.config.max_tokens,
            "top_p": self.config.top_p,
        }
        
        # 커스텀 generation_config 병합
        if hasattr(self.config, 'generation_config') and self.config.generation_config:
            generation_config.update(self.config.generation_config)
        
        return genai.GenerativeModel(
            model_name=name,
            generation_config=generation_config,
            safety_settings=getattr(self.config, 'safety_settings', None),
        )
    
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
        model = self._get_model(kwargs.get("model"))
        history, last_message = self._format_messages(messages)
        
        try:
            # 대화 세션 생성
            chat = model.start_chat(history=history)
            
            # tools 처리
            tools = kwargs.get("tools")
            if tools:
                formatted_tools = self._format_tools(tools)
                response = await chat.send_message_async(
                    last_message,
                    tools=formatted_tools,
                )
            else:
                response = await chat.send_message_async(last_message)
            
            return self._parse_response(response)
            
        except Exception as e:
            error_str = str(e).lower()
            if "quota" in error_str or "rate" in error_str:
                raise RateLimitError(f"Gemini rate limit exceeded: {e}", self.provider, e)
            elif "api key" in error_str or "authentication" in error_str:
                raise AuthenticationError(f"Gemini authentication failed: {e}", self.provider, e)
            else:
                raise LLMError(f"Gemini API error: {e}", self.provider, e)
    
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
        model = self._get_model(kwargs.get("model"))
        history, last_message = self._format_messages(messages)
        
        try:
            chat = model.start_chat(history=history)
            response = await chat.send_message_async(
                last_message,
                stream=True,
            )
            
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            raise LLMError(f"Gemini streaming error: {e}", self.provider, e)
    
    def count_tokens(
        self,
        text: str,
    ) -> int:
        """
        토큰 수 계산
        
        Args:
            text: 텍스트
            
        Returns:
            토큰 수
        """
        try:
            model = self._get_model()
            result = model.count_tokens(text)
            return result.total_tokens
        except Exception:
            # 실패 시 근사치 반환
            return len(text) // 4
    
    async def generate_with_tools(
        self,
        messages: List[Message],
        tools: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Function Calling을 사용한 생성
        
        Args:
            messages: 대화 메시지 목록
            tools: Tool 정의 목록
            **kwargs: 추가 옵션
            
        Returns:
            LLM 응답 (function_call 포함 가능)
        """
        return await self.generate(messages, tools=tools, **kwargs)
    
    async def generate_multimodal(
        self,
        messages: List[Message],
        images: Optional[List[bytes]] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        멀티모달 생성 (이미지 + 텍스트)
        
        Args:
            messages: 대화 메시지 목록
            images: 이미지 데이터 목록
            **kwargs: 추가 옵션
            
        Returns:
            LLM 응답
        """
        genai = self._get_genai()
        model = self._get_model(kwargs.get("model", "gemini-1.5-pro"))
        
        # 컨텐츠 구성
        contents = []
        
        # 텍스트 메시지 추가
        for msg in messages:
            if msg.role in [MessageRole.USER, MessageRole.SYSTEM]:
                contents.append(msg.content)
        
        # 이미지 추가
        if images:
            from PIL import Image
            import io
            for img_data in images:
                img = Image.open(io.BytesIO(img_data))
                contents.append(img)
        
        try:
            response = await model.generate_content_async(contents)
            return self._parse_response(response)
            
        except Exception as e:
            raise LLMError(f"Gemini multimodal error: {e}", self.provider, e)
    
    def _format_messages(
        self,
        messages: List[Message],
    ) -> tuple[List[Dict[str, Any]], str]:
        """
        Gemini 형식으로 메시지 변환
        
        Args:
            messages: 표준 메시지 목록
            
        Returns:
            (history, last_message) 튜플
        """
        history = []
        last_message = ""
        
        # system 메시지를 첫 user 메시지에 포함
        system_content = ""
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_content = msg.content
                break
        
        for i, msg in enumerate(messages):
            if msg.role == MessageRole.SYSTEM:
                continue
            
            content = msg.content
            
            # 첫 user 메시지에 system 추가
            if msg.role == MessageRole.USER and system_content and i == 0:
                content = f"{system_content}\n\n{content}"
                system_content = ""
            
            # 마지막 메시지는 별도 처리
            if i == len(messages) - 1 and msg.role == MessageRole.USER:
                last_message = content
            else:
                role = "user" if msg.role == MessageRole.USER else "model"
                history.append({
                    "role": role,
                    "parts": [content],
                })
        
        return history, last_message
    
    def _format_tools(
        self,
        tools: List[Dict[str, Any]],
    ) -> List[Any]:
        """
        Gemini Function 형식으로 변환
        
        Args:
            tools: Tool 정의 목록
            
        Returns:
            Gemini Tool 형식 목록
        """
        genai = self._get_genai()
        
        function_declarations = []
        for tool in tools:
            if "function" in tool:
                func = tool["function"]
                function_declarations.append({
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "parameters": func.get("parameters", {}),
                })
            else:
                function_declarations.append({
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {}),
                })
        
        return [genai.protos.Tool(function_declarations=function_declarations)]
    
    def _parse_response(
        self,
        response: Any,
    ) -> LLMResponse:
        """
        Gemini 응답 파싱
        
        Args:
            response: Gemini API 응답
            
        Returns:
            표준 LLM 응답
        """
        # 텍스트 추출
        content = ""
        tool_calls = None
        
        try:
            # 단일 candidate 처리
            candidate = response.candidates[0] if response.candidates else None
            
            if candidate and candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, 'text') and part.text:
                        content += part.text
                    elif hasattr(part, 'function_call'):
                        if tool_calls is None:
                            tool_calls = []
                        fc = part.function_call
                        tool_calls.append({
                            "id": f"call_{len(tool_calls)}",
                            "type": "function",
                            "function": {
                                "name": fc.name,
                                "arguments": dict(fc.args) if fc.args else {},
                            }
                        })
        except Exception:
            # 간단한 응답 형식
            if hasattr(response, 'text'):
                content = response.text
        
        # 토큰 사용량 (Gemini는 usage_metadata 제공)
        usage = TokenUsage()
        if hasattr(response, 'usage_metadata'):
            um = response.usage_metadata
            usage = TokenUsage(
                prompt_tokens=getattr(um, 'prompt_token_count', 0),
                completion_tokens=getattr(um, 'candidates_token_count', 0),
                total_tokens=getattr(um, 'total_token_count', 0),
            )
            self._update_usage(usage)
        
        # finish_reason
        finish_reason = None
        try:
            if response.candidates:
                finish_reason = str(response.candidates[0].finish_reason)
        except Exception:
            pass
        
        return LLMResponse(
            content=content,
            role=MessageRole.ASSISTANT,
            model=self.config.model,
            usage=usage,
            finish_reason=finish_reason,
            tool_calls=tool_calls,
            metadata={}
        )
    
    def _configure_safety_settings(self) -> List[Dict[str, Any]]:
        """
        기본 안전 설정 구성
        
        Returns:
            안전 설정 목록
        """
        genai = self._get_genai()
        
        return [
            {
                "category": genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                "threshold": genai.types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            },
            {
                "category": genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                "threshold": genai.types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            },
            {
                "category": genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                "threshold": genai.types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            },
            {
                "category": genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                "threshold": genai.types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            },
        ]
