"""
PROMETHEUS 사용 예제

이 파일은 PROMETHEUS의 다양한 사용 방법을 보여줍니다.
"""

import asyncio
from prometheus import (
    # 메인 함수
    list_projects,
    
    # Agents
    AgentInput,
    
    # Controller
    AgentFactory,
    Router,
    
    # Tools
    PythonExecTool,
    RAGTool,
    DesktopCommanderTool,
    
    # Memory
    VectorStore,
    ContextManager,
    SessionManager,
    ConversationMemory,
    ContextPriority,
    
    # Enums
    AgentType,
)


# =============================================================================
# 예제 1: 간단한 Python 코드 실행
# =============================================================================
async def example_python_exec():
    """Python 코드 실행 예제"""
    print("\n" + "=" * 60)
    print("예제 1: Python 코드 실행")
    print("=" * 60)
    
    tool = PythonExecTool()
    
    # 간단한 계산
    result = await tool.execute(code="2 ** 10")
    print(f"2 ** 10 = {result.output['return_value']}")
    
    # 데이터 처리
    result = await tool.execute(
        code="""
data = [1, 2, 3, 4, 5]
squared = [x ** 2 for x in data]
print(f"Squared: {squared}")
sum(squared)
"""
    )
    print(f"Sum of squares = {result.output['return_value']}")


# =============================================================================
# 예제 2: RAG 검색
# =============================================================================
async def example_rag_search():
    """RAG 검색 예제"""
    print("\n" + "=" * 60)
    print("예제 2: RAG 검색")
    print("=" * 60)
    
    rag = RAGTool()
    
    # 문서 추가
    await rag.add_document(
        content="Python은 데이터 과학과 머신러닝에 널리 사용되는 프로그래밍 언어입니다.",
        metadata={"topic": "python", "lang": "ko"}
    )
    await rag.add_document(
        content="JavaScript는 웹 개발의 핵심 언어로 프론트엔드와 백엔드 모두에서 사용됩니다.",
        metadata={"topic": "javascript", "lang": "ko"}
    )
    await rag.add_document(
        content="머신러닝은 데이터로부터 패턴을 학습하여 예측을 수행하는 AI 기술입니다.",
        metadata={"topic": "ml", "lang": "ko"}
    )
    
    # 검색
    results = await rag.search("데이터 과학 프로그래밍", top_k=2)
    
    print(f"검색 결과 ({len(results)}개):")
    for r in results:
        print(f"  - Score: {r.score:.3f}")
        print(f"    Content: {r.chunk.content[:50]}...")


# =============================================================================
# 예제 3: 세션 및 대화 관리
# =============================================================================
async def example_session_conversation():
    """세션 및 대화 관리 예제"""
    print("\n" + "=" * 60)
    print("예제 3: 세션 및 대화 관리")
    print("=" * 60)
    
    # 세션 관리자
    session_mgr = SessionManager()
    
    # 세션 생성
    session = session_mgr.create_session(
        user_id="user_123",
        metadata={"language": "ko", "timezone": "Asia/Seoul"}
    )
    print(f"세션 생성됨: {session.id}")
    
    # 대화 메모리
    conv = ConversationMemory(session_id=session.id)
    
    # 대화 추가
    conv.add_system_message("당신은 친절한 AI 어시스턴트입니다.")
    conv.add_user_message("안녕하세요!")
    conv.add_assistant_message("안녕하세요! 무엇을 도와드릴까요?")
    conv.add_user_message("오늘 날씨가 어때요?")
    conv.add_assistant_message("죄송하지만 저는 실시간 날씨 정보에 접근할 수 없습니다.")
    
    print(f"대화 메시지 수: {len(conv.messages)}")
    
    # 세션 데이터 저장
    session_mgr.set_session_data(session.id, "conversation", conv.model_dump())
    
    # 마지막 2개 메시지 조회
    recent = conv.get_messages(last_n=2)
    print("최근 메시지:")
    for msg in recent:
        print(f"  [{msg['role']}] {msg['content'][:30]}...")


# =============================================================================
# 예제 4: Agent Factory 사용
# =============================================================================
async def example_agent_factory():
    """Agent Factory 사용 예제"""
    print("\n" + "=" * 60)
    print("예제 4: Agent Factory 사용")
    print("=" * 60)
    
    factory = AgentFactory()
    
    # Tool 등록
    factory.register_tool("python_exec", PythonExecTool())
    factory.register_tool("rag_search", RAGTool())
    
    print(f"등록된 Tools: {factory.list_tools()}")
    
    # Agent 생성
    planner = factory.create_agent(AgentType.PLANNER)
    executor = factory.create_agent(AgentType.EXECUTOR)
    writer = factory.create_agent(AgentType.WRITER)
    qa = factory.create_agent(AgentType.QA)
    
    print(f"생성된 Agents:")
    print(f"  - Planner: {planner.agent_type}")
    print(f"  - Executor: {executor.agent_type}")
    print(f"  - Writer: {writer.agent_type}")
    print(f"  - QA: {qa.agent_type}")


# =============================================================================
# 예제 5: Router 사용
# =============================================================================
async def example_router():
    """Router 사용 예제"""
    print("\n" + "=" * 60)
    print("예제 5: Router 사용")
    print("=" * 60)
    
    router = Router()
    
    test_requests = [
        "프로젝트 계획을 세워주세요",
        "이 코드를 실행해주세요",
        "보고서를 작성해주세요",
        "결과를 검토해주세요",
    ]
    
    print("요청별 라우팅 결과:")
    for request in test_requests:
        decision = router.route_sync(request)
        print(f"  '{request[:20]}...'")
        print(f"    → Agent: {decision.target_agent.value}")
        print(f"    → Strategy: {decision.strategy.value}")


# =============================================================================
# 예제 6: 컨텍스트 관리
# =============================================================================
async def example_context_manager():
    """컨텍스트 관리 예제"""
    print("\n" + "=" * 60)
    print("예제 6: 컨텍스트 관리")
    print("=" * 60)
    
    ctx = ContextManager()
    
    # 시스템 프롬프트 설정
    ctx.set_system_prompt("당신은 데이터 분석 전문가입니다.")
    
    # 메시지 추가 (우선순위 지정)
    await ctx.add_message("user", "중요한 분석 요청입니다", priority=ContextPriority.CRITICAL)
    await ctx.add_message("user", "일반적인 질문", priority=ContextPriority.MEDIUM)
    await ctx.add_message("user", "참고용 정보", priority=ContextPriority.LOW)
    
    print(f"토큰 수: {ctx.get_token_count()}")
    print(f"사용 가능 토큰: {ctx.get_available_tokens()}")
    
    # 컨텍스트 윈도우 구축
    window = ctx.build_context()
    messages = window.to_messages()
    
    print(f"컨텍스트 메시지 수: {len(messages)}")


# =============================================================================
# 예제 7: VectorStore 사용
# =============================================================================
async def example_vector_store():
    """VectorStore 사용 예제"""
    print("\n" + "=" * 60)
    print("예제 7: VectorStore 사용")
    print("=" * 60)
    
    store = VectorStore()
    
    # 문서 저장
    docs = [
        "인공지능은 인간의 학습, 추론, 지각 능력을 모방하는 기술입니다.",
        "딥러닝은 여러 층의 신경망을 사용하여 복잡한 패턴을 학습합니다.",
        "자연어 처리는 컴퓨터가 인간의 언어를 이해하고 생성하는 기술입니다.",
        "컴퓨터 비전은 이미지와 비디오를 분석하는 AI 분야입니다.",
    ]
    
    for doc in docs:
        await store.store(content=doc)
    
    print(f"저장된 문서 수: {store.count()}")
    
    # 유사도 검색
    results = await store.retrieve("인간의 언어를 이해하는 AI", max_results=2)
    
    print("검색 결과:")
    for r in results:
        print(f"  [{r.rank}] Score: {r.score:.3f}")
        print(f"      {r.entry.content[:40]}...")


# =============================================================================
# 예제 8: 시스템 명령 실행
# =============================================================================
async def example_desktop_commander():
    """Desktop Commander 사용 예제"""
    print("\n" + "=" * 60)
    print("예제 8: 시스템 명령 실행")
    print("=" * 60)
    
    cmd = DesktopCommanderTool()
    
    # 간단한 명령
    result = await cmd.execute(command="echo 'Hello PROMETHEUS'")
    print(f"echo 결과: {result.output['stdout'].strip()}")
    
    # 현재 디렉토리
    result = await cmd.execute(command="pwd")
    print(f"현재 디렉토리: {result.output['stdout'].strip()}")
    
    # 날짜
    result = await cmd.execute(command="date")
    print(f"현재 시간: {result.output['stdout'].strip()}")


# =============================================================================
# 메인 실행
# =============================================================================
async def main():
    """모든 예제 실행"""
    print("=" * 60)
    print("🚀 PROMETHEUS 사용 예제")
    print("=" * 60)
    
    await example_python_exec()
    await example_rag_search()
    await example_session_conversation()
    await example_agent_factory()
    await example_router()
    await example_context_manager()
    await example_vector_store()
    await example_desktop_commander()
    
    print("\n" + "=" * 60)
    print("✅ 모든 예제 완료!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
