"""
PROMETHEUS CLI - 명령줄 인터페이스

이 파일의 책임:
- 프로젝트 생성/관리
- 요청 실행
- 상태 조회
- 설정 관리
"""

import argparse
import asyncio
import sys
import json
from pathlib import Path
from typing import Optional

import prometheus
from prometheus import (
    ConfigLoader,
    MetaAgent,
    ExecutionMode,
    AgentType,
    LLMProvider,
)


def create_parser() -> argparse.ArgumentParser:
    """CLI 파서 생성"""
    parser = argparse.ArgumentParser(
        prog="prometheus",
        description="PROMETHEUS - Multi-Agent Orchestration Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  prometheus new my_project --request "데이터 분석 보고서 작성"
  prometheus run my_project "추가 분석 요청"
  prometheus list
  prometheus status my_project
  prometheus version
        """,
    )
    
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"PROMETHEUS v{prometheus.__version__}",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # new - 새 프로젝트 생성
    new_parser = subparsers.add_parser("new", help="Create a new project")
    new_parser.add_argument("name", help="Project name")
    new_parser.add_argument("--request", "-r", help="Initial request")
    new_parser.add_argument("--description", "-d", default="", help="Project description")
    
    # run - 프로젝트 실행
    run_parser = subparsers.add_parser("run", help="Run a project with request")
    run_parser.add_argument("project", nargs="?", help="Project name")
    run_parser.add_argument("request", nargs="?", help="Request to execute")
    run_parser.add_argument("--mode", "-m", 
                           choices=["auto", "sequential", "plan_based"],
                           default="auto", help="Execution mode")
    run_parser.add_argument("--interactive", "-i", action="store_true",
                           help="Interactive mode")
    
    # list - 프로젝트 목록
    list_parser = subparsers.add_parser("list", help="List all projects")
    list_parser.add_argument("--verbose", "-v", action="store_true",
                            help="Show detailed info")
    
    # status - 프로젝트 상태
    status_parser = subparsers.add_parser("status", help="Show project status")
    status_parser.add_argument("project", help="Project name")
    
    # config - 설정 관리
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_parser.add_argument("action", choices=["show", "set", "reset"],
                              help="Config action")
    config_parser.add_argument("--key", "-k", help="Config key")
    config_parser.add_argument("--value", "-v", help="Config value")
    
    # init - 초기화
    init_parser = subparsers.add_parser("init", help="Initialize PROMETHEUS in current directory")
    
    # agents - Agent 정보
    agents_parser = subparsers.add_parser("agents", help="List available agents")
    
    # tools - Tool 정보
    tools_parser = subparsers.add_parser("tools", help="List available tools")
    
    return parser


def cmd_new(args) -> int:
    """새 프로젝트 생성"""
    try:
        loader = ConfigLoader()
        path = loader.create_project(
            project_name=args.name,
            request=args.request,
        )
        print(f"✅ Project '{args.name}' created at: {path}")
        
        if args.request:
            print(f"   Initial request: {args.request}")
        
        print(f"\nNext steps:")
        print(f"  1. Edit the project config at: {path}")
        print(f"  2. Run: prometheus run {args.name} \"your request\"")
        
        return 0
    except Exception as e:
        print(f"❌ Failed to create project: {e}", file=sys.stderr)
        return 1


def cmd_run(args) -> int:
    """프로젝트 실행"""
    if args.interactive:
        return cmd_run_interactive(args)
    
    if not args.request:
        print("❌ Request is required. Use: prometheus run [project] \"request\"", file=sys.stderr)
        return 1
    
    mode_map = {
        "auto": ExecutionMode.AUTO,
        "sequential": ExecutionMode.SEQUENTIAL,
        "plan_based": ExecutionMode.PLAN_BASED,
    }
    
    async def run_async():
        meta = MetaAgent()
        result = await meta.process_request(
            request=args.request,
            project_name=args.project,
            mode=mode_map[args.mode],
        )
        return result
    
    try:
        print(f"🚀 Running request: {args.request}")
        if args.project:
            print(f"   Project: {args.project}")
        print(f"   Mode: {args.mode}")
        print("-" * 50)
        
        result = asyncio.run(run_async())
        
        if result.success:
            print("\n✅ Execution completed successfully!")
            print(f"   Execution time: {result.execution_time:.2f}s")
            
            if result.plan:
                print(f"   Steps completed: {len([s for s in result.plan.steps if s.status.value == 'completed'])}/{result.plan.total_steps}")
            
            if result.result:
                print(f"\n📄 Result:")
                print(json.dumps(result.result, indent=2, ensure_ascii=False, default=str)[:1000])
        else:
            print(f"\n❌ Execution failed: {result.error}")
            return 1
        
        return 0
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


def cmd_run_interactive(args) -> int:
    """대화형 모드 실행"""
    print("=" * 60)
    print("🤖 PROMETHEUS Interactive Mode")
    print("=" * 60)
    print("Type 'quit' or 'exit' to exit.")
    print("Type 'help' for available commands.")
    print("-" * 60)
    
    meta = MetaAgent()
    project_name = args.project
    
    async def process(request: str):
        return await meta.process_request(
            request=request,
            project_name=project_name,
            mode=ExecutionMode.AUTO,
        )
    
    while True:
        try:
            user_input = input("\n📝 Request > ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["quit", "exit", "q"]:
                print("👋 Goodbye!")
                break
            
            if user_input.lower() == "help":
                print("""
Available commands:
  quit, exit, q  - Exit interactive mode
  help          - Show this help
  status        - Show current status
  
Or enter any request to execute.
                """)
                continue
            
            if user_input.lower() == "status":
                stats = meta._lifecycle.get_stats() if hasattr(meta, '_lifecycle') else {}
                print(f"Projects: {len(meta._project_agents)}")
                continue
            
            print(f"\n⏳ Processing: {user_input}")
            result = asyncio.run(process(user_input))
            
            if result.success:
                print(f"✅ Done! ({result.execution_time:.2f}s)")
                if result.result:
                    print(f"Result: {str(result.result)[:500]}")
            else:
                print(f"❌ Failed: {result.error}")
                
        except KeyboardInterrupt:
            print("\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return 0


def cmd_list(args) -> int:
    """프로젝트 목록"""
    loader = ConfigLoader()
    projects = loader.list_projects()
    
    if not projects:
        print("📂 No projects found.")
        print("   Create one with: prometheus new <project_name>")
        return 0
    
    print(f"📂 Projects ({len(projects)}):")
    print("-" * 40)
    
    for name in projects:
        if args.verbose:
            try:
                config = loader.load_project(name)
                print(f"  📁 {name}")
                print(f"     Description: {config.metadata.description or 'N/A'}")
                print(f"     Agents: {len(config.agents)}")
                print(f"     Created: {config.metadata.created_at}")
            except:
                print(f"  📁 {name} (error loading)")
        else:
            print(f"  📁 {name}")
    
    return 0


def cmd_status(args) -> int:
    """프로젝트 상태"""
    loader = ConfigLoader()
    
    try:
        config = loader.load_project(args.project)
    except FileNotFoundError:
        print(f"❌ Project '{args.project}' not found.", file=sys.stderr)
        return 1
    
    print(f"📊 Project: {config.metadata.name}")
    print("=" * 40)
    print(f"Description: {config.metadata.description or 'N/A'}")
    print(f"Version: {config.metadata.version}")
    print(f"Created: {config.metadata.created_at}")
    
    print(f"\n🤖 Agents ({len(config.agents)}):")
    for agent in config.agents:
        print(f"  - {agent.agent_type.value}: {agent.name or 'default'}")
    
    print(f"\n🔧 Tools:")
    for agent in config.agents:
        if agent.tools:
            print(f"  {agent.agent_type.value}: {', '.join(agent.tools)}")
    
    if config.default_llm:
        print(f"\n🧠 Default LLM: {config.default_llm.provider.value}/{config.default_llm.model}")
    
    return 0


def cmd_config(args) -> int:
    """설정 관리"""
    if args.action == "show":
        loader = ConfigLoader()
        print(f"📁 Base directory: {loader.base_dir}")
        print(f"📁 Projects directory: {loader.projects_dir}")
        return 0
    
    print(f"Config action '{args.action}' not implemented yet.")
    return 0


def cmd_init(args) -> int:
    """현재 디렉토리에 PROMETHEUS 초기화"""
    cwd = Path.cwd()
    prometheus_dir = cwd / ".prometheus"
    
    if prometheus_dir.exists():
        print(f"⚠️  PROMETHEUS already initialized in {cwd}")
        return 0
    
    prometheus_dir.mkdir(parents=True)
    (prometheus_dir / "projects").mkdir()
    
    # 기본 설정 파일 생성
    config = {
        "version": prometheus.__version__,
        "base_dir": str(prometheus_dir),
    }
    
    with open(prometheus_dir / "config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ PROMETHEUS initialized in {cwd}")
    print(f"   Config directory: {prometheus_dir}")
    
    return 0


def cmd_agents(args) -> int:
    """Agent 목록"""
    print("🤖 Available Agents:")
    print("-" * 40)
    
    agents = [
        ("planner", "PlannerAgent", "작업 계획 수립 및 분해"),
        ("executor", "ExecutorAgent", "계획된 작업 실행"),
        ("writer", "WriterAgent", "문서 작성 및 번역"),
        ("qa", "QAAgent", "품질 검토 및 검증"),
    ]
    
    for agent_type, class_name, desc in agents:
        print(f"  📌 {agent_type}")
        print(f"     Class: {class_name}")
        print(f"     Description: {desc}")
        print()
    
    return 0


def cmd_tools(args) -> int:
    """Tool 목록"""
    print("🔧 Available Tools:")
    print("-" * 40)
    
    tools = [
        ("python_exec", "PythonExecTool", "Python 코드 안전 실행"),
        ("rag_search", "RAGTool", "벡터 검색 및 문서 처리"),
        ("desktop_commander", "DesktopCommanderTool", "시스템 명령 실행"),
    ]
    
    for tool_name, class_name, desc in tools:
        print(f"  🔹 {tool_name}")
        print(f"     Class: {class_name}")
        print(f"     Description: {desc}")
        print()
    
    return 0


def main() -> int:
    """메인 진입점"""
    parser = create_parser()
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 0
    
    commands = {
        "new": cmd_new,
        "run": cmd_run,
        "list": cmd_list,
        "status": cmd_status,
        "config": cmd_config,
        "init": cmd_init,
        "agents": cmd_agents,
        "tools": cmd_tools,
    }
    
    handler = commands.get(args.command)
    if handler:
        return handler(args)
    
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
