"""
NEXOUS API - Replay Result Formatter

Replay 결과를 GUI 친화적 JSON으로 변환
"""

from typing import Dict, Any, List, Optional
import json
from pathlib import Path


class ReplayResultFormatter:
    """Replay 결과를 API 응답 형식으로 변환"""
    
    @staticmethod
    def format_for_api(
        trace_path: str,
        mode: str = "dry",
        report_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Replay 결과를 STEP 4A-2 스펙에 맞게 변환
        
        Args:
            trace_path: Trace 파일 경로
            mode: Replay 모드 (dry/full)
            report_text: 텍스트 리포트
        
        Returns:
            API 응답 형식의 딕셔너리
        """
        # Trace 로드
        with open(trace_path, 'r', encoding='utf-8') as f:
            trace = json.load(f)
        
        # Timeline 생성
        timeline = ReplayResultFormatter._build_timeline(trace)
        
        # Summary 생성
        summary = ReplayResultFormatter._build_summary(trace, timeline)
        
        return {
            'ok': True,
            'mode': mode,
            'summary': summary,
            'timeline': timeline,
            'report': report_text or ''
        }
    
    @staticmethod
    def _build_timeline(trace: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Trace에서 타임라인 생성"""
        timeline = []
        step_index = 0
        
        # Start 이벤트
        timeline.append({
            'step_index': step_index,
            'type': 'SYSTEM',
            'label': 'Start Run',
            'duration_ms': 0
        })
        step_index += 1
        
        # Agent 실행 순서대로 처리
        for agent in trace.get('agents', []):
            agent_id = agent.get('agent_id', 'unknown')
            
            # Agent의 각 Step 처리
            for step in agent.get('steps', []):
                step_type = step.get('type', 'UNKNOWN')
                
                if step_type == 'LLM':
                    timeline.append({
                        'step_index': step_index,
                        'type': 'LLM',
                        'label': f"{agent_id} ({step.get('provider', 'unknown')}/{step.get('model', 'unknown')})",
                        'duration_ms': step.get('latency_ms', 0),
                        'meta': {
                            'agent_id': agent_id,
                            'provider': step.get('provider'),
                            'model': step.get('model'),
                            'attempt': 1,
                            'tokens': step.get('tokens', {}),
                            'status': step.get('status', 'OK')
                        }
                    })
                
                elif step_type == 'TOOL':
                    timeline.append({
                        'step_index': step_index,
                        'type': 'TOOL',
                        'label': step.get('tool_name', 'unknown_tool'),
                        'duration_ms': step.get('duration_ms', 0),
                        'meta': {
                            'agent_id': agent_id,
                            'tool_name': step.get('tool_name'),
                            'status': step.get('status', 'OK'),
                            'input_summary': step.get('input_summary', ''),
                            'output_summary': step.get('output_summary', '')
                        }
                    })
                
                elif step_type == 'INPUT' or step_type == 'OUTPUT':
                    # INPUT/OUTPUT은 타임라인에 표시 안 함 (내부 처리)
                    continue
                
                else:
                    # UNKNOWN 타입
                    timeline.append({
                        'step_index': step_index,
                        'type': step_type,
                        'label': f"{agent_id} ({step_type})",
                        'duration_ms': 0
                    })
                
                step_index += 1
            
            # Agent 실패 시 ERROR 추가
            if agent.get('status') == 'FAILED':
                errors = agent.get('errors', [])
                for error in errors:
                    timeline.append({
                        'step_index': step_index,
                        'type': 'ERROR',
                        'label': f"{agent_id} error",
                        'duration_ms': 0,
                        'meta': {
                            'agent_id': agent_id,
                            'error_type': error.get('type', 'UNKNOWN'),
                            'message': error.get('message', 'Unknown error')
                        }
                    })
                    step_index += 1
        
        # End 이벤트
        timeline.append({
            'step_index': step_index,
            'type': 'SYSTEM',
            'label': f"End Run ({trace.get('status', 'UNKNOWN')})",
            'duration_ms': 0
        })
        
        return timeline
    
    @staticmethod
    def _build_summary(trace: Dict[str, Any], timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summary 생성"""
        # Step 유형별 카운트
        llm_steps = sum(1 for item in timeline if item['type'] == 'LLM')
        tool_steps = sum(1 for item in timeline if item['type'] == 'TOOL')
        error_steps = sum(1 for item in timeline if item['type'] == 'ERROR')
        
        return {
            'total_steps': len(timeline),
            'llm_steps': llm_steps,
            'tool_steps': tool_steps,
            'error_steps': error_steps,
            'status': trace.get('status', 'UNKNOWN')
        }


def format_replay_for_gui(
    trace_path: str,
    mode: str = "dry",
    report_text: Optional[str] = None
) -> Dict[str, Any]:
    """편의 함수"""
    return ReplayResultFormatter.format_for_api(trace_path, mode, report_text)
