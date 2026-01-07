"""
Trace Diff Module

두 Trace 파일의 차이점을 분석합니다.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime


class TraceDiff:
    """두 Trace 파일을 비교하는 클래스"""
    
    def __init__(self, trace1_path: str, trace2_path: str):
        self.trace1_path = Path(trace1_path)
        self.trace2_path = Path(trace2_path)
        self.trace1: Dict[str, Any] = {}
        self.trace2: Dict[str, Any] = {}
        self.differences: List[Dict[str, Any]] = []
        
    def load_traces(self):
        """두 Trace 파일 로드"""
        with open(self.trace1_path, 'r', encoding='utf-8') as f:
            self.trace1 = json.load(f)
        
        with open(self.trace2_path, 'r', encoding='utf-8') as f:
            self.trace2 = json.load(f)
    
    def compare_metadata(self) -> Dict[str, Any]:
        """메타데이터 비교"""
        return {
            'project_id': {
                'trace1': self.trace1.get('project_id'),
                'trace2': self.trace2.get('project_id'),
                'same': self.trace1.get('project_id') == self.trace2.get('project_id')
            },
            'status': {
                'trace1': self.trace1.get('status'),
                'trace2': self.trace2.get('status'),
                'same': self.trace1.get('status') == self.trace2.get('status')
            },
            'duration_ms': {
                'trace1': self.trace1.get('duration_ms'),
                'trace2': self.trace2.get('duration_ms'),
                'diff': abs(self.trace1.get('duration_ms', 0) - self.trace2.get('duration_ms', 0))
            }
        }
    
    def compare_agents(self) -> List[Dict[str, Any]]:
        """Agent 비교"""
        agents1 = {a['agent_id']: a for a in self.trace1.get('agents', [])}
        agents2 = {a['agent_id']: a for a in self.trace2.get('agents', [])}
        
        differences = []
        
        # 공통 Agent 비교
        for agent_id in agents1.keys():
            if agent_id in agents2:
                agent1 = agents1[agent_id]
                agent2 = agents2[agent_id]
                
                if agent1.get('status') != agent2.get('status'):
                    differences.append({
                        'agent_id': agent_id,
                        'type': 'STATUS_DIFF',
                        'trace1_status': agent1.get('status'),
                        'trace2_status': agent2.get('status')
                    })
                
                # Steps 개수 비교
                steps1_count = len(agent1.get('steps', []))
                steps2_count = len(agent2.get('steps', []))
                if steps1_count != steps2_count:
                    differences.append({
                        'agent_id': agent_id,
                        'type': 'STEPS_COUNT_DIFF',
                        'trace1_count': steps1_count,
                        'trace2_count': steps2_count
                    })
            else:
                differences.append({
                    'agent_id': agent_id,
                    'type': 'MISSING_IN_TRACE2'
                })
        
        # Trace2에만 있는 Agent
        for agent_id in agents2.keys():
            if agent_id not in agents1:
                differences.append({
                    'agent_id': agent_id,
                    'type': 'MISSING_IN_TRACE1'
                })
        
        return differences
    
    def compare_errors(self) -> Dict[str, Any]:
        """에러 비교"""
        errors1 = self.trace1.get('errors', [])
        errors2 = self.trace2.get('errors', [])
        
        return {
            'trace1_errors': len(errors1),
            'trace2_errors': len(errors2),
            'same_count': len(errors1) == len(errors2),
            'errors1': errors1,
            'errors2': errors2
        }
    
    def compare_summary(self) -> Dict[str, Any]:
        """Summary 비교"""
        sum1 = self.trace1.get('summary', {})
        sum2 = self.trace2.get('summary', {})
        
        return {
            'total_agents': {
                'trace1': sum1.get('total_agents'),
                'trace2': sum2.get('total_agents'),
                'same': sum1.get('total_agents') == sum2.get('total_agents')
            },
            'completed_agents': {
                'trace1': sum1.get('completed_agents'),
                'trace2': sum2.get('completed_agents'),
                'same': sum1.get('completed_agents') == sum2.get('completed_agents')
            },
            'failed_agents': {
                'trace1': sum1.get('failed_agents'),
                'trace2': sum2.get('failed_agents'),
                'same': sum1.get('failed_agents') == sum2.get('failed_agents')
            },
            'total_duration_ms': {
                'trace1': sum1.get('total_duration_ms'),
                'trace2': sum2.get('total_duration_ms'),
                'diff': abs(sum1.get('total_duration_ms', 0) - sum2.get('total_duration_ms', 0))
            }
        }
    
    def diff(self) -> Dict[str, Any]:
        """전체 Diff 실행"""
        if not self.trace1 or not self.trace2:
            self.load_traces()
        
        print(f"\n🔍 Comparing Traces:")
        print(f"   Trace 1: {self.trace1.get('run_id')}")
        print(f"   Trace 2: {self.trace2.get('run_id')}\n")
        
        # 메타데이터 비교
        metadata_diff = self.compare_metadata()
        print("📋 Metadata:")
        for key, value in metadata_diff.items():
            if isinstance(value, dict):
                if 'same' in value:
                    status = "✅" if value['same'] else "❌"
                    print(f"   {key}: {status}")
                    if not value['same']:
                        print(f"      Trace1: {value.get('trace1')}")
                        print(f"      Trace2: {value.get('trace2')}")
                elif 'diff' in value:
                    print(f"   {key}:")
                    print(f"      Trace1: {value.get('trace1')}")
                    print(f"      Trace2: {value.get('trace2')}")
                    print(f"      Diff: {value.get('diff')}")
        
        # Agent 비교
        agent_diffs = self.compare_agents()
        if agent_diffs:
            print(f"\n🤖 Agent Differences ({len(agent_diffs)}):")
            for diff in agent_diffs:
                print(f"   - {diff.get('agent_id')}: {diff.get('type')}")
                if 'trace1_status' in diff:
                    print(f"      Trace1: {diff.get('trace1_status')}")
                    print(f"      Trace2: {diff.get('trace2_status')}")
        else:
            print("\n🤖 Agents: ✅ All same")
        
        # 에러 비교
        error_diff = self.compare_errors()
        print(f"\n❌ Errors:")
        print(f"   Trace1: {error_diff.get('trace1_errors')}")
        print(f"   Trace2: {error_diff.get('trace2_errors')}")
        if error_diff.get('same_count'):
            print("   Status: ✅ Same count")
        else:
            print("   Status: ❌ Different count")
        
        # Summary 비교
        summary_diff = self.compare_summary()
        print(f"\n📊 Summary:")
        for key, value in summary_diff.items():
            status = "✅" if value.get('same') else "❌"
            print(f"   {key}: {status}")
            if not value.get('same'):
                print(f"      Trace1: {value.get('trace1')}")
                print(f"      Trace2: {value.get('trace2')}")
        
        return {
            'metadata': metadata_diff,
            'agents': agent_diffs,
            'errors': error_diff,
            'summary': summary_diff
        }


def diff_traces(trace1_path: str, trace2_path: str) -> Dict[str, Any]:
    """두 Trace 파일 비교 (편의 함수)"""
    differ = TraceDiff(trace1_path, trace2_path)
    return differ.diff()
