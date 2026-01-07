#!/usr/bin/env python
"""Step 스키마 v1.0 확인 (TOOL 포함)"""

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

# Run 시작
store.start_run(
    run_id="run_20260101_001",
    project_id="flood_analysis",
    project_name="울산 침수 분석",
    agents_config=[
        {"id": "executor_01", "preset": "executor", "purpose": "SWMM 기반 침수 시뮬레이션 실행"},
    ]
)

store.start_agent("run_20260101_001", "flood_analysis", "executor_01")

# 1. INPUT Step
input_step = TraceStep.create_input(
    agent_id="executor_01",
    timestamp="2026-01-01T12:02:10Z",
    context=["rainfall", "dem", "drainage_network"],
    previous_results=["planner_01"]
)
store.add_step("run_20260101_001", "flood_analysis", input_step)

# 2. LLM Step
llm_step = TraceStep.create_llm(
    agent_id="executor_01",
    sequence=1,
    provider="openai",
    model="gpt-4o",
    started_at="2026-01-01T12:02:15Z",
    ended_at="2026-01-01T12:02:22Z",
    latency_ms=7000,
    tokens_input=3120,
    tokens_output=860,
    input_summary="SWMM 실행 계획 해석",
    output_summary="침수 시뮬레이션 실행 지시 생성"
)
store.add_step("run_20260101_001", "flood_analysis", llm_step)

# 3. TOOL Step (새 스키마)
tool_step = TraceStep.create_tool(
    agent_id="executor_01",
    tool_name="python_exec",
    started_at="2026-01-01T12:02:25Z",
    ended_at="2026-01-01T12:05:30Z",
    latency_ms=185000,
    input_summary="SWMM 실행 스크립트",
    output_summary="침수 깊이 래스터 생성"
)
store.add_step("run_20260101_001", "flood_analysis", tool_step)

# 4. OUTPUT Step
output_step = TraceStep.create_output(
    agent_id="executor_01",
    timestamp="2026-01-01T12:05:35Z",
    output_keys=["flood_depth", "flow_rate", "water_level"],
    artifact_ids=["flood_depth_map", "simulation_log"]
)
store.add_step("run_20260101_001", "flood_analysis", output_step)

# 완료
store.complete_agent("run_20260101_001", "flood_analysis", "executor_01", "COMPLETED")
store.complete_run("run_20260101_001", "flood_analysis", RunStatus.COMPLETED)

# 결과 출력
trace_path = temp_dir / "flood_analysis" / "run_20260101_001" / "trace.json"
with open(trace_path, 'r') as f:
    data = json.load(f)

print("\n" + "=" * 60)
print("  Step Schema v1.0 (All Types)")
print("=" * 60)

for agent in data["agents"]:
    if agent["agent_id"] == "executor_01":
        print(f"\nAgent: {agent['agent_id']}")
        print("-" * 50)
        for step in agent["steps"]:
            print(f"\n[{step['type']}]")
            print(json.dumps(step, indent=2, ensure_ascii=False))

shutil.rmtree(temp_dir, ignore_errors=True)
