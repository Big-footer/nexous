#!/usr/bin/env python
"""
TraceStore 테스트 스크립트
"""

import sys
from pathlib import Path
from datetime import datetime
import json
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent))

from trace_store import (
    TraceStore,
    TraceDocument,
    AgentTrace,
    TraceStep,
    TraceSummary,
    TraceEvent,
    RunStatus,
    StepType,
    EventType
)


def test_trace_store():
    """TraceStore 기본 테스트"""
    print("\n" + "=" * 60)
    print("  TraceStore Test")
    print("=" * 60)
    
    # 임시 디렉토리 생성
    temp_dir = Path(tempfile.mkdtemp())
    print(f"\nTemp dir: {temp_dir}")
    
    try:
        store = TraceStore(temp_dir)
        
        # 1. Run 시작
        print("\n[1] Starting run...")
        run_id = "test_run_001"
        project_id = "test_project"
        
        agents_config = [
            {"id": "planner", "preset": "core/planner", "purpose": "계획 수립"},
            {"id": "executor", "preset": "core/executor", "purpose": "실행"},
        ]
        
        trace = store.start_run(
            run_id=run_id,
            project_id=project_id,
            project_name="Test Project",
            agents_config=agents_config
        )
        
        print(f"  Run started: {trace.run_id}")
        print(f"  Status: {trace.status}")
        print(f"  Agents: {[a.agent_id for a in trace.agents]}")
        
        # 2. Agent 시작
        print("\n[2] Starting agent...")
        store.start_agent(run_id, project_id, "planner")
        
        # 3. Step 추가
        print("\n[3] Adding steps...")
        step1 = TraceStep(
            step_id="planner_llm_001",
            agent_id="planner",
            step_type=StepType.LLM,
            status="RUNNING",
            started_at=datetime.now().isoformat(),
            model="gpt-4o"
        )
        store.add_step(run_id, project_id, step1)
        
        # Step 완료
        step1.status = "COMPLETED"
        step1.finished_at = datetime.now().isoformat()
        step1.latency_ms = 2000
        step1.tokens = 1500
        step1.output_summary = "Plan generated"
        store.add_step(run_id, project_id, step1)
        
        # 4. Agent 완료
        print("\n[4] Completing agent...")
        store.complete_agent(run_id, project_id, "planner", "COMPLETED")
        
        # 5. Run 완료
        print("\n[5] Completing run...")
        final_trace = store.complete_run(run_id, project_id, RunStatus.COMPLETED)
        
        print(f"  Status: {final_trace.status}")
        print(f"  Duration: {final_trace.duration_ms}ms")
        print(f"  Summary: {final_trace.summary.to_dict()}")
        
        # 6. 파일 확인
        print("\n[6] Checking files...")
        trace_path = temp_dir / project_id / run_id / "trace.json"
        events_path = temp_dir / project_id / run_id / "events.jsonl"
        
        print(f"  trace.json exists: {trace_path.exists()}")
        print(f"  events.jsonl exists: {events_path.exists()}")
        
        # trace.json 내용
        with open(trace_path, 'r') as f:
            trace_data = json.load(f)
        print(f"\n  trace.json content:")
        print(f"    run_id: {trace_data['run_id']}")
        print(f"    status: {trace_data['status']}")
        print(f"    agents: {len(trace_data['agents'])}")
        
        # events.jsonl 내용
        with open(events_path, 'r') as f:
            events = [json.loads(line) for line in f if line.strip()]
        print(f"\n  events.jsonl content:")
        print(f"    total events: {len(events)}")
        for event in events[:5]:
            print(f"    - {event['type']}: {event.get('agent_id', 'system')}")
        
        # 7. 조회 테스트
        print("\n[7] Testing retrieval...")
        loaded_trace = store.get_trace(project_id, run_id)
        print(f"  Loaded trace: {loaded_trace.run_id}")
        print(f"  Loaded agents: {[a.agent_id for a in loaded_trace.agents]}")
        
        loaded_events = store.get_events(project_id, run_id, limit=10)
        print(f"  Loaded events: {len(loaded_events)}")
        
        print("\n" + "=" * 60)
        print("  ✓ All TraceStore tests passed!")
        print("=" * 60)
        
    finally:
        # 정리
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_trace_files():
    """실제 traces 디렉토리 확인"""
    print("\n" + "=" * 60)
    print("  Checking traces directory")
    print("=" * 60)
    
    traces_dir = Path(__file__).parent.parent.parent / "traces"
    print(f"\nTraces dir: {traces_dir}")
    print(f"Exists: {traces_dir.exists()}")
    
    if traces_dir.exists():
        for project_dir in traces_dir.iterdir():
            if project_dir.is_dir():
                print(f"\nProject: {project_dir.name}")
                for run_dir in project_dir.iterdir():
                    if run_dir.is_dir():
                        trace_file = run_dir / "trace.json"
                        events_file = run_dir / "events.jsonl"
                        print(f"  Run: {run_dir.name}")
                        print(f"    trace.json: {trace_file.exists()}")
                        print(f"    events.jsonl: {events_file.exists()}")


if __name__ == "__main__":
    test_trace_store()
    test_trace_files()
