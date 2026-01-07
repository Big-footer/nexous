"""
NEXOUS Baseline Module

Baseline 승인, 검증, 관리 기능
"""

from .approval import Approval, approve_baseline, verify_baseline
from .manager import BaselineManager

__all__ = [
    'Approval',
    'approve_baseline',
    'verify_baseline',
    'BaselineManager'
]
