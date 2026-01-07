#!/usr/bin/env python
"""trace.json 스키마 확인"""

import sys
from pathlib import Path
import json
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent))

from trace_store import TraceStore, TraceStep, StepType, RunStatus
from datetime import datetime

# 임시 디렉토리에 테스트
temp_dir = Path(tempfile.mkdtemp())
store = TraceStore(temp_dir)

# Run 시작
trace = store.start_run(
    run_id="run_20260101_001",
    project_id="flood_analysis_ulsan",
    project_name="울산 태화지구 침수 분석",
    agents_config=[
        {"id": "planner", "preset": "core/planner", "purpose": "계획 수립"},
        {"id": "executor", "preset": "core/executor", "purpose": "실행"},
    ],
    execution_config={"mode": "sequential", "max_retries": 3}
)

# Agent/Step 시뮬레이션
store.start_agent("run_20260101_001", "flood_analysis_ulsan", "planner")

step = TraceStep(
    step_id="planner_llm_001",
    agent_id="planner",
    step_type=StepType.LLM,
    status="COMPLETED",
    started_at=datetime.utcnow().isoformat() + "Z",
    ended_at=datetime.utcnow().isoformat() + "Z",
    latency_ms=2000,
    model="gpt-4o",
    tokens=1500,
    output_summary="Plan generated"
)
store.add_step("run_20260101_001", "flood_analysis_ulsan", step)
store.complete_agent("run_20260101_001", "flood_analysis_ulsan", "planner", "COMPLETED")

# Artifact 추가
store.add_artifact(
    "run_20260101_001", "flood_analysis_ulsan",
    artifact_id="flood_depth_map",
    source_agent="executor",
    artifact_type="tif",
    path="outputs/flood_depth.tif",
    size_bytes=1024000
)

# Run 완료
store.complete_run("run_20260101_001", "flood_analysis_ulsan", RunStatus.COMPLETED)

# trace.json 출력
trace_path = temp_dir / "flood_analysis_ulsan" / "run_20260101_001" / "trace.json"
with open(trace_path, 'r') as f:
    trace_json = json.load(f)

print("\n" + "=" * 60)
print("  trace.json (v1.0 스키마)")
print("=" * 60)
print(json.dumps(trace_json, indent=2, ensure_ascii=False))

# 정리
shutil.rmtree(temp_dir, ignore_errors=True)
