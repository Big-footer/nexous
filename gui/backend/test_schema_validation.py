#!/usr/bin/env python
"""JSON Schema로 trace.json 검증"""

import sys
from pathlib import Path
import json
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent))

try:
    import jsonschema
    from jsonschema import validate, ValidationError
except ImportError:
    print("jsonschema 패키지가 필요합니다: pip install jsonschema")
    sys.exit(1)

from trace_store import TraceStore, TraceStep, StepType, RunStatus

# 스키마 로드
schema_path = Path(__file__).parent / "schemas" / "trace_schema_v1.json"
with open(schema_path, 'r') as f:
    schema = json.load(f)

# 임시 디렉토리에서 테스트
temp_dir = Path(tempfile.mkdtemp())
store = TraceStore(temp_dir)

print("=" * 60)
print("  JSON Schema Validation Test")
print("=" * 60)

# 완전한 trace 생성
store.start_run(
    run_id="run_20260101_001",
    project_id="flood_analysis",
    project_name="울산 침수 분석",
    agents_config=[
        {"id": "planner_01", "preset": "planner", "purpose": "분석 계획 수립"},
        {"id": "executor_01", "preset": "executor", "purpose": "SWMM 시뮬레이션"},
    ]
)

# Agent 1: planner
store.start_agent("run_20260101_001", "flood_analysis", "planner_01")

store.add_step("run_20260101_001", "flood_analysis", TraceStep.create_input(
    agent_id="planner_01",
    timestamp="2026-01-01T12:00:00Z",
    context=["user_request", "project_config"],
    previous_results=[]
))

store.add_step("run_20260101_001", "flood_analysis", TraceStep.create_llm(
    agent_id="planner_01", sequence=1,
    provider="openai", model="gpt-4o",
    started_at="2026-01-01T12:00:01Z",
    ended_at="2026-01-01T12:00:05Z",
    latency_ms=4000,
    tokens_input=1000, tokens_output=500,
    input_summary="분석 계획 요청",
    output_summary="계획 생성 완료"
))

store.add_step("run_20260101_001", "flood_analysis", TraceStep.create_output(
    agent_id="planner_01",
    timestamp="2026-01-01T12:00:06Z",
    output_keys=["analysis_plan"],
    artifact_ids=[]
))

store.complete_agent("run_20260101_001", "flood_analysis", "planner_01", "COMPLETED")

# Agent 2: executor
store.start_agent("run_20260101_001", "flood_analysis", "executor_01")

store.add_step("run_20260101_001", "flood_analysis", TraceStep.create_input(
    agent_id="executor_01",
    timestamp="2026-01-01T12:01:00Z",
    context=["rainfall", "dem"],
    previous_results=["planner_01"]
))

store.add_step("run_20260101_001", "flood_analysis", TraceStep.create_llm(
    agent_id="executor_01", sequence=1,
    provider="openai", model="gpt-4o",
    started_at="2026-01-01T12:01:01Z",
    ended_at="2026-01-01T12:01:03Z",
    latency_ms=2000,
    tokens_input=2000, tokens_output=800,
    input_summary="실행 계획 해석",
    output_summary="실행 지시 생성"
))

store.add_step("run_20260101_001", "flood_analysis", TraceStep.create_tool(
    agent_id="executor_01",
    tool_name="python_exec",
    started_at="2026-01-01T12:01:05Z",
    ended_at="2026-01-01T12:05:00Z",
    latency_ms=235000,
    input_summary="SWMM 실행 스크립트",
    output_summary="침수 깊이 래스터 생성"
))

store.add_step("run_20260101_001", "flood_analysis", TraceStep.create_output(
    agent_id="executor_01",
    timestamp="2026-01-01T12:05:01Z",
    output_keys=["flood_depth", "simulation_log"],
    artifact_ids=["flood_depth_map"]
))

store.complete_agent("run_20260101_001", "flood_analysis", "executor_01", "COMPLETED")

# Artifact 추가
store.add_artifact(
    run_id="run_20260101_001",
    project_id="flood_analysis",
    artifact_id="flood_depth_map",
    artifact_type="raster",
    path="outputs/maps/flood_depth.tif",
    created_by="executor_01",
    created_at="2026-01-01T12:05:00Z"
)

# Run 완료
store.complete_run("run_20260101_001", "flood_analysis", RunStatus.COMPLETED)

# trace.json 로드
trace_path = temp_dir / "flood_analysis" / "run_20260101_001" / "trace.json"
with open(trace_path, 'r') as f:
    trace_data = json.load(f)

# 스키마 검증
print("\n[1] Validating trace.json against schema...")

try:
    validate(instance=trace_data, schema=schema)
    print("✅ Schema validation PASSED!")
except ValidationError as e:
    print(f"❌ Schema validation FAILED:")
    print(f"   Path: {' -> '.join(str(p) for p in e.absolute_path)}")
    print(f"   Error: {e.message}")
    sys.exit(1)

# 구조 확인
print("\n[2] Structure Check:")
print(f"   trace_version: {trace_data.get('trace_version')}")
print(f"   project_id: {trace_data.get('project_id')}")
print(f"   run_id: {trace_data.get('run_id')}")
print(f"   status: {trace_data.get('status')}")
print(f"   agents: {len(trace_data.get('agents', []))} agents")
print(f"   artifacts: {len(trace_data.get('artifacts', []))} artifacts")
print(f"   errors: {len(trace_data.get('errors', []))} errors")

# Summary 확인
summary = trace_data.get('summary', {})
print(f"\n[3] Summary:")
print(f"   total_agents: {summary.get('total_agents')}")
print(f"   completed_agents: {summary.get('completed_agents')}")
print(f"   total_llm_calls: {summary.get('total_llm_calls')}")
print(f"   total_tool_calls: {summary.get('total_tool_calls')}")
print(f"   total_tokens: {summary.get('total_tokens')}")

# Step 타입별 확인
print(f"\n[4] Steps by Type:")
for agent in trace_data.get('agents', []):
    print(f"\n   Agent: {agent['agent_id']}")
    for step in agent.get('steps', []):
        step_type = step.get('type')
        step_id = step.get('step_id')
        status = step.get('status')
        print(f"     - [{step_type}] {step_id}: {status}")

print("\n" + "=" * 60)
print("  All validations PASSED! ✅")
print("=" * 60)

# 정리
shutil.rmtree(temp_dir, ignore_errors=True)
