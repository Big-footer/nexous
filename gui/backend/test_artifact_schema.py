#!/usr/bin/env python
"""Artifact 스키마 v1.0 확인"""

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

# Artifacts 추가
store.add_artifact(
    run_id="run_20260101_001",
    project_id="flood_analysis",
    artifact_id="flood_depth_map",
    artifact_type="raster",
    path="outputs/maps/flood_depth.tif",
    created_by="executor_01",
    created_at="2026-01-01T12:05:40Z"
)

store.add_artifact(
    run_id="run_20260101_001",
    project_id="flood_analysis",
    artifact_id="simulation_log",
    artifact_type="log",
    path="outputs/logs/swmm_run.log",
    created_by="executor_01",
    created_at="2026-01-01T12:05:41Z"
)

store.add_artifact(
    run_id="run_20260101_001",
    project_id="flood_analysis",
    artifact_id="final_report",
    artifact_type="markdown",
    path="outputs/reports/flood_analysis_report.md",
    created_by="writer_01",
    created_at="2026-01-01T12:07:30Z"
)

# 완료
store.complete_agent("run_20260101_001", "flood_analysis", "executor_01", "COMPLETED")
store.complete_run("run_20260101_001", "flood_analysis", RunStatus.COMPLETED)

# 결과 출력
trace_path = temp_dir / "flood_analysis" / "run_20260101_001" / "trace.json"
with open(trace_path, 'r') as f:
    data = json.load(f)

print("\n" + "=" * 60)
print("  Artifact Schema v1.0")
print("=" * 60)

for artifact in data["artifacts"]:
    print(json.dumps(artifact, indent=2, ensure_ascii=False))
    print()

shutil.rmtree(temp_dir, ignore_errors=True)
