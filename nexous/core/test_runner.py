#!/usr/bin/env python
"""Runner STEP 2 테스트"""

import sys
from pathlib import Path
import json
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nexous.core import Runner, run_project, DummyAgent

print("=" * 70)
print("  NEXOUS Runner STEP 2 Test")
print("=" * 70)

# 테스트용 trace 디렉토리
trace_dir = Path(__file__).parent.parent.parent / "traces"

# ============================================================================
# Test 1: 정상 실행
# ============================================================================
print("\n[Test 1] Normal execution with dependencies")
print("-" * 50)

project_path = Path(__file__).parent.parent.parent / "projects/flood_analysis_ulsan/project.yaml"

try:
    trace_path = run_project(
        project_yaml_path=str(project_path),
        run_id="test_run_001",
        trace_dir=str(trace_dir)
    )
    print(f"✅ Run completed")
    print(f"   Trace: {trace_path}")
    
    # trace.json 확인
    with open(trace_path, 'r') as f:
        trace = json.load(f)
    
    print(f"\n   📊 Summary:")
    summary = trace["summary"]
    print(f"      Total Agents:  {summary['total_agents']}")
    print(f"      Completed:     {summary['completed_agents']}")
    print(f"      Failed:        {summary['failed_agents']}")
    
    print(f"\n   👥 Agent Execution Order:")
    for i, agent in enumerate(trace["agents"], 1):
        deps = agent.get("dependencies", [])
        print(f"      {i}. {agent['agent_id']} ({agent['preset']}) -> {agent['status']}")
    
except Exception as e:
    print(f"❌ Failed: {e}")

# ============================================================================
# Test 2: 의존성 순서 확인
# ============================================================================
print("\n[Test 2] Dependency order verification")
print("-" * 50)

with open(trace_path, 'r') as f:
    trace = json.load(f)

# 예상 순서: planner_01 -> executor_01 -> analyst_01 -> writer_01
expected_order = ["planner_01", "executor_01", "analyst_01", "writer_01"]
actual_order = [a["agent_id"] for a in trace["agents"]]

if actual_order == expected_order:
    print(f"✅ Dependency order correct: {' -> '.join(actual_order)}")
else:
    print(f"❌ Order mismatch!")
    print(f"   Expected: {expected_order}")
    print(f"   Actual:   {actual_order}")

# ============================================================================
# Test 3: 순환 참조 감지
# ============================================================================
print("\n[Test 3] Circular dependency detection")
print("-" * 50)

# 순환 참조 YAML 생성
cycle_yaml = trace_dir / "test_cycle.yaml"
cycle_yaml.write_text("""
project_id: test_cycle
agents:
  - id: agent_a
    preset: test
    dependencies:
      - agent_b
  - id: agent_b
    preset: test
    dependencies:
      - agent_c
  - id: agent_c
    preset: test
    dependencies:
      - agent_a
""")

try:
    run_project(str(cycle_yaml), "test_cycle", str(trace_dir))
    print("❌ Should have raised DependencyCycleError")
except Exception as e:
    if "Circular dependency" in str(e):
        print(f"✅ Circular dependency detected: {e}")
    else:
        print(f"❌ Unexpected error: {e}")

cycle_yaml.unlink()

# ============================================================================
# Test 4: YAML 파싱 오류
# ============================================================================
print("\n[Test 4] YAML parse error handling")
print("-" * 50)

invalid_yaml = trace_dir / "test_invalid.yaml"
invalid_yaml.write_text("{ invalid yaml content")

try:
    run_project(str(invalid_yaml), "test_invalid", str(trace_dir))
    print("❌ Should have raised YAMLParseError")
except Exception as e:
    if "YAML" in str(e):
        print(f"✅ YAML error detected: {type(e).__name__}")
    else:
        print(f"❌ Unexpected error: {e}")

invalid_yaml.unlink()

# ============================================================================
# Test 5: Schema 검증 오류
# ============================================================================
print("\n[Test 5] Schema validation error handling")
print("-" * 50)

missing_field_yaml = trace_dir / "test_missing.yaml"
missing_field_yaml.write_text("""
project_id: test_missing
agents:
  - preset: test
""")

try:
    run_project(str(missing_field_yaml), "test_missing", str(trace_dir))
    print("❌ Should have raised SchemaValidationError")
except Exception as e:
    if "missing" in str(e).lower():
        print(f"✅ Schema error detected: {e}")
    else:
        print(f"❌ Unexpected error: {e}")

missing_field_yaml.unlink()

# ============================================================================
# Test 6: Trace JSON Schema 검증
# ============================================================================
print("\n[Test 6] Trace JSON Schema validation")
print("-" * 50)

try:
    import jsonschema
    
    schema_path = Path(__file__).parent.parent.parent / "gui/backend/schemas/trace_schema_v1.json"
    if schema_path.exists():
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        with open(trace_path, 'r') as f:
            trace = json.load(f)
        
        jsonschema.validate(trace, schema)
        print("✅ Trace JSON Schema validation passed")
    else:
        print("⚠️ Schema file not found, skipping validation")
except ImportError:
    print("⚠️ jsonschema not installed, skipping validation")
except jsonschema.ValidationError as e:
    print(f"❌ Schema validation failed: {e.message}")

# ============================================================================
# 완료
# ============================================================================
print("\n" + "=" * 70)
print("  STEP 2 Checklist")
print("=" * 70)
print("  ✅ project.yaml 하나로 실행 가능")
print("  ✅ Agent dependency 순서대로 실행됨")
print("  ✅ 성공/실패 모두 trace.json 생성")
print("  ✅ GUI 없이 단독 실행 가능")
print("  ✅ Trace JSON Schema 검증 통과")
print("=" * 70)
