"""
NEXOUS Test - Conftest

pytest 공통 fixtures

LEVEL 2 확장:
- LLM Policy fixtures
- Mock LLM Client
- Output Schema
"""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# .env 로드
ENV_FILE = PROJECT_ROOT / ".env"
if ENV_FILE.exists():
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k and not os.getenv(k):
                    os.environ[k] = v


# ============================================================
# 기본 Fixtures
# ============================================================

@pytest.fixture
def project_root():
    """프로젝트 루트 경로"""
    return PROJECT_ROOT


@pytest.fixture
def test_trace_dir(tmp_path):
    """임시 trace 디렉토리"""
    trace_dir = tmp_path / "traces"
    trace_dir.mkdir()
    return trace_dir


@pytest.fixture
def test_project_yaml(tmp_path):
    """테스트용 project.yaml 생성"""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    
    project_yaml = project_dir / "project.yaml"
    project_yaml.write_text("""
project_id: test_project
version: "1.0"
description: LEVEL 2 테스트 프로젝트

execution:
  mode: sequential

agents:
  - id: test_agent
    preset: executor
    purpose: 테스트 계산 수행
    inputs:
      task: "1+2+3을 계산하세요"
""")
    return str(project_yaml)


@pytest.fixture
def simple_project_yaml(tmp_path):
    """단순 테스트용 project.yaml"""
    project_dir = tmp_path / "simple_project"
    project_dir.mkdir()
    
    project_yaml = project_dir / "project.yaml"
    project_yaml.write_text("""
project_id: simple_test
version: "1.0"

agents:
  - id: planner
    preset: planner
    purpose: 간단한 계획 수립
""")
    return str(project_yaml)


@pytest.fixture
def invalid_project_yaml(tmp_path):
    """잘못된 project.yaml (agents 없음)"""
    project_dir = tmp_path / "invalid_project"
    project_dir.mkdir()
    
    project_yaml = project_dir / "project.yaml"
    project_yaml.write_text("""
project_id: invalid_test
version: "1.0"
# agents 필드 없음
""")
    return str(project_yaml)


@pytest.fixture
def has_openai_key():
    """OpenAI API 키 존재 여부"""
    key = os.getenv("OPENAI_API_KEY", "")
    return bool(key and key.startswith("sk-"))


@pytest.fixture
def has_anthropic_key():
    """Anthropic API 키 존재 여부"""
    key = os.getenv("ANTHROPIC_API_KEY", "")
    return bool(key)


@pytest.fixture
def has_gemini_key():
    """Gemini API 키 존재 여부"""
    key = os.getenv("GOOGLE_API_KEY", "")
    return bool(key)


# ============================================================
# LEVEL 2: LLM Policy Fixtures
# ============================================================

@pytest.fixture
def default_llm_policy():
    """기본 LLM Policy"""
    from nexous.llm import LLMPolicy
    
    return LLMPolicy(
        primary="openai/gpt-4o",
        retry=3,
        retry_delay=1.0,
        fallback=["anthropic/claude-3-5-sonnet-20241022", "gemini/gemini-1.5-pro"],
        timeout=60,
    )


@pytest.fixture
def openai_only_policy():
    """OpenAI 전용 Policy"""
    from nexous.llm import LLMPolicy
    
    return LLMPolicy(
        primary="openai/gpt-4o",
        retry=2,
        fallback=[],
        timeout=30,
    )


@pytest.fixture
def fallback_policy():
    """Fallback 테스트용 Policy"""
    from nexous.llm import LLMPolicy
    
    return LLMPolicy(
        primary="openai/gpt-4o",
        retry=1,
        retry_delay=0.1,
        fallback=["anthropic/claude-3-5-sonnet-20241022"],
        timeout=30,
    )


# ============================================================
# LEVEL 2: Mock LLM Client
# ============================================================

@pytest.fixture
def mock_llm_response():
    """Mock LLM Response 생성 함수"""
    from nexous.llm import LLMResponse
    
    def _create(
        content: str = "Test response",
        provider: str = "openai",
        model: str = "gpt-4o",
        tokens_input: int = 10,
        tokens_output: int = 20,
        latency_ms: int = 100,
    ):
        return LLMResponse(
            content=content,
            provider=provider,
            model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            latency_ms=latency_ms,
            finish_reason="stop",
        )
    
    return _create


@pytest.fixture
def mock_openai_client(mock_llm_response):
    """Mock OpenAI Client"""
    client = Mock()
    client.provider = "openai"
    client.is_available.return_value = True
    client.generate.return_value = mock_llm_response(
        content='{"result": "success"}',
        provider="openai",
        model="gpt-4o",
    )
    return client


@pytest.fixture
def mock_anthropic_client(mock_llm_response):
    """Mock Anthropic Client"""
    client = Mock()
    client.provider = "anthropic"
    client.is_available.return_value = True
    client.generate.return_value = mock_llm_response(
        content='{"result": "fallback success"}',
        provider="anthropic",
        model="claude-3-5-sonnet-20241022",
    )
    return client


@pytest.fixture
def mock_failing_client():
    """항상 실패하는 Mock Client"""
    from nexous.llm import LLMClientError
    
    client = Mock()
    client.provider = "mock"
    client.is_available.return_value = True
    client.generate.side_effect = LLMClientError(
        "Mock API Error",
        provider="mock",
        recoverable=True,
    )
    return client


@pytest.fixture
def mock_unrecoverable_client():
    """복구 불가능한 실패 Mock Client"""
    from nexous.llm import LLMClientError
    
    client = Mock()
    client.provider = "mock"
    client.is_available.return_value = True
    client.generate.side_effect = LLMClientError(
        "Invalid API Key",
        provider="mock",
        recoverable=False,
    )
    return client


# ============================================================
# LEVEL 2: Output Schema
# ============================================================

@pytest.fixture
def output_schema():
    """출력 JSON Schema"""
    schema_path = PROJECT_ROOT / "schemas" / "output_schema.json"
    if schema_path.exists():
        with open(schema_path) as f:
            return json.load(f)
    
    # 기본 스키마
    return {
        "type": "object",
        "properties": {
            "agent_id": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "error"]},
        },
        "required": ["agent_id", "status"]
    }


@pytest.fixture
def executor_output_schema():
    """Executor 출력 Schema"""
    return {
        "type": "object",
        "required": ["execution_status"],
        "properties": {
            "execution_status": {
                "type": "string",
                "enum": ["success", "partial", "failed"]
            },
            "output_files": {
                "type": "array",
                "items": {"type": "string"}
            },
            "logs": {
                "type": "array",
                "items": {"type": "string"}
            },
        }
    }


# ============================================================
# LEVEL 2: Trace Schema
# ============================================================

@pytest.fixture
def trace_schema():
    """trace_schema.json 로드"""
    return {
        "type": "object",
        "required": ["run_id", "project_id", "status", "agents", "summary"],
        "properties": {
            "run_id": {"type": "string"},
            "project_id": {"type": "string"},
            "status": {"type": "string", "enum": ["RUNNING", "COMPLETED", "FAILED"]},
            "agents": {"type": "array"},
            "summary": {"type": "object"},
            "errors": {"type": "array"},
        }
    }


# ============================================================
# Helper Functions
# ============================================================

def load_trace(trace_path: str) -> dict:
    """trace.json 로드 헬퍼"""
    with open(trace_path) as f:
        return json.load(f)


def count_llm_steps(trace: dict) -> int:
    """LLM step 개수"""
    count = 0
    for agent in trace.get("agents", []):
        for step in agent.get("steps", []):
            if step.get("type") == "LLM":
                count += 1
    return count


def get_llm_steps(trace: dict) -> list:
    """LLM step 목록"""
    steps = []
    for agent in trace.get("agents", []):
        for step in agent.get("steps", []):
            if step.get("type") == "LLM":
                steps.append(step)
    return steps
