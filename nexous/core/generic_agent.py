"""
NEXOUS Core - Generic Agent

LLM + Tool을 호출하는 Agent 구현

LEVEL 2:
- LLMRouter를 통한 정책 기반 LLM 호출
- primary/retry/fallback 지원
- JSON 출력 + Schema 검증
- Agent만 Router를 호출 (Runner는 LLM 모름)
"""

from __future__ import annotations

import json
import logging
import re
from typing import Dict, Any, List, Callable, Optional

from .base_agent import BaseAgent
from ..llm import (
    LLMMessage,
    LLMResponse,
    LLMPolicy,
    LLMRouter,
    LLMClientError,
    LLMAllProvidersFailedError,
)
from ..tools import (
    ToolResult,
    ToolError,
    get_registry,
    ALLOWED_TOOLS,
)

logger = logging.getLogger(__name__)


class OutputValidationError(Exception):
    """출력 스키마 검증 오류"""
    pass


class GenericAgent(BaseAgent):
    """
    LLM + Tool을 호출하는 범용 Agent
    
    LEVEL 2:
    - LLMPolicy에 따른 Router 사용
    - primary/retry/fallback 자동 처리
    - JSON 출력 검증
    """
    
    def __init__(
        self,
        agent_id: str,
        role: str,
        purpose: str,
        llm_config: Dict[str, Any] = None,
        tools: List[str] = None,
        system_prompt: str = "",
        output_policy: Dict[str, Any] = None,
        config: Dict[str, Any] = None,
        trace_callback: Callable = None,
    ):
        super().__init__(
            agent_id=agent_id,
            role=role,
            purpose=purpose,
            llm_config=llm_config,
            tools=tools,
            system_prompt=system_prompt,
            output_policy=output_policy,
            config=config,
        )
        
        self.trace_callback = trace_callback
        self._tool_registry = get_registry()
        self._available_tools = self._resolve_tools(tools or [])
        
        # LLM Policy 생성
        self._llm_policy = self._create_llm_policy()
    
    def _create_llm_policy(self) -> LLMPolicy:
        """LLM 설정에서 Policy 생성"""
        llm_config = self.llm_config or {}
        
        # policy가 별도로 정의된 경우
        if "policy" in llm_config:
            return LLMPolicy.from_dict(llm_config["policy"])
        
        # 기존 방식 호환 (provider/model)
        provider = llm_config.get("provider", "openai")
        model = llm_config.get("model", "gpt-4o")
        primary = f"{provider}/{model}"
        
        return LLMPolicy(
            primary=primary,
            retry=llm_config.get("retry", 3),
            retry_delay=llm_config.get("retry_delay", 1.0),
            fallback=llm_config.get("fallback", []),
            timeout=llm_config.get("timeout", 60),
        )
    
    def _resolve_tools(self, tool_names: List[str]) -> List[str]:
        """사용 가능한 Tool 필터링"""
        available = []
        for name in tool_names:
            if self._tool_registry.is_available(name):
                available.append(name)
            else:
                logger.warning(f"[GenericAgent] Tool '{name}' not available, skipping")
        return available
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Agent 실행"""
        logger.info(f"[GenericAgent] {self.agent_id} executing (role={self.role})")
        
        try:
            # 1. Router 생성
            router = LLMRouter(
                policy=self._llm_policy,
                trace_callback=self.trace_callback,
                agent_id=self.agent_id,
            )
            
            # 2. 메시지 준비
            messages = self._build_messages(context)
            
            # 3. LLM 호출 (Router가 policy 처리)
            temperature = self.llm_config.get("temperature", 0.3)
            max_tokens = self.llm_config.get("max_tokens", 4096)
            
            llm_response = router.route(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            # 4. 출력 검증 (JSON)
            validated_output = self._validate_output(llm_response.content)
            
            # 5. Tool 실행
            tool_results = []
            if self._available_tools and self._has_code_blocks(llm_response.content):
                tool_results = self._execute_tools(llm_response.content)
            
            # 6. 결과 반환
            result = {
                "status": "success",
                "agent_id": self.agent_id,
                "role": self.role,
                "purpose": self.purpose,
                "llm_response": llm_response.content,
                "validated_output": validated_output,
                "tokens": {
                    "input": llm_response.tokens_input,
                    "output": llm_response.tokens_output,
                    "total": llm_response.tokens_total,
                },
                "latency_ms": llm_response.latency_ms,
                "model": llm_response.model,
                "provider": llm_response.provider,
                "tool_results": tool_results,
                "routing_info": {
                    "attempt": llm_response.attempt,
                    "fallback_from": llm_response.fallback_from,
                    "attempts": router.attempts,
                },
            }
            
            logger.info(
                f"[GenericAgent] {self.agent_id} completed | "
                f"provider: {llm_response.provider} | "
                f"tokens: {llm_response.tokens_total}"
            )
            
            return result
            
        except LLMAllProvidersFailedError as e:
            logger.error(f"[GenericAgent] {self.agent_id} all providers failed")
            raise
        except (LLMClientError, ToolError) as e:
            logger.error(f"[GenericAgent] {self.agent_id} error: {e}")
            raise
    
    def _build_messages(self, context: Dict[str, Any]) -> List[LLMMessage]:
        """LLM 메시지 구성"""
        messages = []
        
        # System prompt (JSON 출력 강제)
        system_content = self.system_prompt or ""
        if self._available_tools:
            system_content += f"\n\n사용 가능한 Tool: {self._available_tools}"
            system_content += "\n\n중요: Python 코드는 반드시 ```python 으로 시작하세요."
        
        # JSON 출력 요구
        if self.output_policy and self.output_policy.get("format") == "json":
            system_content += "\n\n중요: 반드시 유효한 JSON 형식으로 응답하세요."
        
        if system_content:
            messages.append(LLMMessage(role="system", content=system_content))
        
        # User message
        user_content = self._build_user_content(context)
        messages.append(LLMMessage(role="user", content=user_content))
        
        return messages
    
    def _build_user_content(self, context: Dict[str, Any]) -> str:
        """User 메시지 구성"""
        parts = [f"## 목적\n{self.purpose}"]
        
        inputs = context.get("inputs", {})
        if inputs:
            parts.append(
                f"\n## 입력 데이터\n```json\n"
                f"{json.dumps(inputs, ensure_ascii=False, indent=2)}\n```"
            )
        
        previous = context.get("previous_results", {})
        if previous:
            parts.append(f"\n## 이전 Agent 결과\n완료된 Agent: {list(previous.keys())}")
        
        return "\n".join(parts)
    
    def _validate_output(self, content: str) -> Optional[Dict[str, Any]]:
        """출력 JSON 검증"""
        if not self.output_policy:
            return None
        
        if self.output_policy.get("format") != "json":
            return None
        
        # JSON 블록 추출
        json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 전체가 JSON인 경우
            json_str = content.strip()
        
        try:
            parsed = json.loads(json_str)
            
            # required_fields 검증
            required = self.output_policy.get("required_fields", [])
            missing = [f for f in required if f not in parsed]
            
            if missing:
                logger.warning(f"[GenericAgent] Missing required fields: {missing}")
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.warning(f"[GenericAgent] JSON validation failed: {e}")
            return None
    
    def _has_code_blocks(self, content: str) -> bool:
        """코드 블록 존재 여부"""
        return "```python" in content.lower() or "```py" in content.lower()
    
    def _execute_tools(self, content: str) -> List[Dict[str, Any]]:
        """Tool 실행 + Trace 기록"""
        results = []
        code_blocks = self._extract_code_blocks(content)
        
        if not code_blocks or "python_exec" not in self._available_tools:
            return results
        
        tool = self._tool_registry.get("python_exec")
        
        for i, code in enumerate(code_blocks):
            logger.info(f"[GenericAgent] Executing code block {i+1}/{len(code_blocks)}")
            
            result: ToolResult = tool.run(code=code)
            
            # Trace 기록
            if self.trace_callback:
                self.trace_callback(
                    agent_id=self.agent_id,
                    step_type="TOOL",
                    status="OK" if result["ok"] else "ERROR",
                    payload={
                        "tool_name": "python_exec",
                        "input_summary": code[:100] + ("..." if len(code) > 100 else ""),
                        "output_summary": (result["output"] or "")[:200],
                    },
                    metadata=result["metadata"],
                )
            
            results.append({
                "tool": "python_exec",
                "ok": result["ok"],
                "output": result["output"],
                "error": result["error"],
                "metadata": result["metadata"],
            })
        
        return results
    
    def _extract_code_blocks(self, content: str) -> List[str]:
        """Python 코드 블록 추출"""
        pattern = r"```(?:python|python_exec|py)\s*(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
        return [m.strip() for m in matches if m.strip()]
