"""
PROMETHEUS Chat UI - Streamlit 기반 대화 인터페이스

Claude 스타일의 채팅 UI를 제공합니다.
"""

import streamlit as st
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import sys
import os

# PROMETHEUS 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prometheus import (
    MetaAgent,
    ExecutionMode,
    SessionManager,
    ConversationMemory,
    Router,
    AgentFactory,
    AgentType,
    PythonExecTool,
    RAGTool,
    __version__,
)

# =============================================================================
# 페이지 설정
# =============================================================================
st.set_page_config(
    page_title="PROMETHEUS",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# 커스텀 CSS
# =============================================================================
st.markdown("""
<style>
    /* 메인 컨테이너 */
    .main {
        background-color: #1a1a2e;
    }
    
    /* 채팅 컨테이너 */
    .chat-container {
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
    }
    
    /* 메시지 스타일 */
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px 20px;
        border-radius: 20px 20px 5px 20px;
        margin: 10px 0;
        max-width: 80%;
        margin-left: auto;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .assistant-message {
        background: linear-gradient(135deg, #2d2d44 0%, #1a1a2e 100%);
        color: #e0e0e0;
        padding: 15px 20px;
        border-radius: 20px 20px 20px 5px;
        margin: 10px 0;
        max-width: 80%;
        border: 1px solid #3d3d5c;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }
    
    /* 입력 필드 */
    .stTextInput > div > div > input {
        background-color: #2d2d44;
        color: white;
        border: 1px solid #3d3d5c;
        border-radius: 25px;
        padding: 15px 20px;
    }
    
    /* 버튼 */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 10px 30px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* 사이드바 */
    .css-1d391kg {
        background-color: #16213e;
    }
    
    /* 제목 */
    .main-title {
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 10px;
    }
    
    .sub-title {
        text-align: center;
        color: #888;
        font-size: 1rem;
        margin-bottom: 30px;
    }
    
    /* 상태 표시 */
    .status-badge {
        display: inline-block;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    
    .status-ready {
        background-color: #28a745;
        color: white;
    }
    
    .status-processing {
        background-color: #ffc107;
        color: black;
    }
    
    /* 타임스탬프 */
    .timestamp {
        font-size: 0.7rem;
        color: #666;
        margin-top: 5px;
    }
    
    /* 스크롤바 */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1a1a2e;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #3d3d5c;
        border-radius: 4px;
    }
    
    /* Agent 태그 */
    .agent-tag {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 10px;
        font-size: 0.7rem;
        margin-bottom: 5px;
    }
    
    .agent-planner { background-color: #3498db; color: white; }
    .agent-executor { background-color: #e74c3c; color: white; }
    .agent-writer { background-color: #2ecc71; color: white; }
    .agent-qa { background-color: #9b59b6; color: white; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 세션 상태 초기화
# =============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_manager" not in st.session_state:
    st.session_state.session_manager = SessionManager()
    st.session_state.session = st.session_state.session_manager.create_session(
        user_id="streamlit_user"
    )

if "conversation" not in st.session_state:
    st.session_state.conversation = ConversationMemory(
        session_id=st.session_state.session.id
    )

if "router" not in st.session_state:
    st.session_state.router = Router()

if "agent_factory" not in st.session_state:
    st.session_state.agent_factory = AgentFactory()

if "processing" not in st.session_state:
    st.session_state.processing = False

if "current_mode" not in st.session_state:
    st.session_state.current_mode = "auto"

# =============================================================================
# 사이드바
# =============================================================================
with st.sidebar:
    st.markdown("## 🔥 PROMETHEUS")
    st.markdown(f"<small>v{__version__}</small>", unsafe_allow_html=True)
    st.markdown("---")
    
    # 실행 모드 선택
    st.markdown("### ⚙️ 설정")
    mode = st.selectbox(
        "실행 모드",
        options=["auto", "sequential", "plan_based"],
        index=0,
        help="auto: 자동 선택, sequential: 순차 실행, plan_based: 계획 기반"
    )
    st.session_state.current_mode = mode
    
    # Agent 정보
    st.markdown("### 🤖 Agents")
    agents_info = {
        "Planner": ("📋", "작업 계획 수립"),
        "Executor": ("⚡", "작업 실행"),
        "Writer": ("✍️", "문서 작성"),
        "QA": ("🔍", "품질 검토"),
    }
    
    for name, (icon, desc) in agents_info.items():
        st.markdown(f"{icon} **{name}**: {desc}")
    
    st.markdown("---")
    
    # 대화 관리
    st.markdown("### 💬 대화 관리")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ 초기화", use_container_width=True):
            st.session_state.messages = []
            st.session_state.conversation.clear()
            st.rerun()
    
    with col2:
        if st.button("📥 내보내기", use_container_width=True):
            # 대화 내보내기 (추후 구현)
            st.info("준비 중...")
    
    st.markdown("---")
    
    # 통계
    st.markdown("### 📊 통계")
    st.markdown(f"- 메시지 수: **{len(st.session_state.messages)}**")
    st.markdown(f"- 세션 ID: `{st.session_state.session.id[:12]}...`")
    
    st.markdown("---")
    st.markdown(
        "<small>Made with ❤️ by PROMETHEUS Team</small>",
        unsafe_allow_html=True
    )

# =============================================================================
# 메인 화면
# =============================================================================

# 헤더
st.markdown('<h1 class="main-title">🔥 PROMETHEUS</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-title">Multi-Agent Orchestration Framework</p>',
    unsafe_allow_html=True
)

# 상태 표시
status_class = "status-processing" if st.session_state.processing else "status-ready"
status_text = "처리 중..." if st.session_state.processing else "준비됨"
st.markdown(
    f'<div style="text-align: center; margin-bottom: 20px;">'
    f'<span class="status-badge {status_class}">{status_text}</span>'
    f'</div>',
    unsafe_allow_html=True
)

# 채팅 컨테이너
chat_container = st.container()

with chat_container:
    # 환영 메시지 (메시지가 없을 때)
    if not st.session_state.messages:
        st.markdown("""
        <div style="text-align: center; padding: 50px; color: #888;">
            <h3>👋 안녕하세요!</h3>
            <p>PROMETHEUS에 오신 것을 환영합니다.</p>
            <p>아래에 요청을 입력해주세요.</p>
            <br>
            <p><small>예시:</small></p>
            <p><code>데이터 분석 보고서를 작성해주세요</code></p>
            <p><code>Python으로 피보나치 수열을 계산해주세요</code></p>
            <p><code>프로젝트 계획을 세워주세요</code></p>
        </div>
        """, unsafe_allow_html=True)
    
    # 메시지 표시
    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg["content"]
        timestamp = msg.get("timestamp", "")
        agent = msg.get("agent", "")
        
        if role == "user":
            st.markdown(
                f'<div class="user-message">'
                f'{content}'
                f'<div class="timestamp">{timestamp}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            agent_tag = ""
            if agent:
                agent_class = f"agent-{agent.lower()}"
                agent_tag = f'<span class="agent-tag {agent_class}">{agent}</span><br>'
            
            st.markdown(
                f'<div class="assistant-message">'
                f'{agent_tag}'
                f'{content}'
                f'<div class="timestamp">{timestamp}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

# =============================================================================
# 입력 영역
# =============================================================================
st.markdown("<br>", unsafe_allow_html=True)

# 입력 폼
with st.form(key="chat_form", clear_on_submit=True):
    col1, col2 = st.columns([6, 1])
    
    with col1:
        user_input = st.text_input(
            "메시지 입력",
            placeholder="요청을 입력하세요...",
            label_visibility="collapsed",
        )
    
    with col2:
        submit_button = st.form_submit_button("전송 🚀", use_container_width=True)

# =============================================================================
# 메시지 처리
# =============================================================================
async def process_message(user_message: str) -> Dict[str, Any]:
    """사용자 메시지 처리"""
    
    # 라우팅
    router = st.session_state.router
    decision = router.route_sync(user_message)
    
    # Agent 선택
    agent_name = decision.target_agent.value.capitalize()
    
    # 응답 생성 (현재는 시뮬레이션)
    # TODO: 실제 LLM 연동
    
    response = {
        "agent": agent_name,
        "content": "",
    }
    
    # Agent별 시뮬레이션 응답
    if decision.target_agent == AgentType.PLANNER:
        response["content"] = f"""📋 **계획 수립 완료**

요청을 분석하여 다음과 같은 계획을 수립했습니다:

**1단계**: 요구사항 분석
- 입력: "{user_message[:50]}..."
- 목표 파악 및 범위 정의

**2단계**: 작업 분해
- 세부 작업 식별
- 의존성 분석

**3단계**: 실행 계획
- 리소스 할당
- 일정 수립

다음 단계로 진행하시겠습니까?"""
    
    elif decision.target_agent == AgentType.EXECUTOR:
        # Python 코드 실행 시도
        if "python" in user_message.lower() or "계산" in user_message or "실행" in user_message:
            tool = PythonExecTool()
            
            # 간단한 코드 추출 시도
            if "피보나치" in user_message:
                code = """
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)

result = [fib(i) for i in range(10)]
print(f"피보나치 수열: {result}")
result
"""
                result = await tool.execute(code=code)
                if result.success:
                    response["content"] = f"""⚡ **실행 완료**

```python
{code.strip()}
```

**결과:**
```
{result.output.get('stdout', '')}
반환값: {result.output.get('return_value', 'None')}
```
"""
                else:
                    response["content"] = f"❌ 실행 오류: {result.error}"
            else:
                response["content"] = f"""⚡ **작업 실행 준비**

요청하신 작업을 실행할 준비가 되었습니다.
실행할 구체적인 코드나 명령을 알려주세요.

**사용 가능한 도구:**
- 🐍 Python 코드 실행
- 🔍 문서 검색 (RAG)
- 💻 시스템 명령"""
        else:
            response["content"] = f"""⚡ **작업 분석 완료**

요청: "{user_message}"

이 작업을 실행하려면 추가 정보가 필요합니다.
구체적인 실행 내용을 알려주세요."""
    
    elif decision.target_agent == AgentType.WRITER:
        response["content"] = f"""✍️ **문서 작성 준비**

요청하신 내용을 바탕으로 문서를 작성하겠습니다.

**문서 유형 선택:**
1. 📄 보고서
2. 📝 기술 문서
3. 📊 분석 문서
4. 📋 요약 문서

원하시는 형식을 알려주시면 작성을 시작하겠습니다."""
    
    elif decision.target_agent == AgentType.QA:
        response["content"] = f"""🔍 **품질 검토 준비**

검토할 내용을 제출해주시면 다음 항목을 확인하겠습니다:

**검토 항목:**
- ✅ 정확성
- ✅ 완전성
- ✅ 일관성
- ✅ 가독성
- ✅ 형식 준수

검토할 문서나 코드를 공유해주세요."""
    
    else:
        response["content"] = f"""요청을 처리했습니다.

**분석 결과:**
- 라우팅: {agent_name}
- 전략: {decision.strategy.value}

추가 요청이 있으시면 말씀해주세요."""
    
    return response


def run_async(coro):
    """비동기 함수 실행 헬퍼"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


if submit_button and user_input:
    # 사용자 메시지 추가
    timestamp = datetime.now().strftime("%H:%M")
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": timestamp,
    })
    st.session_state.conversation.add_user_message(user_input)
    
    # 처리 중 상태
    st.session_state.processing = True
    
    # 메시지 처리
    with st.spinner("🔄 처리 중..."):
        response = run_async(process_message(user_input))
    
    # 응답 추가
    st.session_state.messages.append({
        "role": "assistant",
        "content": response["content"],
        "timestamp": datetime.now().strftime("%H:%M"),
        "agent": response.get("agent", ""),
    })
    st.session_state.conversation.add_assistant_message(response["content"])
    
    # 처리 완료
    st.session_state.processing = False
    
    # 페이지 새로고침
    st.rerun()

# =============================================================================
# 푸터
# =============================================================================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    """
    <div style="text-align: center; color: #666; font-size: 0.8rem;">
        <p>PROMETHEUS v{version} | Multi-Agent Orchestration Framework</p>
        <p>Press Enter or click 🚀 to send message</p>
    </div>
    """.format(version=__version__),
    unsafe_allow_html=True
)
