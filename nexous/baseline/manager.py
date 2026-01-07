"""
NEXOUS Baseline Manager

baseline.yaml 관리 및 검증
"""

import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional


class BaselineConfig:
    """baseline.yaml 구조"""
    
    def __init__(
        self,
        project: str,
        baseline_run_id: str,
        trace_path: str,
        approved: bool = True,
        approved_at: Optional[str] = None,
        policy: Optional[Dict[str, Any]] = None
    ):
        self.project = project
        self.baseline_run_id = baseline_run_id
        self.trace_path = trace_path
        self.approved = approved
        self.approved_at = approved_at or datetime.now(timezone.utc).isoformat()
        self.policy = policy or {
            'diff_required': True,
            'replay_allowed': True,
            'overwrite_forbidden': True
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Dictionary로 변환"""
        return {
            'project': self.project,
            'baseline_run_id': self.baseline_run_id,
            'trace_path': self.trace_path,
            'approved': self.approved,
            'approved_at': self.approved_at,
            'policy': self.policy
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaselineConfig':
        """Dictionary에서 생성"""
        return cls(
            project=data['project'],
            baseline_run_id=data['baseline_run_id'],
            trace_path=data['trace_path'],
            approved=data.get('approved', True),
            approved_at=data.get('approved_at'),
            policy=data.get('policy')
        )
    
    @classmethod
    def load(cls, baseline_yaml_path: Path) -> 'BaselineConfig':
        """파일에서 로드"""
        with open(baseline_yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)
    
    def save(self, baseline_yaml_path: Path):
        """파일로 저장"""
        with open(baseline_yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, allow_unicode=True)


class BaselineManager:
    """Baseline 관리자"""
    
    def __init__(self, project_root: Path = None):
        if project_root:
            self.project_root = Path(project_root)
        else:
            self.project_root = Path.cwd()
    
    def get_baseline_path(self, project: str) -> Path:
        """프로젝트의 baseline.yaml 경로"""
        return self.project_root / "projects" / project / "baseline.yaml"
    
    def create_baseline(
        self,
        project: str,
        run_id: str,
        trace_path: str
    ) -> Path:
        """
        Baseline 생성
        
        Args:
            project: 프로젝트 이름
            run_id: Run ID
            trace_path: Trace 경로
        
        Returns:
            baseline.yaml 경로
        """
        config = BaselineConfig(
            project=project,
            baseline_run_id=run_id,
            trace_path=trace_path
        )
        
        baseline_path = self.get_baseline_path(project)
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        
        config.save(baseline_path)
        
        return baseline_path
    
    def load_baseline(self, project: str) -> Optional[BaselineConfig]:
        """Baseline 로드"""
        baseline_path = self.get_baseline_path(project)
        
        if not baseline_path.exists():
            return None
        
        return BaselineConfig.load(baseline_path)
    
    def verify_baseline(self, project: str) -> tuple[bool, list[str]]:
        """
        Baseline 검증
        
        Returns:
            (성공 여부, 오류 메시지 리스트)
        """
        errors = []
        
        # baseline.yaml 존재 확인
        baseline_path = self.get_baseline_path(project)
        if not baseline_path.exists():
            errors.append(f"baseline.yaml not found: {baseline_path}")
            return False, errors
        
        # baseline.yaml 로드
        try:
            config = BaselineConfig.load(baseline_path)
        except Exception as e:
            errors.append(f"baseline.yaml load error: {e}")
            return False, errors
        
        # trace.json 존재 확인
        trace_path = self.project_root / config.trace_path
        if not trace_path.exists():
            errors.append(f"trace.json not found: {trace_path}")
        
        # approval.json 존재 확인
        trace_dir = trace_path.parent
        approval_path = trace_dir / "approval.json"
        if not approval_path.exists():
            errors.append(f"approval.json not found: {approval_path}")
        else:
            # approval.json 검증
            from .approval import Approval, verify_baseline as verify_approval
            valid, approval_errors = verify_approval(trace_dir)
            if not valid:
                errors.extend(approval_errors)
        
        # approved 확인
        if not config.approved:
            errors.append("baseline is not approved")
        
        return len(errors) == 0, errors
    
    def get_baseline_trace_path(self, project: str) -> Optional[Path]:
        """Baseline trace 경로 반환"""
        config = self.load_baseline(project)
        if not config:
            return None
        
        return self.project_root / config.trace_path
