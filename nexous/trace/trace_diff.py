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
    
    def __init__(self, trace1_path: str, trace2_path: str, only: str = None, show: str = None):
        self.trace1_path = Path(trace1_path)
        self.trace2_path = Path(trace2_path)
        self.trace1: Dict[str, Any] = {}
        self.trace2: Dict[str, Any] = {}
        self.differences: List[Dict[str, Any]] = []
        self.only = only  # 'llm', 'tools', 'errors', None
        self.show = show  # 'first', 'all', None
        
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
    
    def find_first_divergence(self) -> Dict[str, Any]:
        """첫 번째 차이점 찾기"""
        agents1 = self.trace1.get('agents', [])
        agents2 = self.trace2.get('agents', [])
        
        # Agent 순서대로 비교
        max_agents = max(len(agents1), len(agents2))
        
        for i in range(max_agents):
            # Agent 존재 여부
            if i >= len(agents1):
                return {
                    'type': 'AGENT_MISSING',
                    'location': f"Agent #{i+1}",
                    'agent_id': agents2[i].get('agent_id'),
                    'message': f"Trace1에 Agent가 없음 (Trace2: {agents2[i].get('agent_id')})"
                }
            
            if i >= len(agents2):
                return {
                    'type': 'AGENT_MISSING',
                    'location': f"Agent #{i+1}",
                    'agent_id': agents1[i].get('agent_id'),
                    'message': f"Trace2에 Agent가 없음 (Trace1: {agents1[i].get('agent_id')})"
                }
            
            agent1 = agents1[i]
            agent2 = agents2[i]
            
            # Agent ID 차이
            if agent1.get('agent_id') != agent2.get('agent_id'):
                return {
                    'type': 'AGENT_ID_DIFF',
                    'location': f"Agent #{i+1}",
                    'trace1_agent': agent1.get('agent_id'),
                    'trace2_agent': agent2.get('agent_id'),
                    'message': f"Agent ID 차이: {agent1.get('agent_id')} vs {agent2.get('agent_id')}"
                }
            
            # Status 차이
            if agent1.get('status') != agent2.get('status'):
                return {
                    'type': 'STATUS_DIFF',
                    'location': f"Agent #{i+1}: {agent1.get('agent_id')}",
                    'trace1_status': agent1.get('status'),
                    'trace2_status': agent2.get('status'),
                    'message': f"Status 차이: {agent1.get('status')} vs {agent2.get('status')}"
                }
            
            # Steps 비교
            steps1 = agent1.get('steps', [])
            steps2 = agent2.get('steps', [])
            
            if len(steps1) != len(steps2):
                return {
                    'type': 'STEPS_COUNT_DIFF',
                    'location': f"Agent #{i+1}: {agent1.get('agent_id')}",
                    'trace1_count': len(steps1),
                    'trace2_count': len(steps2),
                    'message': f"Steps 개수 차이: {len(steps1)} vs {len(steps2)}"
                }
            
            # 각 Step 비교
            for j in range(len(steps1)):
                step1 = steps1[j]
                step2 = steps2[j]
                
                if step1.get('type') != step2.get('type'):
                    return {
                        'type': 'STEP_TYPE_DIFF',
                        'location': f"Agent #{i+1}: {agent1.get('agent_id')}, Step #{j+1}",
                        'trace1_type': step1.get('type'),
                        'trace2_type': step2.get('type'),
                        'message': f"Step type 차이: {step1.get('type')} vs {step2.get('type')}"
                    }
                
                if step1.get('status') != step2.get('status'):
                    return {
                        'type': 'STEP_STATUS_DIFF',
                        'location': f"Agent #{i+1}: {agent1.get('agent_id')}, Step #{j+1} ({step1.get('type')})",
                        'trace1_status': step1.get('status'),
                        'trace2_status': step2.get('status'),
                        'message': f"Step status 차이: {step1.get('status')} vs {step2.get('status')}"
                    }
        
        # 차이점 없음
        return None
    
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
    
    def compare_llm_calls(self) -> Dict[str, Any]:
        """LLM 호출 비교"""
        llm_calls_1 = []
        llm_calls_2 = []
        
        # Trace1에서 LLM calls 추출
        for agent in self.trace1.get('agents', []):
            for step in agent.get('steps', []):
                if step.get('type') == 'LLM':
                    llm_calls_1.append({
                        'agent_id': agent.get('agent_id'),
                        'provider': step.get('provider'),
                        'model': step.get('model'),
                        'latency_ms': step.get('latency_ms'),
                        'tokens': step.get('tokens', {}),
                        'step_id': step.get('step_id')
                    })
        
        # Trace2에서 LLM calls 추출
        for agent in self.trace2.get('agents', []):
            for step in agent.get('steps', []):
                if step.get('type') == 'LLM':
                    llm_calls_2.append({
                        'agent_id': agent.get('agent_id'),
                        'provider': step.get('provider'),
                        'model': step.get('model'),
                        'latency_ms': step.get('latency_ms'),
                        'tokens': step.get('tokens', {}),
                        'step_id': step.get('step_id')
                    })
        
        # 총 토큰 계산
        total_tokens_1 = sum(call.get('tokens', {}).get('total', 0) for call in llm_calls_1)
        total_tokens_2 = sum(call.get('tokens', {}).get('total', 0) for call in llm_calls_2)
        
        # 총 latency 계산
        total_latency_1 = sum(call.get('latency_ms', 0) for call in llm_calls_1)
        total_latency_2 = sum(call.get('latency_ms', 0) for call in llm_calls_2)
        
        return {
            'trace1_calls': llm_calls_1,
            'trace2_calls': llm_calls_2,
            'trace1_count': len(llm_calls_1),
            'trace2_count': len(llm_calls_2),
            'trace1_tokens': total_tokens_1,
            'trace2_tokens': total_tokens_2,
            'trace1_latency': total_latency_1,
            'trace2_latency': total_latency_2,
            'same_count': len(llm_calls_1) == len(llm_calls_2)
        }
    
    def compare_tool_calls(self) -> Dict[str, Any]:
        """Tool 호출 비교"""
        tool_calls_1 = []
        tool_calls_2 = []
        
        # Trace1에서 Tool calls 추출
        for agent in self.trace1.get('agents', []):
            for step in agent.get('steps', []):
                if step.get('type') == 'TOOL':
                    tool_calls_1.append({
                        'agent_id': agent.get('agent_id'),
                        'tool_name': step.get('tool_name'),
                        'status': step.get('status'),
                        'started_at': step.get('started_at'),
                        'ended_at': step.get('ended_at'),
                        'step_id': step.get('step_id'),
                        'input_summary': step.get('input_summary', ''),
                        'output_summary': step.get('output_summary', '')
                    })
        
        # Trace2에서 Tool calls 추출
        for agent in self.trace2.get('agents', []):
            for step in agent.get('steps', []):
                if step.get('type') == 'TOOL':
                    tool_calls_2.append({
                        'agent_id': agent.get('agent_id'),
                        'tool_name': step.get('tool_name'),
                        'status': step.get('status'),
                        'started_at': step.get('started_at'),
                        'ended_at': step.get('ended_at'),
                        'step_id': step.get('step_id'),
                        'input_summary': step.get('input_summary', ''),
                        'output_summary': step.get('output_summary', '')
                    })
        
        return {
            'trace1_calls': tool_calls_1,
            'trace2_calls': tool_calls_2,
            'trace1_count': len(tool_calls_1),
            'trace2_count': len(tool_calls_2),
            'same_count': len(tool_calls_1) == len(tool_calls_2)
        }
    
    def diff(self) -> Dict[str, Any]:
        """전체 Diff 실행"""
        if not self.trace1 or not self.trace2:
            self.load_traces()
        
        print(f"\n🔍 Comparing Traces:")
        print(f"   Trace 1: {self.trace1.get('run_id')}")
        print(f"   Trace 2: {self.trace2.get('run_id')}")
        
        if self.only:
            print(f"   Filter: --only {self.only}")
        if self.show:
            print(f"   Show: --show {self.show}")
        print()
        
        # --show first: 첫 divergence만 표시
        if self.show == 'first':
            first_div = self.find_first_divergence()
            
            if first_div:
                print("🎯 First Divergence Found:")
                print(f"   Type: {first_div['type']}")
                print(f"   Location: {first_div['location']}")
                print(f"   Message: {first_div['message']}")
                print()
                
                # 상세 정보
                if 'trace1_status' in first_div:
                    print(f"   Trace1: {first_div['trace1_status']}")
                    print(f"   Trace2: {first_div['trace2_status']}")
                elif 'trace1_agent' in first_div:
                    print(f"   Trace1: {first_div['trace1_agent']}")
                    print(f"   Trace2: {first_div['trace2_agent']}")
                elif 'trace1_count' in first_div:
                    print(f"   Trace1: {first_div['trace1_count']} steps")
                    print(f"   Trace2: {first_div['trace2_count']} steps")
                elif 'trace1_type' in first_div:
                    print(f"   Trace1: {first_div['trace1_type']}")
                    print(f"   Trace2: {first_div['trace2_type']}")
            else:
                print("✅ No Divergence: Traces are identical!")
            
            return {'first_divergence': first_div}
        
        # --only llm 필터
        if self.only == 'llm':
            llm_diff = self.compare_llm_calls()
            
            print("🤖 LLM Calls:")
            print(f"   Trace1: {llm_diff['trace1_count']} calls")
            print(f"   Trace2: {llm_diff['trace2_count']} calls")
            
            if llm_diff['same_count']:
                print("   Status: ✅ Same count")
            else:
                print("   Status: ❌ Different count")
            
            print(f"\n📊 Tokens:")
            print(f"   Trace1: {llm_diff['trace1_tokens']:,}")
            print(f"   Trace2: {llm_diff['trace2_tokens']:,}")
            if llm_diff['trace1_tokens'] != llm_diff['trace2_tokens']:
                diff = llm_diff['trace2_tokens'] - llm_diff['trace1_tokens']
                print(f"   Diff: {diff:+,}")
            
            print(f"\n⏱️  Latency:")
            print(f"   Trace1: {llm_diff['trace1_latency']:,}ms")
            print(f"   Trace2: {llm_diff['trace2_latency']:,}ms")
            if llm_diff['trace1_latency'] != llm_diff['trace2_latency']:
                diff = llm_diff['trace2_latency'] - llm_diff['trace1_latency']
                pct = (diff / llm_diff['trace1_latency'] * 100) if llm_diff['trace1_latency'] > 0 else 0
                print(f"   Diff: {diff:+,}ms ({pct:+.1f}%)")
            
            # 각 LLM call 상세
            if llm_diff['trace1_calls'] or llm_diff['trace2_calls']:
                print(f"\n📋 LLM Call Details:")
                
                max_calls = max(len(llm_diff['trace1_calls']), len(llm_diff['trace2_calls']))
                for i in range(max_calls):
                    print(f"\n   Call #{i+1}:")
                    
                    if i < len(llm_diff['trace1_calls']):
                        call1 = llm_diff['trace1_calls'][i]
                        print(f"      Trace1: {call1['agent_id']}")
                        print(f"         Model: {call1['provider']}/{call1['model']}")
                        print(f"         Tokens: {call1['tokens'].get('total', 0)}")
                        print(f"         Latency: {call1['latency_ms']}ms")
                    else:
                        print(f"      Trace1: (no call)")
                    
                    if i < len(llm_diff['trace2_calls']):
                        call2 = llm_diff['trace2_calls'][i]
                        print(f"      Trace2: {call2['agent_id']}")
                        print(f"         Model: {call2['provider']}/{call2['model']}")
                        print(f"         Tokens: {call2['tokens'].get('total', 0)}")
                        print(f"         Latency: {call2['latency_ms']}ms")
                    else:
                        print(f"      Trace2: (no call)")
            
            return {'llm': llm_diff}
        
        # --only tool 필터
        if self.only == 'tool' or self.only == 'tools':
            tool_diff = self.compare_tool_calls()
            
            print("🔧 Tool Calls:")
            print(f"   Trace1: {tool_diff['trace1_count']} calls")
            print(f"   Trace2: {tool_diff['trace2_count']} calls")
            
            if tool_diff['same_count']:
                print("   Status: ✅ Same count")
            else:
                print("   Status: ❌ Different count")
            
            # 각 Tool call 상세
            if tool_diff['trace1_calls'] or tool_diff['trace2_calls']:
                print(f"\n📋 Tool Call Details:")
                
                max_calls = max(len(tool_diff['trace1_calls']), len(tool_diff['trace2_calls']))
                for i in range(max_calls):
                    print(f"\n   Call #{i+1}:")
                    
                    if i < len(tool_diff['trace1_calls']):
                        call1 = tool_diff['trace1_calls'][i]
                        print(f"      Trace1: {call1['agent_id']}")
                        print(f"         Tool: {call1['tool_name']}")
                        print(f"         Status: {call1['status']}")
                        if call1.get('input_summary'):
                            print(f"         Input: {call1['input_summary'][:80]}...")
                        if call1.get('output_summary'):
                            print(f"         Output: {call1['output_summary'][:80]}...")
                    else:
                        print(f"      Trace1: (no call)")
                    
                    if i < len(tool_diff['trace2_calls']):
                        call2 = tool_diff['trace2_calls'][i]
                        print(f"      Trace2: {call2['agent_id']}")
                        print(f"         Tool: {call2['tool_name']}")
                        print(f"         Status: {call2['status']}")
                        if call2.get('input_summary'):
                            print(f"         Input: {call2['input_summary'][:80]}...")
                        if call2.get('output_summary'):
                            print(f"         Output: {call2['output_summary'][:80]}...")
                    else:
                        print(f"      Trace2: (no call)")
            
            return {'tool': tool_diff}
        
        # 전체 비교 (기존 코드)
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


def diff_traces(trace1_path: str, trace2_path: str, only: str = None, show: str = None) -> Dict[str, Any]:
    """두 Trace 파일 비교 (편의 함수)"""
    differ = TraceDiff(trace1_path, trace2_path, only=only, show=show)
    return differ.diff()
