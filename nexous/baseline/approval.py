"""
NEXOUS Baseline Approval

approval.json 생성 및 검증
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional


class Approval:
    """Baseline 승인 메타데이터"""
    
    SCHEMA_VERSION = "1.0"
    
    def __init__(
        self,
        project: str,
        approved_by: str,
        reason: str,
        engine_version: str = "nexous:latest",
        lock: bool = True
    ):
        self.baseline = True
        self.project = project
        self.approved_by = approved_by
        self.approved_at = datetime.now(timezone.utc).isoformat()
        self.reason = reason
        self.engine_version = engine_version
        self.lock = lock
        self.schema_version = self.SCHEMA_VERSION
    
    def to_dict(self) -> Dict[str, Any]:
        """Dictionary로 변환"""
        return {
            "baseline": self.baseline,
            "project": self.project,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "reason": self.reason,
            "engine_version": self.engine_version,
            "lock": self.lock,
            "schema_version": self.schema_version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Approval':
        """Dictionary에서 생성"""
        approval = cls(
            project=data['project'],
            approved_by=data['approved_by'],
            reason=data['reason'],
            engine_version=data.get('engine_version', 'nexous:latest'),
            lock=data.get('lock', True)
        )
        approval.approved_at = data['approved_at']
        return approval
    
    @classmethod
    def load(cls, approval_path: Path) -> 'Approval':
        """파일에서 로드"""
        with open(approval_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def save(self, approval_path: Path):
        """파일로 저장"""
        with open(approval_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        
        # Read-only로 설정
        os.chmod(approval_path, 0o444)
    
    def verify(self) -> tuple[bool, Optional[str]]:
        """승인 유효성 검증"""
        if not self.baseline:
            return False, "baseline field is not True"
        
        if not self.lock:
            return False, "lock field is not True"
        
        if not self.project:
            return False, "project field is empty"
        
        if not self.approved_by:
            return False, "approved_by field is empty"
        
        return True, None


def approve_baseline(
    trace_dir: Path,
    project: str,
    approved_by: str,
    reason: str,
    engine_version: str = "nexous:latest"
) -> Path:
    """
    Baseline 승인
    
    Args:
        trace_dir: Trace 디렉토리 경로
        project: 프로젝트 이름
        approved_by: 승인자
        reason: 승인 이유
        engine_version: 엔진 버전
    
    Returns:
        approval.json 경로
    """
    # approval.json 생성
    approval = Approval(
        project=project,
        approved_by=approved_by,
        reason=reason,
        engine_version=engine_version,
        lock=True
    )
    
    approval_path = trace_dir / "approval.json"
    approval.save(approval_path)
    
    # 디렉토리 Read-only 설정
    try:
        # 디렉토리 권한: r-xr-xr-x (555)
        os.chmod(trace_dir, 0o555)
    except Exception as e:
        print(f"Warning: Could not set directory read-only: {e}")
    
    return approval_path


def verify_baseline(trace_dir: Path) -> tuple[bool, list[str]]:
    """
    Baseline 검증
    
    Args:
        trace_dir: Trace 디렉토리 경로
    
    Returns:
        (성공 여부, 오류 메시지 리스트)
    """
    errors = []
    
    # trace.json 존재 확인
    trace_path = trace_dir / "trace.json"
    if not trace_path.exists():
        errors.append(f"trace.json not found: {trace_path}")
    
    # approval.json 존재 확인
    approval_path = trace_dir / "approval.json"
    if not approval_path.exists():
        errors.append(f"approval.json not found: {approval_path}")
        return False, errors
    
    # approval.json 검증
    try:
        approval = Approval.load(approval_path)
        valid, error = approval.verify()
        if not valid:
            errors.append(f"approval.json invalid: {error}")
    except Exception as e:
        errors.append(f"approval.json load error: {e}")
    
    # Read-only 확인
    try:
        # 파일이 쓰기 가능하면 경고
        if os.access(approval_path, os.W_OK):
            errors.append("approval.json is not read-only")
    except Exception:
        pass
    
    return len(errors) == 0, errors
