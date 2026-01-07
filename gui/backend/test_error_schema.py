#!/usr/bin/env python
"""Error 스키마 v1.0 확인"""

import sys
from pathlib import Path
import json
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent))

from trace_store import TraceStore, TraceStep, StepType, RunStatus

temp_dir = Path(tempfile.mkdtemp())
store = TraceStore(temp_dir)

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

# TOOL Step 추가
tool_step = TraceStep.create_tool(
    agent_id="executor_01",
    tool_name="python_exec",
    started_at="2026-01-01T12:02:25Z",
    ended_at="2026-01-01T12:03:10Z",
    latency_ms=45000,
    input_summary="SWMM 실행 스크립트",
    output_summary="",
    status="ERROR"
)
store.add_step("run_20260101_001", "flood_analysis", tool_step)

# Error 추가
store.add_error(
    run_id="run_20260101_001",
    project_id="flood_analysis",
    agent_id="executor_01",
    step_id="executor_01.tool_python_exec",
    error_type="TOOL_ERROR",
    message="SWMM 실행 실패",
    timestamp="2026-01-01T12:03:10Z",
    recoverable=False
)

# 두 번째 에러 (복구 가능)
store.add_error(
    run_id="run_20260101_001",
    project_id="flood_analysis",
    agent_id="executor_01",
    step_id="executor_01.llm_01",
    error_type="LLM_ERROR",
    message="Rate limit exceeded",
    timestamp="2026-01-01T12:03:15Z",
    recoverable=True
)

# 완료
store.complete_agent("run_20260101_001", "flood_analysis", "executor_01", "FAILED", error="SWMM 실행 실패")
store.complete_run("run_20260101_001", "flood_analysis", RunStatus.FAILED)

# 결과 출력
trace_path = temp_dir / "flood_analysis" / "run_20260101_001" / "trace.json"
with open(trace_path, 'r') as f:
    data = json.load(f)

print("\n" + "=" * 60)
print("  Error Schema v1.0")
print("=" * 60)

for error in data["errors"]:
    print(json.dumps(error, indent=2, ensure_ascii=False))
    print()

print(f"Run Status: {data['status']}")
print(f"Retry Count: {data['execution']['retry_count']}")

shutil.rmtree(temp_dir, ignore_errors=True)
