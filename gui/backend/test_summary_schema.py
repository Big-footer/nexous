#!/usr/bin/env python
"""Summary 스키마 v1.0 확인"""

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
        {"id": "planner_01", "preset": "planner", "purpose": "분석 계획 수립"},
        {"id": "executor_01", "preset": "executor", "purpose": "SWMM 시뮬레이션"},
        {"id": "analyst_01", "preset": "analyst", "purpose": "결과 분석"},
        {"id": "writer_01", "preset": "writer", "purpose": "보고서 작성"},
    ]
)

# Agent 1: planner
store.start_agent("run_20260101_001", "flood_analysis", "planner_01")
store.add_step("run_20260101_001", "flood_analysis", TraceStep.create_llm(
    agent_id="planner_01", sequence=1, provider="openai", model="gpt-4o",
    started_at="2026-01-01T12:01:00Z", ended_at="2026-01-01T12:01:05Z",
    latency_ms=5000, tokens_input=1000, tokens_output=500,
    input_summary="분석 계획 요청", output_summary="계획 생성"
))
store.complete_agent("run_20260101_001", "flood_analysis", "planner_01", "COMPLETED")

# Agent 2: executor
store.start_agent("run_20260101_001", "flood_analysis", "executor_01")
store.add_step("run_20260101_001", "flood_analysis", TraceStep.create_llm(
    agent_id="executor_01", sequence=1, provider="openai", model="gpt-4o",
    started_at="2026-01-01T12:02:00Z", ended_at="2026-01-01T12:02:03Z",
    latency_ms=3000, tokens_input=2000, tokens_output=800,
    input_summary="실행 계획 해석", output_summary="실행 지시"
))
store.add_step("run_20260101_001", "flood_analysis", TraceStep.create_tool(
    agent_id="executor_01", tool_name="python_exec",
    started_at="2026-01-01T12:02:05Z", ended_at="2026-01-01T12:05:00Z",
    latency_ms=175000, input_summary="SWMM 스크립트", output_summary="시뮬레이션 완료"
))
store.add_step("run_20260101_001", "flood_analysis", TraceStep.create_tool(
    agent_id="executor_01", tool_name="file_write",
    started_at="2026-01-01T12:05:01Z", ended_at="2026-01-01T12:05:02Z",
    latency_ms=1000, input_summary="래스터 저장", output_summary="flood_depth.tif"
))
store.complete_agent("run_20260101_001", "flood_analysis", "executor_01", "COMPLETED")

# Agent 3: analyst
store.start_agent("run_20260101_001", "flood_analysis", "analyst_01")
store.add_step("run_20260101_001", "flood_analysis", TraceStep.create_llm(
    agent_id="analyst_01", sequence=1, provider="openai", model="gpt-4o",
    started_at="2026-01-01T12:05:10Z", ended_at="2026-01-01T12:05:15Z",
    latency_ms=5000, tokens_input=3000, tokens_output=1500,
    input_summary="결과 분석 요청", output_summary="분석 완료"
))
store.add_step("run_20260101_001", "flood_analysis", TraceStep.create_tool(
    agent_id="analyst_01", tool_name="python_exec",
    started_at="2026-01-01T12:05:16Z", ended_at="2026-01-01T12:05:30Z",
    latency_ms=14000, input_summary="통계 계산", output_summary="통계 완료"
))
store.complete_agent("run_20260101_001", "flood_analysis", "analyst_01", "COMPLETED")

# Agent 4: writer
store.start_agent("run_20260101_001", "flood_analysis", "writer_01")
store.add_step("run_20260101_001", "flood_analysis", TraceStep.create_llm(
    agent_id="writer_01", sequence=1, provider="openai", model="gpt-4o",
    started_at="2026-01-01T12:06:00Z", ended_at="2026-01-01T12:06:10Z",
    latency_ms=10000, tokens_input=2500, tokens_output=1500,
    input_summary="보고서 작성 요청", output_summary="보고서 생성"
))
store.add_step("run_20260101_001", "flood_analysis", TraceStep.create_llm(
    agent_id="writer_01", sequence=2, provider="openai", model="gpt-4o",
    started_at="2026-01-01T12:06:15Z", ended_at="2026-01-01T12:06:20Z",
    latency_ms=5000, tokens_input=500, tokens_output=150,
    input_summary="요약 생성", output_summary="요약 완료"
))
store.complete_agent("run_20260101_001", "flood_analysis", "writer_01", "COMPLETED")

# Run 완료
store.complete_run("run_20260101_001", "flood_analysis", RunStatus.COMPLETED)

# 결과 출력
trace_path = temp_dir / "flood_analysis" / "run_20260101_001" / "trace.json"
with open(trace_path, 'r') as f:
    data = json.load(f)

print("\n" + "=" * 60)
print("  Summary Schema v1.0")
print("=" * 60)
print(json.dumps(data["summary"], indent=2, ensure_ascii=False))

print("\n" + "-" * 60)
print("  Expected:")
print("-" * 60)
print("""
{
  "total_agents": 4,
  "completed_agents": 4,
  "failed_agents": 0,
  "total_llm_calls": 5,
  "total_tool_calls": 3,
  "total_tokens": 12450,
  "total_duration_ms": ...
}
""")

shutil.rmtree(temp_dir, ignore_errors=True)
