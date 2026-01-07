"""
NEXOUS Core - LLM Agent

LEVEL 1: 플랫폼 안정화
- OpenAI 단일 provider
- gpt-4o 단일 모델
- 모든 LLM/Tool 호출 Trace 기록
"""

from __future__ import annotations

import json
import logging
from typing import Dict, Any, List, Callable

from .base_agent import BaseAgent
from ..providers.openai_provider import OpenAIProvider, LLMResponse
from ..tools import default_registry, ToolResult

logger = logging.getLogger(__name__)


class LLMAgent(BaseAgent):
    """
    실제 LLM을 호출하는 Agent
    
    LEVEL 1 제약:
    - OpenAI만 사용
    - gpt-4o 모델 고정
    - python_exec, file_read, file_write 3개 Tool만
    """
    
    def __init__(
        self,
        agent_id: str,
        role: str,
        purpose: str,
        llm_config: Dict[str, Any] = None,
        tools: Dict[str, Any] = None,
        system_prompt: str = "",
        output_policy: Dict[str, Any] = None,
        config: Dict[str, Any] = None,
        trace_callback: Callable = None
    ):
        super().__init__(
            agent_id=agent_id,
            role=role,
            purpose=purpose,
            llm_config=llm_config,
            tools=tools,
            system_prompt=system_prompt,
            output_policy=output_policy,
            config=config
        )
        
        self.trace_callback = trace_callback
        self._llm_provider = None
        self._tool_registry = default_registry
    
    @property
    def llm(self) -> OpenAIProvider:
        """LLM Provider (OpenAI 단일)"""
        if self._llm_provider is None:
            # LEVEL 1: OpenAI, gpt-4o 고정
            model = self.llm_config.get("model", "gpt-4o")
            self._llm_provider = OpenAIProvider(model=model)
        return self._llm_provider
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Agent 실행"""
        logger.info(f"[LLMAgent] {self.agent_id} executing (role={self.role})")
        
        # 1. 입력 준비
        user_message = self._prepare_user_message(context)
        
        # 2. LLM 호출 (Trace 기록)
        llm_response = self._call_llm(user_message)
        
        # 3. Tool 호출 (Trace 기록)
        tool_results = []
        if self._has_code_blocks(llm_response.content):
            tool_results = self._execute_tools(llm_response.content)
        
        # 4. 결과 반환
        return {
            "status": "success",
            "agent_id": self.agent_id,
            "role": self.role,
            "purpose": self.purpose,
            "llm_response": llm_response.content,
            "tokens": {
                "input": llm_response.tokens_input,
                "output": llm_response.tokens_output,
                "total": llm_response.tokens_total
            },
            "latency_ms": llm_response.latency_ms,
            "tool_results": tool_results
        }
    
    def _prepare_user_message(self, context: Dict[str, Any]) -> str:
        """사용자 메시지 준비"""
        parts = [f"## 목적\n{self.purpose}"]
        
        inputs = context.get("inputs", {})
        if inputs:
            parts.append(f"\n## 입력 데이터\n```json\n{json.dumps(inputs, ensure_ascii=False, indent=2)}\n```")
        
        previous = context.get("previous_results", {})
        if previous:
            parts.append(f"\n## 이전 Agent 결과\n완료: {list(previous.keys())}")
        
        return "\n".join(parts)
    
    def _call_llm(self, user_message: str) -> LLMResponse:
        """LLM 호출 + Trace 기록"""
        temperature = self.llm_config.get("temperature", 0.3)
        
        response = self.llm.chat(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=self.system_prompt,
            temperature=temperature
        )
        
        # Trace 기록
        if self.trace_callback:
            self.trace_callback(
                agent_id=self.agent_id,
                step_type="LLM",
                status="OK",
                payload={
                    "input_summary": user_message[:200] + "..." if len(user_message) > 200 else user_message,
                    "output_summary": response.content[:200] + "..." if len(response.content) > 200 else response.content
                },
                metadata={
                    "provider": "openai",
                    "model": response.model,
                    "tokens_input": response.tokens_input,
                    "tokens_output": response.tokens_output,
                    "latency_ms": response.latency_ms
                }
            )
        
        return response
    
    def _has_code_blocks(self, content: str) -> bool:
        """코드 블록 존재 여부"""
        return "```python" in content.lower()
    
    def _execute_tools(self, content: str) -> List[Dict]:
        """Tool 실행 + Trace 기록"""
        results = []
        code_blocks = self._extract_code_blocks(content)
        
        for code in code_blocks:
            if not self._tool_registry.has("python_exec"):
                continue
            
            tool = self._tool_registry.get("python_exec")
            result = tool.execute(code=code)
            
            # Trace 기록
            if self.trace_callback:
                self.trace_callback(
                    agent_id=self.agent_id,
                    step_type="TOOL",
                    status="OK" if result.success else "ERROR",
                    payload={
                        "tool_name": "python_exec",
                        "input_summary": code[:100] + "..." if len(code) > 100 else code,
                        "output_summary": str(result.output)[:200] if result.output else ""
                    },
                    metadata={
                        "latency_ms": result.latency_ms,
                        "success": result.success
                    }
                )
            
            results.append({
                "tool": "python_exec",
                "success": result.success,
                "output": result.output,
                "error": result.error
            })
        
        return results
    
    def _extract_code_blocks(self, content: str) -> List[str]:
        """Python 코드 블록 추출"""
        blocks = []
        parts = content.split("```python")
        
        for part in parts[1:]:
            if "```" in part:
                code = part.split("```")[0].strip()
                if code:
                    blocks.append(code)
        
        return blocks
