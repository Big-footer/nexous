"""
NEXOUS API - Diff Result Formatter

Diff 결과를 GUI 친화적 JSON으로 변환
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class DiffResultFormatter:
    """Diff 결과를 API 응답 형식으로 변환"""
    
    @staticmethod
    def format_for_api(
        baseline_run: str,
        target_run: str,
        diff_result: Dict[str, Any],
        report_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Diff 결과를 STEP 4A-1 스펙에 맞게 변환
        
        Args:
            baseline_run: Baseline run ID
            target_run: Target run ID
            diff_result: TraceDiff.diff() 결과
            report_text: 텍스트 리포트
        
        Returns:
            API 응답 형식의 딕셔너리
        """
        # First divergence 찾기
        first_divergence = None
        if 'first_divergence' in diff_result and diff_result['first_divergence']:
            div = diff_result['first_divergence']
            first_divergence = {
                'step_index': DiffResultFormatter._extract_step_index(div.get('location', '')),
                'step_type': DiffResultFormatter._extract_step_type(div.get('type', '')),
                'reason': div.get('message', 'unknown')
            }
        
        # Changes 추출
        changes = DiffResultFormatter._extract_changes(diff_result)
        
        # Counts 계산
        counts = {
            'llm': sum(1 for c in changes if c['type'] == 'LLM'),
            'tool': sum(1 for c in changes if c['type'] == 'TOOL'),
            'errors': sum(1 for c in changes if c['type'] == 'ERROR')
        }
        
        # Status 결정
        status = DiffResultFormatter._determine_status(diff_result, changes)
        
        return {
            'ok': True,
            'summary': {
                'baseline_run': baseline_run,
                'target_run': target_run,
                'status': status,
                'first_divergence': first_divergence,
                'counts': counts
            },
            'changes': changes,
            'report': report_text or ''
        }
    
    @staticmethod
    def _extract_step_index(location: str) -> int:
        """위치 문자열에서 step index 추출"""
        # "Agent #1, Step #3" -> 3
        import re
        match = re.search(r'Step #(\d+)', location)
        if match:
            return int(match.group(1))
        return 0
    
    @staticmethod
    def _extract_step_type(diff_type: str) -> str:
        """Diff 타입에서 step type 추출"""
        if 'LLM' in diff_type.upper():
            return 'LLM'
        elif 'TOOL' in diff_type.upper():
            return 'TOOL'
        elif 'ERROR' in diff_type.upper():
            return 'ERROR'
        return 'UNKNOWN'
    
    @staticmethod
    def _extract_changes(diff_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Diff 결과에서 changes 리스트 생성"""
        changes = []
        
        # LLM 변경 사항
        if 'llm' in diff_result:
            llm_diff = diff_result['llm']
            
            # Call count 차이
            if not llm_diff.get('same_count'):
                changes.append({
                    'step_index': 0,
                    'type': 'LLM',
                    'field': 'call_count',
                    'baseline_value': str(llm_diff.get('trace1_count', 0)),
                    'target_value': str(llm_diff.get('trace2_count', 0)),
                    'policy': None
                })
            
            # Token 차이
            if llm_diff.get('trace1_tokens') != llm_diff.get('trace2_tokens'):
                changes.append({
                    'step_index': 0,
                    'type': 'LLM',
                    'field': 'tokens',
                    'baseline_value': str(llm_diff.get('trace1_tokens', 0)),
                    'target_value': str(llm_diff.get('trace2_tokens', 0)),
                    'policy': None
                })
            
            # Latency 차이
            if llm_diff.get('trace1_latency') != llm_diff.get('trace2_latency'):
                changes.append({
                    'step_index': 0,
                    'type': 'LLM',
                    'field': 'latency',
                    'baseline_value': f"{llm_diff.get('trace1_latency', 0)}ms",
                    'target_value': f"{llm_diff.get('trace2_latency', 0)}ms",
                    'policy': None
                })
        
        # Tool 변경 사항
        if 'tool' in diff_result:
            tool_diff = diff_result['tool']
            
            if not tool_diff.get('same_count'):
                changes.append({
                    'step_index': 0,
                    'type': 'TOOL',
                    'field': 'call_count',
                    'baseline_value': str(tool_diff.get('trace1_count', 0)),
                    'target_value': str(tool_diff.get('trace2_count', 0)),
                    'policy': None
                })
        
        # Metadata 변경 사항
        if 'metadata' in diff_result:
            metadata = diff_result['metadata']
            
            if 'status' in metadata and not metadata['status'].get('same'):
                changes.append({
                    'step_index': 0,
                    'type': 'METADATA',
                    'field': 'status',
                    'baseline_value': metadata['status'].get('trace1', 'UNKNOWN'),
                    'target_value': metadata['status'].get('trace2', 'UNKNOWN'),
                    'policy': None
                })
        
        # Errors 변경 사항
        if 'errors' in diff_result:
            errors = diff_result['errors']
            
            if not errors.get('same_count'):
                changes.append({
                    'step_index': 0,
                    'type': 'ERROR',
                    'field': 'error_count',
                    'baseline_value': str(errors.get('trace1_errors', 0)),
                    'target_value': str(errors.get('trace2_errors', 0)),
                    'policy': None
                })
        
        return changes
    
    @staticmethod
    def _determine_status(diff_result: Dict[str, Any], changes: List[Dict[str, Any]]) -> str:
        """Diff 상태 결정"""
        # First divergence가 없으면 IDENTICAL
        if 'first_divergence' in diff_result:
            if diff_result['first_divergence'] is None:
                return 'IDENTICAL'
        
        # Changes가 없으면 IDENTICAL
        if not changes:
            return 'IDENTICAL'
        
        # Error 관련 변경이 있으면 FAILED
        has_errors = any(c['type'] == 'ERROR' for c in changes)
        if has_errors:
            return 'FAILED'
        
        # 그 외는 CHANGED
        return 'CHANGED'


def format_diff_for_gui(
    baseline_run: str,
    target_run: str,
    diff_result: Dict[str, Any],
    report_text: Optional[str] = None
) -> Dict[str, Any]:
    """편의 함수"""
    return DiffResultFormatter.format_for_api(
        baseline_run, target_run, diff_result, report_text
    )
