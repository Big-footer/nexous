"""
NEXOUS Core - State Enums

Run / Agent / Step 상태 정의
"""

from enum import Enum


class RunStatus(str, Enum):
    """
    Run 실행 상태
    
    상태 전이:
        CREATED → RUNNING → COMPLETED
                         → FAILED
    """
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AgentStatus(str, Enum):
    """
    Agent 실행 상태
    
    상태 전이:
        IDLE → RUNNING → COMPLETED
                      → FAILED
    """
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StepType(str, Enum):
    """Step 타입"""
    INPUT = "INPUT"
    LLM = "LLM"
    TOOL = "TOOL"
    OUTPUT = "OUTPUT"


class StepStatus(str, Enum):
    """Step 상태"""
    OK = "OK"
    ERROR = "ERROR"
