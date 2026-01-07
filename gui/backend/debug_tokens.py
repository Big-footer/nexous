#!/usr/bin/env python
"""Step tokens 디버깅 v2"""

import sys
from pathlib import Path
import json
import tempfile
import shutil
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

from trace_store import TraceStore, TraceStep, StepType, RunStatus

temp_dir = Path(tempfile.mkdtemp())
store = TraceStore(temp_dir)

def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

# Run/Agent 시작
store.start_run(
    run_id="run_001",
    project_id="test",
    agents_config=[{"id": "agent_01", "preset": "executor", "purpose": "test"}]
)
store.start_agent("run_001", "test", "agent_01")

# LLM Step 추가
llm_step = TraceStep.create_llm(
    agent_id="agent_01",
    sequence=1,
    provider="openai",
    model="gpt-4o",
    started_at=now_utc(),
    ended_at=now_utc(),
    latency_ms=7000,
    tokens_input=3120,
    tokens_output=860,
    input_summary="test input",
    output_summary="test output"
)
store.add_step("run_001", "test", llm_step)

# complete_agent 전 active_agent 확인
agent = store._get_active_agent("run_001", "agent_01")
print(f"Before complete_agent:")
print(f"  Agent steps: {len(agent.steps)}")
print(f"  Agent total_tokens: {agent.total_tokens}")

# 완료
store.complete_agent("run_001", "test", "agent_01", "COMPLETED")

# complete_agent 후 확인
print(f"\nAfter complete_agent:")
print(f"  Agent total_tokens: {agent.total_tokens}")

# JSON 직렬화 확인
agent_dict = agent.to_dict()
print(f"  agent.to_dict() keys: {agent_dict.keys()}")
print(f"  'total_tokens' in dict: {'total_tokens' in agent_dict}")

# 파일에서 읽기
trace_path = temp_dir / "test" / "run_001" / "trace.json"
with open(trace_path, 'r') as f:
    data = json.load(f)

print(f"\nFrom file:")
print(f"  agents[0] keys: {data['agents'][0].keys()}")

shutil.rmtree(temp_dir, ignore_errors=True)
