"""
NEXOUS CLI - Command Line Interface

CLI는 사용자 인터페이스가 아니라 실행 진입점이다.

❌ 로직
❌ 판단
❌ 해석

CLI는 오직 아래만 한다:
    입력 파싱 → Runner 호출 → 상태 출력

CLI는 입구다.
판단은 Runner가 한다.
"""

from __future__ import annotations

import os
import argparse
import sys
from pathlib import Path


def load_env():
    """
    .env 파일에서 환경변수 로드
    
    우선순위:
    1. 이미 설정된 환경변수 (유지)
    2. .env 파일의 값
    """
    env_paths = [
        Path.cwd() / ".env",  # 현재 디렉토리
        Path(__file__).parent.parent.parent / ".env",  # NEXOUS 루트
    ]
    
    for env_path in env_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()
                        # 이미 설정된 환경변수는 덮어쓰지 않음
                        if key and not os.getenv(key):
                            os.environ[key] = value
            break


def create_parser() -> argparse.ArgumentParser:
    """CLI 파서 생성"""
    parser = argparse.ArgumentParser(
        prog="nexous",
        description="NEXOUS - Multi-Agent Orchestration System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  nexous run project.yaml
  nexous run project.yaml --run-id my_run_001
  nexous run project.yaml --use-llm
  nexous run project.yaml --dry-run
        """
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # ========================================
    # run 명령
    # ========================================
    run_parser = subparsers.add_parser(
        "run",
        help="Run a NEXOUS project"
    )
    
    run_parser.add_argument(
        "project",
        type=str,
        help="Path to project.yaml"
    )
    
    run_parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Run ID (auto-generated if not specified)"
    )
    
    run_parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use real LLM (requires OPENAI_API_KEY)"
    )
    
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate YAML without execution"
    )
    
    run_parser.add_argument(
        "--trace-dir",
        type=str,
        default="traces",
        help="Directory for trace output (default: traces)"
    )
    
    # ========================================
    # replay 명령
    # ========================================
    replay_parser = subparsers.add_parser(
        "replay",
        help="Replay execution from trace file"
    )
    
    replay_parser.add_argument(
        "trace",
        type=str,
        help="Path to trace.json file"
    )
    
    replay_parser.add_argument(
        "--mode",
        type=str,
        choices=["dry", "full"],
        default="dry",
        help="Replay mode: 'dry' (timeline only) or 'full' (actual execution)"
    )
    
    # ========================================
    # diff 명령
    # ========================================
    diff_parser = subparsers.add_parser(
        "diff",
        help="Compare two trace files"
    )
    
    diff_parser.add_argument(
        "trace1",
        type=str,
        help="Path to first trace.json file"
    )
    
    diff_parser.add_argument(
        "trace2",
        type=str,
        help="Path to second trace.json file"
    )
    
    diff_parser.add_argument(
        "--only",
        type=str,
        choices=["llm", "tools", "errors"],
        help="Filter comparison: 'llm' (LLM calls only), 'tools' (Tool calls only), 'errors' (Errors only)"
    )
    
    return parser


def cmd_run(args: argparse.Namespace) -> int:
    """run 명령 실행"""
    project_path = Path(args.project)
    if not project_path.exists():
        print(f"[NEXOUS] Error: Project file not found: {args.project}")
        return 1
    
    # dry-run 모드
    if args.dry_run:
        print(f"[NEXOUS] Dry-run mode: validating {args.project}")
        try:
            from nexous.core.runner import Runner
            runner = Runner(trace_dir=args.trace_dir)
            runner._load_project(str(project_path))
            print(f"[NEXOUS] Validation passed: {args.project}")
            return 0
        except Exception as e:
            print(f"[NEXOUS] Validation failed: {e}")
            return 1
    
    # API Key 확인 (--use-llm 시)
    if args.use_llm and not os.getenv("OPENAI_API_KEY"):
        print(f"[NEXOUS] Error: OPENAI_API_KEY not set")
        print(f"[NEXOUS] Set API key in .env file or environment variable")
        return 1
    
    # 실행
    print(f"[NEXOUS] Project execution started")
    print(f"[NEXOUS] Project: {args.project}")
    
    if args.use_llm:
        print(f"[NEXOUS] LLM Mode: ENABLED (OpenAI)")
    
    if args.run_id:
        print(f"[NEXOUS] Run ID: {args.run_id}")
    
    try:
        from nexous.core.runner import run_project
        
        trace_path = run_project(
            project_yaml_path=str(project_path),
            run_id=args.run_id,
            trace_dir=args.trace_dir,
            use_llm=args.use_llm
        )
        
        print(f"[NEXOUS] Trace written to {trace_path}")
        print(f"[NEXOUS] Project execution completed")
        return 0
        
    except Exception as e:
        print(f"[NEXOUS] Execution failed: {e}")
        return 1


def cmd_replay(args) -> int:
    """Replay 명령 실행"""
    from nexous.trace import TraceReplay
    
    print("[NEXOUS] Trace Replay started")
    print(f"[NEXOUS] Trace file: {args.trace}")
    print(f"[NEXOUS] Mode: {args.mode.upper()}")
    
    try:
        replay = TraceReplay(args.trace, mode=args.mode)
        replay.replay()
        print("\n[NEXOUS] Replay completed successfully")
        return 0
    except FileNotFoundError as e:
        print(f"[NEXOUS] Error: {e}")
        return 1
    except Exception as e:
        print(f"[NEXOUS] Replay failed: {e}")
        return 1
        print(f"[NEXOUS] Replay failed: {e}")
        return 1


def cmd_diff(args) -> int:
    """Diff 명령 실행"""
    from nexous.trace import diff_traces
    
    print("[NEXOUS] Trace Diff started")
    print(f"[NEXOUS] Trace 1: {args.trace1}")
    print(f"[NEXOUS] Trace 2: {args.trace2}")
    if args.only:
        print(f"[NEXOUS] Filter: --only {args.only}")
    
    try:
        diff_traces(args.trace1, args.trace2, only=args.only)
        print("\n[NEXOUS] Diff completed successfully")
        return 0
    except FileNotFoundError as e:
        print(f"[NEXOUS] Error: {e}")
        return 1
    except Exception as e:
        print(f"[NEXOUS] Diff failed: {e}")
        return 1
    except Exception as e:
        print(f"[NEXOUS] Diff failed: {e}")
        return 1


def cli(args: list = None) -> int:
    """CLI 메인 함수"""
    # .env 파일 로드
    load_env()
    
    parser = create_parser()
    parsed_args = parser.parse_args(args)
    
    if parsed_args.command is None:
        parser.print_help()
        return 0
    
    if parsed_args.command == "run":
        return cmd_run(parsed_args)
    elif parsed_args.command == "replay":
        return cmd_replay(parsed_args)
    elif parsed_args.command == "diff":
        return cmd_diff(parsed_args)
    
    return 0


def main():
    """CLI 진입점"""
    sys.exit(cli())


if __name__ == "__main__":
    main()
