"""
NEXOUS Core - Agent Factory

Project YAML의 agent 정의 + Preset을 결합하여
실행 가능한 Agent 인스턴스를 생성한다.

LEVEL 1:
- use_llm=True → GenericAgent (실제 LLM 호출)
- use_llm=False → PresetAgent (Placeholder)
"""

from __future__ import annotations

import os
import logging
from typing import Dict, Any, Optional, Callable

from .base_agent import BaseAgent, PresetAgent
from .preset_loader import PresetLoader, PresetNotFoundError
from .exceptions import NEXOUSError

logger = logging.getLogger(__name__)


class AgentCreationError(NEXOUSError):
    """Agent 생성 오류"""
    pass


class AgentFactory:
    """
    Agent 팩토리
    
    agent_spec(Project YAML) + preset을 결합하여 Agent 인스턴스를 생성한다.
    
    LEVEL 1:
    - use_llm=True → GenericAgent 생성
    - use_llm=False → PresetAgent 생성 (Placeholder)
    """
    
    def __init__(
        self,
        preset_loader: PresetLoader,
        use_llm: bool = False,
        trace_callback: Callable = None,
    ):
        """
        Args:
            preset_loader: Preset 로더
            use_llm: 실제 LLM 사용 여부
            trace_callback: TraceWriter.log_step 콜백
        """
        self.preset_loader = preset_loader
        self.use_llm = use_llm
        self.trace_callback = trace_callback
        
        # 환경변수로 LLM 사용 여부 override
        if os.getenv("NEXOUS_USE_LLM", "").lower() in ("true", "1", "yes"):
            self.use_llm = True
    
    def create(self, agent_spec: Dict[str, Any]) -> BaseAgent:
        """
        Agent 인스턴스 생성
        
        Args:
            agent_spec: Project YAML의 agent 정의
                - id: Agent ID
                - preset: Preset 이름
                - purpose: Agent 목적
                - inputs: 입력 데이터
                - dependencies: 의존성
                
        Returns:
            BaseAgent 인스턴스
        """
        agent_id = agent_spec.get("id")
        preset_id = agent_spec.get("preset")
        purpose = agent_spec.get("purpose", "")
        
        if not agent_id:
            raise AgentCreationError("Missing 'id' in agent_spec")
        
        if not preset_id:
            raise AgentCreationError(f"Missing 'preset' in agent_spec for '{agent_id}'")
        
        try:
            # Preset 로드
            preset = self.preset_loader.get(preset_id)
            
            # Agent 생성
            if self.use_llm:
                # LEVEL 1: GenericAgent (실제 LLM 호출)
                from .generic_agent import GenericAgent
                
                agent = GenericAgent(
                    agent_id=agent_id,
                    role=preset.get("role", preset_id),
                    purpose=purpose,
                    llm_config=preset.get("llm", {}),
                    tools=preset.get("tools", []),
                    system_prompt=preset.get("system_prompt", ""),
                    output_policy=preset.get("output_policy"),
                    config=agent_spec,
                    trace_callback=self.trace_callback,
                )
                logger.debug(f"[AgentFactory] Created GenericAgent: {agent_id}")
            else:
                # Placeholder Agent
                agent = PresetAgent(
                    agent_id=agent_id,
                    role=preset.get("role", preset_id),
                    purpose=purpose,
                    llm_config=preset.get("llm", {}),
                    tools=preset.get("tools", []),
                    system_prompt=preset.get("system_prompt", ""),
                    output_policy=preset.get("output_policy"),
                    config=agent_spec,
                )
                logger.debug(f"[AgentFactory] Created PresetAgent: {agent_id}")
            
            return agent
            
        except PresetNotFoundError:
            raise
        except Exception as e:
            raise AgentCreationError(f"Failed to create agent '{agent_id}': {e}")
