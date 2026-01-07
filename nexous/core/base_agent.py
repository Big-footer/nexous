"""
NEXOUS Core - Base Agent

Agent 인터페이스 정의

Runner는 Agent 내부를 알지 못한다.
Runner는 단 하나만 안다: agent.execute(context) -> result
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Agent 기본 인터페이스
    
    모든 Agent는 이 클래스를 상속해야 한다.
    Runner는 오직 execute() 메서드만 호출한다.
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
        config: Dict[str, Any] = None
    ):
        self.agent_id = agent_id
        self.role = role
        self.purpose = purpose
        self.llm_config = llm_config or {}
        self.tools = tools or {}
        self.system_prompt = system_prompt
        self.output_policy = output_policy or {}
        self.config = config or {}
    
    @property
    def preset(self) -> str:
        """Preset ID (role과 동일)"""
        return self.role
    
    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agent 실행
        
        Args:
            context: 실행 컨텍스트
                - project: 프로젝트 정보
                - previous_results: 이전 Agent 결과들 (agent_id -> result)
                - inputs: Agent별 입력 데이터
                
        Returns:
            실행 결과 (다음 Agent의 context로 전달됨)
        """
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.agent_id}, role={self.role})"


class PresetAgent(BaseAgent):
    """
    Preset 기반 Agent
    
    AgentFactory에서 생성되며, Preset의 설정을 사용한다.
    
    NOTE: 실제 LLM 호출은 이후 단계에서 구현
    STEP 4에서는 인터페이스만 유지
    """
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agent 실행
        
        현재는 Placeholder 구현 (실제 LLM 호출 없음)
        """
        logger.info(f"[PresetAgent] {self.agent_id} executing (role={self.role})")
        logger.debug(f"[PresetAgent] LLM: {self.llm_config.get('provider')}/{self.llm_config.get('model')}")
        logger.debug(f"[PresetAgent] Tools: {list(self.tools.keys())}")
        
        # TODO: 실제 LLM 호출 구현 (STEP 5 이후)
        # 현재는 성공 결과 반환
        
        return {
            "status": "success",
            "agent_id": self.agent_id,
            "role": self.role,
            "purpose": self.purpose,
            "llm_config": self.llm_config,
            "tools_used": list(self.tools.keys()),
            "message": f"PresetAgent '{self.agent_id}' executed successfully"
        }


class DummyAgent(BaseAgent):
    """
    더미 Agent (테스트/개발용)
    
    Preset 없이 동작하는 최소 Agent
    """
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[DummyAgent] {self.agent_id} executed (role={self.role})")
        return {
            "status": "success",
            "agent_id": self.agent_id,
            "role": self.role,
            "message": f"DummyAgent '{self.agent_id}' completed"
        }
