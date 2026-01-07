#!/usr/bin/env python
"""Agent 스키마 v1.0 확인"""

import sys
from pathlib import Path
import json
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent))

from trace_store import TraceStore, RunStatus

# 임시 디렉토리
temp_dir = Path(tempfile.mkdtemp())
store = TraceStore(temp_dir)

# Run 시작
trace = store.start_run(
    run_id="run_20260101_001",
    project_id="flood_analysis",
    project_name="울산 침수 분석",
    agents_config=[
        {"id": "planner_01", "preset": "planner", "purpose": "침수 분석 계획 수립"},
        {"id": "executor_01", "preset": "executor", "purpose": "SWMM 기반 침수 시뮬레이션 실행"},
    ],
    execution_config={"mode": "sequential"}
)

# Agent 시작/완료 (steps 없이)
store.start_agent("run_20260101_001", "flood_analysis", "executor_01")
store.complete_agent("run_20260101_001", "flood_analysis", "executor_01", "COMPLETED")

# Run 완료
store.complete_run("run_20260101_001", "flood_analysis", RunStatus.COMPLETED)

# trace.json 확인
trace_path = temp_dir / "flood_analysis" / "run_20260101_001" / "trace.json"
with open(trace_path, 'r') as f:
    data = json.load(f)

print("\n" + "=" * 60)
print("  Agent Schema v1.0")
print("=" * 60)

for agent in data["agents"]:
    print(json.dumps(agent, indent=2, ensure_ascii=False))
    print()

# 정리
shutil.rmtree(temp_dir, ignore_errors=True)
