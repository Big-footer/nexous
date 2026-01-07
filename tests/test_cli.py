"""
NEXOUS Test - CLI 실행 테스트

CLI 성공/실패 테스트
"""

import os
import sys
import pytest
import subprocess
from pathlib import Path


class TestCLIExecution:
    """CLI 실행 테스트"""
    
    def test_cli_help(self, project_root):
        """CLI --help 실행"""
        result = subprocess.run(
            [sys.executable, "-m", "nexous.cli.main", "--help"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "NEXOUS" in result.stdout
    
    def test_cli_version(self, project_root):
        """CLI --version 실행"""
        result = subprocess.run(
            [sys.executable, "-m", "nexous.cli.main", "--version"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "0.1.0" in result.stdout
    
    def test_cli_run_dry_run(self, project_root, simple_project_yaml):
        """CLI dry-run 모드 실행"""
        result = subprocess.run(
            [sys.executable, "-m", "nexous.cli.main", "run", simple_project_yaml, "--dry-run"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Validation passed" in result.stdout
    
    def test_cli_run_invalid_yaml(self, project_root, invalid_project_yaml):
        """잘못된 YAML 실행 시 실패"""
        result = subprocess.run(
            [sys.executable, "-m", "nexous.cli.main", "run", invalid_project_yaml, "--dry-run"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
    
    def test_cli_run_nonexistent_file(self, project_root):
        """존재하지 않는 파일 실행 시 실패"""
        result = subprocess.run(
            [sys.executable, "-m", "nexous.cli.main", "run", "nonexistent.yaml"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY", "").startswith("sk-"),
        reason="OPENAI_API_KEY not set"
    )
    def test_cli_run_with_llm(self, project_root, simple_project_yaml, test_trace_dir):
        """실제 LLM 사용 실행"""
        result = subprocess.run(
            [
                sys.executable, "-m", "nexous.cli.main", "run",
                simple_project_yaml,
                "--use-llm",
                "--trace-dir", str(test_trace_dir),
                "--run-id", "cli_llm_test"
            ],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0
        assert "completed" in result.stdout.lower()
    
    def test_cli_run_without_llm(self, project_root, simple_project_yaml, test_trace_dir):
        """LLM 없이 실행 (Placeholder)"""
        result = subprocess.run(
            [
                sys.executable, "-m", "nexous.cli.main", "run",
                simple_project_yaml,
                "--trace-dir", str(test_trace_dir),
                "--run-id", "cli_no_llm_test"
            ],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
