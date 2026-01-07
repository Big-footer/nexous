#!/usr/bin/env python
"""TraceWriter API 계약 테스트"""

import sys
from pathlib import Path
import json
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nexous.core import TraceWriter

temp_dir = Path(tempfile.mkdtemp())

print("=" * 60)
print("  TraceWriter API Contract Test")
print("=" * 60)

writer = TraceWriter(base_dir=str(temp_dir))

# 1. start_run(project_id, run_id, execution_mode)
print("\n[1] start_run(project_id, run_id, execution_mode)")
writer.start_run("flood_analysis_ulsan", "run_20260104_001", "sequential")
print("    ✅ Run started")

# 2. start_agent(agent_id, preset, purpose)
print("\n[2] start_agent(agent_id, preset, purpose)")
writer.start_agent("planner_01", "planner", "분석 계획 수립")
print("    ✅ Agent started")

# 3. log_step - INPUT
print("\n[3] log_step(agent_id, 'INPUT', status, payload)")
writer.log_step(
    agent_id="planner_01",
    step_type="INPUT",
    status="OK",
    payload={
        "context": ["user_request", "project_config"],
        "previous_results": []
    }
)
print("    ✅ INPUT step logged")

# 4. log_step - LLM
print("\n[4] log_step(agent_id, 'LLM', status, payload, metadata)")
writer.log_step(
    agent_id="planner_01",
    step_type="LLM",
    status="OK",
    payload={
        "input_summary": "침수 분석 계획 요청",
        "output_summary": "4단계 분석 계획 생성"
    },
    metadata={
        "provider": "openai",
        "model": "gpt-4o",
        "tokens_input": 1000,
        "tokens_output": 500,
        "latency_ms": 2100
    }
)
print("    ✅ LLM step logged")

# 5. log_step - OUTPUT
print("\n[5] log_step(agent_id, 'OUTPUT', status, payload)")
writer.log_step(
    agent_id="planner_01",
    step_type="OUTPUT",
    status="OK",
    payload={
        "output_keys": ["analysis_plan"],
        "artifact_ids": []
    }
)
print("    ✅ OUTPUT step logged")

# 6. end_agent(agent_id, status)
print("\n[6] end_agent(agent_id, status)")
writer.end_agent("planner_01", "COMPLETED")
print("    ✅ Agent ended")

# 7. Second agent with TOOL
print("\n[7] Second agent: executor_01")
writer.start_agent("executor_01", "executor", "SWMM 시뮬레이션")

writer.log_step("executor_01", "INPUT", "OK", {
    "context": ["rainfall", "dem"],
    "previous_results": ["planner_01"]
})

writer.log_step("executor_01", "LLM", "OK",
    payload={"input_summary": "실행 계획 해석", "output_summary": "스크립트 생성"},
    metadata={"provider": "openai", "model": "gpt-4o", "tokens_input": 2000, "tokens_output": 800, "latency_ms": 3000}
)

# 8. log_step - TOOL
print("\n[8] log_step(agent_id, 'TOOL', status, payload, metadata)")
writer.log_step(
    agent_id="executor_01",
    step_type="TOOL",
    status="OK",
    payload={
        "tool_name": "python_exec",
        "input_summary": "SWMM 시뮬레이션 스크립트",
        "output_summary": "침수 깊이 래스터 생성"
    },
    metadata={
        "latency_ms": 185000
    }
)
print("    ✅ TOOL step logged")

# 9. register_artifact(artifact_id, artifact_type, path, created_by)
print("\n[9] register_artifact(artifact_id, artifact_type, path, created_by)")
writer.register_artifact(
    artifact_id="flood_depth_map",
    artifact_type="raster",
    path="outputs/maps/flood_depth.tif",
    created_by="executor_01"
)
print("    ✅ Artifact registered")

writer.log_step("executor_01", "OUTPUT", "OK", {
    "output_keys": ["flood_depth"],
    "artifact_ids": ["flood_depth_map"]
})

writer.end_agent("executor_01", "COMPLETED")
print("    ✅ executor_01 completed")

# 10. Error test
print("\n[10] log_error(agent_id, step_id, error_type, message, recoverable)")
writer.start_agent("failed_agent", "executor", "실패 테스트")
writer.log_step("failed_agent", "INPUT", "OK", {"context": [], "previous_results": []})
writer.log_step("failed_agent", "TOOL", "ERROR",
    payload={"tool_name": "bad_tool", "input_summary": "실패할 작업", "error": "Tool execution failed"},
    metadata={"latency_ms": 100}
)
writer.log_error(
    agent_id="failed_agent",
    step_id="failed_agent.tool_bad_tool",
    error_type="TOOL_ERROR",
    message="Tool execution failed: bad_tool",
    recoverable=False
)
writer.end_agent("failed_agent", "FAILED")
print("    ✅ Error logged")

# 11. end_run(status)
print("\n[11] end_run(status)")
writer.end_run("COMPLETED")
print("    ✅ Run ended")

# 결과 확인
trace = writer.get_trace()

print("\n" + "=" * 60)
print("  Results")
print("=" * 60)

print(f"\n📊 Summary:")
summary = trace["summary"]
print(f"   Total Agents:  {summary['total_agents']}")
print(f"   Completed:     {summary['completed_agents']}")
print(f"   Failed:        {summary['failed_agents']}")
print(f"   LLM Calls:     {summary['total_llm_calls']}")
print(f"   Tool Calls:    {summary['total_tool_calls']}")
print(f"   Total Tokens:  {summary['total_tokens']}")

print(f"\n👥 Agents:")
for agent in trace["agents"]:
    steps = [s["type"] for s in agent["steps"]]
    print(f"   {agent['agent_id']}: {agent['status']} [{', '.join(steps)}]")

print(f"\n📁 Artifacts:")
for artifact in trace["artifacts"]:
    print(f"   {artifact['artifact_id']}: {artifact['type']}")

print(f"\n❌ Errors:")
for error in trace["errors"]:
    print(f"   {error['agent_id']}/{error['step_id']}: {error['message']}")

# JSON 출력
trace_path = writer.get_trace_path()
print(f"\n📄 Trace saved: {trace_path}")

shutil.rmtree(temp_dir, ignore_errors=True)

print("\n" + "=" * 60)
print("  ✅ All API contract tests passed!")
print("=" * 60)
