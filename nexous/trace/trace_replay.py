"""
Trace Replay Module

Trace 파일로부터 실행을 재현합니다.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class TraceReplay:
    """Trace 파일을 읽어서 실행을 재현하는 클래스"""
    
    def __init__(self, trace_path: str, mode: str = "dry"):
        self.trace_path = Path(trace_path)
        self.trace_data: Optional[Dict[str, Any]] = None
        self.mode = mode  # "dry" or "full"
        
    def load_trace(self) -> Dict[str, Any]:
        """Trace 파일 로드"""
        if not self.trace_path.exists():
            raise FileNotFoundError(f"Trace file not found: {self.trace_path}")
        
        with open(self.trace_path, 'r', encoding='utf-8') as f:
            self.trace_data = json.load(f)
        
        return self.trace_data
    
    def validate_trace(self) -> bool:
        """Trace 파일 검증"""
        if not self.trace_data:
            self.load_trace()
        
        required_fields = [
            'trace_version',
            'project_id',
            'run_id',
            'status',
            'agents',
            'summary'
        ]
        
        for field in required_fields:
            if field not in self.trace_data:
                raise ValueError(f"Missing required field: {field}")
        
        return True
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """실행 요약 정보 반환"""
        if not self.trace_data:
            self.load_trace()
        
        return {
            'project_id': self.trace_data.get('project_id'),
            'run_id': self.trace_data.get('run_id'),
            'status': self.trace_data.get('status'),
            'duration_ms': self.trace_data.get('duration_ms'),
            'started_at': self.trace_data.get('started_at'),
            'ended_at': self.trace_data.get('ended_at'),
            'summary': self.trace_data.get('summary')
        }
    
    def get_agent_timeline(self) -> list:
        """Agent 실행 타임라인 반환"""
        if not self.trace_data:
            self.load_trace()
        
        timeline = []
        for agent in self.trace_data.get('agents', []):
            timeline.append({
                'agent_id': agent.get('agent_id'),
                'preset': agent.get('preset'),
                'status': agent.get('status'),
                'started_at': agent.get('started_at'),
                'ended_at': agent.get('ended_at'),
                'steps': len(agent.get('steps', []))
            })
        
        return timeline
    
    def get_errors(self) -> list:
        """에러 정보 반환"""
        if not self.trace_data:
            self.load_trace()
        
        return self.trace_data.get('errors', [])
    
    def replay(self) -> Dict[str, Any]:
        """Trace 재현"""
        if not self.trace_data:
            self.load_trace()
        
        self.validate_trace()
        
        # 모드 표시
        mode_icon = "🎭" if self.mode == "dry" else "🔄"
        mode_text = "DRY RUN" if self.mode == "dry" else "FULL REPLAY"
        
        print(f"\n{mode_icon} {mode_text}: {self.trace_data.get('run_id')}")
        print(f"   Project: {self.trace_data.get('project_id')}")
        print(f"   Status: {self.trace_data.get('status')}")
        print(f"   Duration: {self.trace_data.get('duration_ms')}ms")
        print(f"   Mode: {self.mode.upper()}")
        
        if self.mode == "dry":
            print(f"   ℹ️  LLM/Tool 호출 없이 타임라인만 재생\n")
            # DRY 모드: 타임라인만 출력
            for agent in self.trace_data.get('agents', []):
                self._replay_agent(agent)
        else:
            print(f"   ⚠️  실제 LLM/Tool 호출 재실행\n")
            # FULL 모드: 실제 재실행
            return self._full_replay()
        
        # 에러 출력 (DRY 모드)
        errors = self.get_errors()
        if errors:
            print("\n❌ Errors:")
            for err in errors:
                print(f"   - {err.get('agent_id')}: {err.get('message')}")
        
        # 요약
        summary = self.trace_data.get('summary', {})
        print(f"\n📊 Summary:")
        print(f"   Total Agents: {summary.get('total_agents')}")
        print(f"   Completed: {summary.get('completed_agents')}")
        print(f"   Failed: {summary.get('failed_agents')}")
        print(f"   LLM Calls: {summary.get('total_llm_calls')}")
        print(f"   Duration: {summary.get('total_duration_ms')}ms")
        
        return self.trace_data
    
    def _replay_agent(self, agent: Dict[str, Any]):
        """Agent 실행 시뮬레이션"""
        agent_id = agent.get('agent_id')
        status = agent.get('status')
        
        # Status에 따른 아이콘
        status_icon = {
            'COMPLETED': '✅',
            'FAILED': '❌',
            'SKIPPED': '⏭️',
            'RUNNING': '▶️'
        }.get(status, '❓')
        
        print(f"{status_icon} {agent_id}")
        print(f"   Preset: {agent.get('preset')}")
        print(f"   Purpose: {agent.get('purpose')}")
        print(f"   Status: {status}")
        
        # Steps 출력
        steps = agent.get('steps', [])
        if steps:
            print(f"   Steps: {len(steps)}")
            for step in steps:
                step_type = step.get('type')
                step_status = step.get('status')
                print(f"      - {step_type}: {step_status}")
        
        print()
    
    def _full_replay(self) -> Dict[str, Any]:
        """FULL 모드: 실제 재실행"""
        import tempfile
        import yaml
        from pathlib import Path
        
        print("🔄 Reconstructing project from trace...")
        
        # Trace에서 프로젝트 정보 추출
        project_id = self.trace_data.get('project_id')
        agents = self.trace_data.get('agents', [])
        
        # 임시 프로젝트 파일 생성
        project_yaml = {
            'project_id': project_id,
            'name': f"Replay of {project_id}",
            'description': f"Full replay from trace: {self.trace_data.get('run_id')}",
            'execution': self.trace_data.get('execution', {'mode': 'sequential'}),
            'agents': [],
            'context': self.trace_data.get('context', {})
        }
        
        # Agents 정보 재구성
        for agent in agents:
            agent_config = {
                'id': agent.get('agent_id'),
                'preset': agent.get('preset'),
                'purpose': agent.get('purpose'),
            }
            
            # Inputs 재구성 (첫 INPUT step에서 추출)
            for step in agent.get('steps', []):
                if step.get('type') == 'INPUT':
                    payload = step.get('payload_summary', {})
                    context_keys = payload.get('context', [])
                    if context_keys:
                        agent_config['inputs'] = {k: f"{{{{ {k} }}}}" for k in context_keys}
                    break
            
            # Outputs (OUTPUT step에서 추출)
            for step in agent.get('steps', []):
                if step.get('type') == 'OUTPUT':
                    payload = step.get('payload_summary', {})
                    output_keys = payload.get('output_keys', [])
                    if output_keys:
                        agent_config['outputs'] = output_keys
                    break
            
            project_yaml['agents'].append(agent_config)
        
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(project_yaml, f)
            temp_project_path = f.name
        
        print(f"✅ Project reconstructed: {temp_project_path}")
        print(f"🚀 Running project with --use-llm...")
        
        # 새 run_id 생성
        from datetime import datetime
        new_run_id = f"replay_{self.trace_data.get('run_id')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Runner 호출
        try:
            from nexous.core.runner import run_project
            
            trace_path = run_project(
                project_yaml_path=temp_project_path,
                run_id=new_run_id,
                trace_dir='traces',
                use_llm=True  # FULL 모드는 항상 LLM 사용
            )
            
            print(f"\n✅ FULL Replay completed!")
            print(f"📊 New trace: {trace_path}")
            print(f"🆔 New run_id: {new_run_id}")
            
            # 임시 파일 삭제
            Path(temp_project_path).unlink(missing_ok=True)
            
            return {'status': 'completed', 'trace_path': trace_path, 'run_id': new_run_id}
            
        except Exception as e:
            print(f"\n❌ FULL Replay failed: {e}")
            Path(temp_project_path).unlink(missing_ok=True)
            raise


def replay_trace(trace_path: str, mode: str = "dry") -> Dict[str, Any]:
    """Trace 파일 재현 (편의 함수)"""
    replay = TraceReplay(trace_path, mode=mode)
    return replay.replay()
