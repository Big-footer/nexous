"""
NEXUS Multi-Agent 워크플로우 프로세서

GUI에서 LangGraph 워크플로우를 실행하는 스레드 클래스
"""

import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal


class WorkflowProcessor(QThread):
    """
    Multi-Agent 워크플로우 프로세서
    
    LangGraph 워크플로우를 실행하고 결과를 GUI에 전달합니다.
    """
    
    # 시그널 정의
    workflow_started = pyqtSignal(str)  # trace_id
    agent_started = pyqtSignal(str, str)  # agent_name, status
    agent_completed = pyqtSignal(str, dict)  # agent_name, result
    workflow_completed = pyqtSignal(dict)  # final_state
    workflow_error = pyqtSignal(str)  # error_message
    progress_update = pyqtSignal(int, int, str)  # current, total, message
    
    CONFIG_PATH = Path.home() / ".prometheus" / "config.json"
    
    def __init__(
        self,
        request: str,
        project_name: str = "unnamed",
        settings: Dict = None,
        attached_file: str = None,
    ):
        super().__init__()
        self.request = request
        self.project_name = project_name
        self.settings = settings or self._load_settings()
        self.attached_file = attached_file
        self._setup_api_keys()
        
        # 첨부 파일이 있으면 요청에 파일 정보 추가
        if self.attached_file:
            self.request = self._prepare_request_with_file()
    
    def _load_settings(self) -> Dict:
        """설정 로드"""
        if self.CONFIG_PATH.exists():
            try:
                with open(self.CONFIG_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _setup_api_keys(self) -> None:
        """API 키 환경변수 설정"""
        api_keys = self.settings.get("api_keys", {})
        
        if api_keys.get("openai"):
            os.environ["OPENAI_API_KEY"] = api_keys["openai"]
        if api_keys.get("anthropic"):
            os.environ["ANTHROPIC_API_KEY"] = api_keys["anthropic"]
        if api_keys.get("google"):
            os.environ["GOOGLE_API_KEY"] = api_keys["google"]
    
    def _prepare_request_with_file(self) -> str:
        """첨부 파일 정보를 요청에 추가"""
        import os
        
        file_path = self.attached_file
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_name)[1].lower()
        
        # 파일 내용 미리보기 생성
        preview = ""
        try:
            if file_ext in ['.csv', '.txt', '.json', '.md']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if len(content) > 2000:
                        preview = content[:2000] + "\n... (truncated)"
                    else:
                        preview = content
            elif file_ext in ['.xlsx', '.xls']:
                try:
                    import pandas as pd
                    df = pd.read_excel(file_path)
                    preview = f"Excel 파일 (행: {len(df)}, 열: {len(df.columns)})\n"
                    preview += f"컬럼: {list(df.columns)}\n\n"
                    preview += df.head(10).to_string()
                except:
                    preview = "[Excel 파일 - pandas 필요]"
            elif file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
                preview = f"[이미지 파일: {file_name}]"
            else:
                preview = f"[파일: {file_name}]"
        except Exception as e:
            preview = f"[파일 읽기 오류: {e}]"
        
        # 요청에 파일 정보 추가
        enhanced_request = f"""## 첨부 파일 정보
- 파일명: {file_name}
- 경로: {file_path}
- 형식: {file_ext}

## 파일 내용 미리보기
```
{preview}
```

## 사용자 요청
{self.request}

## 지시사항
위 첨부 파일을 분석하여 사용자 요청을 수행하세요. 파일 경로를 사용하여 데이터를 로드하고 분석하세요.
"""
        return enhanced_request
    
    def run(self):
        """워크플로우 실행"""
        try:
            from prometheus.graphs import PrometheusWorkflow, create_initial_state
            
            # 초기 상태 생성
            initial_state = create_initial_state(
                request=self.request,
                project_name=self.project_name,
            )
            
            trace_id = initial_state["trace_id"]
            self.workflow_started.emit(trace_id)
            
            # 워크플로우 생성
            workflow = PrometheusWorkflow(output_dir="runs")
            
            # 에이전트 순서
            agents = ["meta", "planner", "executor", "writer", "qa"]
            current_idx = 0
            
            # 스트리밍 실행
            final_state = None
            for event in workflow.stream(self.request, self.project_name):
                for node_name, node_output in event.items():
                    current_agent = node_output.get("current_agent", node_name)
                    
                    # 진행 상황 업데이트
                    if current_agent in agents:
                        current_idx = agents.index(current_agent) + 1
                    
                    self.progress_update.emit(
                        current_idx,
                        len(agents),
                        f"{current_agent.upper()} 처리 중..."
                    )
                    
                    # 에이전트 완료 시그널
                    self.agent_completed.emit(current_agent, node_output)
                    
                    final_state = node_output
            
            # 완료
            if final_state:
                self.workflow_completed.emit(final_state)
            
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
            self.workflow_error.emit(error_msg)


def format_workflow_result(state: Dict) -> str:
    """
    워크플로우 결과를 HTML로 포맷
    
    Args:
        state: 최종 State
    
    Returns:
        HTML 문자열
    """
    html = []
    
    # 제목
    html.append("<h2>🔗 NEXUS 실행 결과</h2>")
    
    # Meta 결정
    if state.get("meta_decision"):
        meta = state["meta_decision"]
        html.append("<h3>📋 Agent 구성</h3>")
        html.append("<ul>")
        for agent, llm in meta.get("llm_assignments", {}).items():
            html.append(f"<li><b>{agent}</b>: {llm}</li>")
        html.append("</ul>")
    
    # 계획
    if state.get("plan"):
        plan = state["plan"]
        html.append(f"<h3>📝 계획: {plan.get('task_summary', '')}</h3>")
        
        steps = plan.get("steps", [])
        if steps:
            html.append("<ol>")
            for step in steps:
                html.append(f"<li>{step.get('action', '')}</li>")
            html.append("</ol>")
    
    # 실행 결과
    if state.get("execution_result"):
        exec_result = state["execution_result"]
        html.append("<h3>⚡ 실행 결과</h3>")
        html.append(f"<p>✅ 성공: {exec_result.get('success_count', 0)}개 / "
                   f"❌ 실패: {exec_result.get('fail_count', 0)}개</p>")
    
    # 보고서
    if state.get("report"):
        report = state["report"]
        html.append(f"<h3>📄 {report.get('title', '보고서')}</h3>")
        html.append(f"<p><b>요약:</b> {report.get('summary', '')}</p>")
        
        content = report.get("content", "")
        if content:
            # 마크다운 간단 변환
            content = content.replace("\n", "<br>")
            html.append(f"<div>{content}</div>")
        
        conclusions = report.get("conclusions", [])
        if conclusions:
            html.append("<p><b>결론:</b></p><ul>")
            for c in conclusions:
                html.append(f"<li>{c}</li>")
            html.append("</ul>")
    
    # QA 결과
    if state.get("qa_result"):
        qa = state["qa_result"]
        grade = qa.get("grade", "N/A")
        score = qa.get("score", 0)
        html.append(f"<h3>🔍 QA 결과: {grade} ({score}점)</h3>")
        html.append(f"<p>{qa.get('summary', '')}</p>")
    
    # 에러
    if state.get("error"):
        html.append(f"<h3>❌ 에러</h3>")
        html.append(f"<p style='color:red;'>{state['error']}</p>")
    
    return "".join(html)


def format_agent_status(agent: str, result: Dict) -> str:
    """
    에이전트 상태를 짧은 문자열로 포맷
    
    Args:
        agent: 에이전트 이름
        result: 결과 딕셔너리
    
    Returns:
        상태 문자열
    """
    icons = {
        "meta": "🔍",
        "planner": "📋",
        "executor": "⚡",
        "writer": "✍️",
        "qa": "🔍",
        "error": "❌",
    }
    
    icon = icons.get(agent, "•")
    
    if agent == "planner" and result.get("plan"):
        summary = result["plan"].get("task_summary", "")[:30]
        return f"{icon} Planner: {summary}..."
    elif agent == "executor" and result.get("execution_result"):
        success = result["execution_result"].get("success_count", 0)
        return f"{icon} Executor: {success}개 단계 완료"
    elif agent == "writer" and result.get("report"):
        title = result["report"].get("title", "")[:30]
        return f"{icon} Writer: {title}"
    elif agent == "qa" and result.get("qa_result"):
        grade = result["qa_result"].get("grade", "N/A")
        score = result["qa_result"].get("score", 0)
        return f"{icon} QA: {grade} ({score}점)"
    else:
        return f"{icon} {agent.upper()} 완료"
