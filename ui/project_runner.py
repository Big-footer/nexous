"""
NEXUS Project Runner GUI 컴포넌트

project.yaml을 로드하고 실행하는 GUI 위젯
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QProgressBar, QTextEdit, QFrame, QScrollArea,
    QSplitter, QListWidget, QListWidgetItem, QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

# 색상 정의
COLORS = {
    'bg_white': '#FFFFFF',
    'bg_light': '#F7F7F8',
    'bg_gray': '#ECECF1',
    'text_primary': '#1A1A1A',
    'text_secondary': '#6B6B6B',
    'text_muted': '#8E8E93',
    'accent': '#8B5CF6',
    'accent_light': '#A78BFA',
    'success': '#10B981',
    'warning': '#F59E0B',
    'error': '#EF4444',
    'border': '#E5E5E5',
    'border_light': '#F0F0F0',
}


class ProjectWorker(QThread):
    """프로젝트 실행 워커 스레드"""
    
    started = pyqtSignal(str)  # project_id
    agent_started = pyqtSignal(str)  # agent_name
    agent_completed = pyqtSignal(str, bool)  # agent_name, success
    progress = pyqtSignal(int, int, str)  # current, total, message
    completed = pyqtSignal(dict)  # result
    error = pyqtSignal(str)  # error message
    
    def __init__(self, project_path: str, request: str = None, settings: dict = None):
        super().__init__()
        self.project_path = project_path
        self.request = request
        self.settings = settings or {}
    
    def _setup_api_keys(self):
        """설정에서 API 키를 환경변수로 설정"""
        import os
        api_keys = self.settings.get("api_keys", {})
        
        if api_keys.get("openai"):
            os.environ["OPENAI_API_KEY"] = api_keys["openai"]
        if api_keys.get("anthropic"):
            os.environ["ANTHROPIC_API_KEY"] = api_keys["anthropic"]
        if api_keys.get("google"):
            os.environ["GOOGLE_API_KEY"] = api_keys["google"]
    
    def run(self):
        try:
            # API 키 설정
            self._setup_api_keys()
            
            from prometheus.core import Project, ProjectRunner
            
            # 프로젝트 로드
            project = Project.from_yaml(self.project_path)
            self.started.emit(project.project_id)
            
            # Agent 목록
            agents = project.get_agent_names()
            total = len(agents)
            
            # 커스텀 러너로 진행 상황 추적
            runner = ProjectRunner()
            
            # 워크플로우 빌드
            workflow = runner.builder.build(project)
            
            # 초기 상태
            from langchain_core.messages import HumanMessage
            initial_state = {
                "request": self.request or project.config.description or "",
                "project_name": project.config.name,
                "messages": [HumanMessage(content=self.request or "")],
                "results": {},
                "inputs": project.config.inputs,
            }
            
            # 실행
            current_idx = 0
            final_state = None
            
            for event in workflow.stream(initial_state):
                for node_name, node_output in event.items():
                    self.agent_started.emit(node_name)
                    current_idx += 1
                    
                    success = "error" not in node_output
                    self.agent_completed.emit(node_name, success)
                    self.progress.emit(current_idx, total, f"{node_name} 완료")
                    
                    final_state = node_output
            
            # 결과 반환
            result = {
                "success": True,
                "project_id": project.project_id,
                "project_name": project.config.name,
                "results": final_state.get("results", {}) if final_state else {},
                "agents": agents,
            }
            
            self.completed.emit(result)
            
        except Exception as e:
            import traceback
            self.error.emit(f"{str(e)}\n\n{traceback.format_exc()}")


class AgentStatusWidget(QFrame):
    """Agent 상태 표시 위젯"""
    
    def __init__(self, agent_name: str, parent=None):
        super().__init__(parent)
        self.agent_name = agent_name
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_light']};
                border-radius: 8px;
                padding: 8px;
                margin: 2px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # 상태 아이콘
        self.status_icon = QLabel("⏳")
        self.status_icon.setStyleSheet("font-size: 16px;")
        layout.addWidget(self.status_icon)
        
        # Agent 이름
        self.name_label = QLabel(self.agent_name.upper())
        self.name_label.setStyleSheet(f"""
            font-weight: 600;
            font-size: 13px;
            color: {COLORS['text_primary']};
        """)
        layout.addWidget(self.name_label)
        
        layout.addStretch()
        
        # 상태 텍스트
        self.status_label = QLabel("대기 중")
        self.status_label.setStyleSheet(f"""
            font-size: 12px;
            color: {COLORS['text_muted']};
        """)
        layout.addWidget(self.status_label)
    
    def set_running(self):
        self.status_icon.setText("🔄")
        self.status_label.setText("실행 중...")
        self.status_label.setStyleSheet(f"font-size: 12px; color: {COLORS['warning']};")
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #FEF3C7;
                border-radius: 8px;
                border: 1px solid {COLORS['warning']};
            }}
        """)
    
    def set_completed(self, success: bool = True):
        if success:
            self.status_icon.setText("✅")
            self.status_label.setText("완료")
            self.status_label.setStyleSheet(f"font-size: 12px; color: {COLORS['success']};")
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: #D1FAE5;
                    border-radius: 8px;
                    border: 1px solid {COLORS['success']};
                }}
            """)
        else:
            self.status_icon.setText("❌")
            self.status_label.setText("실패")
            self.status_label.setStyleSheet(f"font-size: 12px; color: {COLORS['error']};")
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: #FEE2E2;
                    border-radius: 8px;
                    border: 1px solid {COLORS['error']};
                }}
            """)


class ProjectRunnerWidget(QWidget):
    """프로젝트 실행 위젯"""
    
    project_completed = pyqtSignal(dict)  # 완료 시그널
    
    def __init__(self, parent=None, settings: dict = None):
        super().__init__(parent)
        self.project_path: Optional[str] = None
        self.project_config: Optional[Dict] = None
        self.agent_widgets: Dict[str, AgentStatusWidget] = {}
        self.settings = settings or self._load_settings()
        self._setup_ui()
    
    def _load_settings(self) -> dict:
        """설정 로드"""
        from pathlib import Path
        import json
        config_path = Path.home() / ".prometheus" / "config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # 헤더
        header = QLabel("🔗 NEXUS 프로젝트 실행")
        header.setStyleSheet(f"""
            font-size: 20px;
            font-weight: bold;
            color: {COLORS['text_primary']};
        """)
        layout.addWidget(header)
        
        # 프로젝트 선택 영역
        select_frame = QFrame()
        select_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_light']};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        select_layout = QVBoxLayout(select_frame)
        
        # 파일 선택 버튼
        file_row = QHBoxLayout()
        
        self.file_label = QLabel("project.yaml을 선택하세요")
        self.file_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        file_row.addWidget(self.file_label, 1)
        
        self.select_btn = QPushButton("📂 파일 선택")
        self.select_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_btn.clicked.connect(self._select_project)
        self.select_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_gray']};
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {COLORS['border']};
            }}
        """)
        file_row.addWidget(self.select_btn)
        
        select_layout.addLayout(file_row)
        
        # 프로젝트 정보
        self.project_info = QLabel("")
        self.project_info.setStyleSheet(f"""
            font-size: 13px;
            color: {COLORS['text_secondary']};
            margin-top: 8px;
        """)
        self.project_info.setWordWrap(True)
        self.project_info.hide()
        select_layout.addWidget(self.project_info)
        
        layout.addWidget(select_frame)
        
        # Agent 상태 영역
        self.agents_frame = QFrame()
        self.agents_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_white']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 12px;
            }}
        """)
        self.agents_layout = QVBoxLayout(self.agents_frame)
        self.agents_layout.setContentsMargins(16, 16, 16, 16)
        self.agents_layout.setSpacing(8)
        
        agents_header = QLabel("Agent 실행 상태")
        agents_header.setStyleSheet(f"""
            font-weight: 600;
            font-size: 14px;
            color: {COLORS['text_primary']};
            margin-bottom: 8px;
        """)
        self.agents_layout.addWidget(agents_header)
        
        self.agents_frame.hide()
        layout.addWidget(self.agents_frame)
        
        # 진행률
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background-color: {COLORS['bg_gray']};
                height: 8px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent']};
                border-radius: 4px;
            }}
        """)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # 실행 버튼
        self.run_btn = QPushButton("▶️ 프로젝트 실행")
        self.run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.run_btn.setEnabled(False)
        self.run_btn.clicked.connect(self._run_project)
        self.run_btn.setFixedHeight(50)
        self.run_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_light']};
            }}
            QPushButton:disabled {{
                background-color: {COLORS['border']};
                color: {COLORS['text_muted']};
            }}
        """)
        layout.addWidget(self.run_btn)
        
        # 결과 영역
        self.result_frame = QFrame()
        self.result_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_light']};
                border-radius: 12px;
            }}
        """)
        result_layout = QVBoxLayout(self.result_frame)
        
        result_header = QLabel("📋 실행 결과")
        result_header.setStyleSheet(f"""
            font-weight: 600;
            font-size: 14px;
            color: {COLORS['text_primary']};
        """)
        result_layout.addWidget(result_header)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_white']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 8px;
                padding: 12px;
                font-family: monospace;
                font-size: 12px;
            }}
        """)
        self.result_text.setMinimumHeight(200)
        result_layout.addWidget(self.result_text)
        
        self.result_frame.hide()
        layout.addWidget(self.result_frame)
        
        layout.addStretch()
    
    def _select_project(self):
        """프로젝트 파일 선택"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "프로젝트 파일 선택",
            "",
            "YAML 파일 (*.yaml *.yml);;모든 파일 (*)"
        )
        
        if file_path:
            self._load_project(file_path)
    
    def _load_project(self, file_path: str):
        """프로젝트 로드"""
        try:
            from prometheus.core import Project
            
            project = Project.from_yaml(file_path)
            self.project_path = file_path
            self.project_config = project.config.model_dump()
            
            # UI 업데이트
            self.file_label.setText(f"📄 {os.path.basename(file_path)}")
            self.file_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 600;")
            
            # 프로젝트 정보
            agents = project.get_agent_names()
            info_text = f"""
<b>프로젝트:</b> {project.config.name}<br>
<b>유형:</b> {project.config.type.value}<br>
<b>Agent:</b> {', '.join(agents)}<br>
<b>설명:</b> {project.config.description or '없음'}
            """
            self.project_info.setText(info_text)
            self.project_info.show()
            
            # Agent 상태 위젯 생성
            self._create_agent_widgets(agents)
            
            self.run_btn.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"프로젝트 로드 실패:\n{e}")
    
    def _create_agent_widgets(self, agents: list):
        """Agent 상태 위젯 생성"""
        # 기존 위젯 제거
        for widget in self.agent_widgets.values():
            widget.deleteLater()
        self.agent_widgets.clear()
        
        # 새 위젯 생성
        for agent in agents:
            widget = AgentStatusWidget(agent)
            self.agents_layout.addWidget(widget)
            self.agent_widgets[agent] = widget
        
        self.agents_frame.show()
    
    def _run_project(self):
        """프로젝트 실행"""
        if not self.project_path:
            return
        
        # UI 상태 변경
        self.run_btn.setEnabled(False)
        self.run_btn.setText("⏳ 실행 중...")
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.result_frame.hide()
        
        # Agent 상태 초기화
        for widget in self.agent_widgets.values():
            widget.status_icon.setText("⏳")
            widget.status_label.setText("대기 중")
        
        # 워커 시작
        self.worker = ProjectWorker(
            self.project_path,
            self.project_config.get("description", ""),
            self.settings  # API 키 포함 설정 전달
        )
        self.worker.started.connect(self._on_started)
        self.worker.agent_started.connect(self._on_agent_started)
        self.worker.agent_completed.connect(self._on_agent_completed)
        self.worker.progress.connect(self._on_progress)
        self.worker.completed.connect(self._on_completed)
        self.worker.error.connect(self._on_error)
        self.worker.start()
    
    def _on_started(self, project_id: str):
        """실행 시작"""
        self.result_text.append(f"🚀 프로젝트 실행 시작: {project_id}\n")
    
    def _on_agent_started(self, agent_name: str):
        """Agent 실행 시작"""
        if agent_name in self.agent_widgets:
            self.agent_widgets[agent_name].set_running()
        self.result_text.append(f"🔄 {agent_name.upper()} 실행 중...")
    
    def _on_agent_completed(self, agent_name: str, success: bool):
        """Agent 완료"""
        if agent_name in self.agent_widgets:
            self.agent_widgets[agent_name].set_completed(success)
        status = "✅ 완료" if success else "❌ 실패"
        self.result_text.append(f"   {status}\n")
    
    def _on_progress(self, current: int, total: int, message: str):
        """진행 상황"""
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
    
    def _on_completed(self, result: dict):
        """실행 완료"""
        self.run_btn.setEnabled(True)
        self.run_btn.setText("▶️ 프로젝트 실행")
        self.progress_bar.setValue(100)
        self.result_frame.show()
        
        # 결과 표시
        self.result_text.append("\n" + "=" * 50)
        self.result_text.append("🎉 프로젝트 실행 완료!")
        self.result_text.append("=" * 50 + "\n")
        
        if result.get("results"):
            for agent, data in result["results"].items():
                self.result_text.append(f"\n📋 {agent.upper()} 결과:")
                if isinstance(data, dict):
                    for key, value in list(data.items())[:5]:
                        self.result_text.append(f"   • {key}: {str(value)[:100]}...")
        
        self.project_completed.emit(result)
    
    def _on_error(self, error: str):
        """에러 발생"""
        self.run_btn.setEnabled(True)
        self.run_btn.setText("▶️ 프로젝트 실행")
        self.result_frame.show()
        
        self.result_text.append("\n" + "=" * 50)
        self.result_text.append("❌ 오류 발생!")
        self.result_text.append("=" * 50)
        self.result_text.append(f"\n{error}")
        
        QMessageBox.critical(self, "실행 오류", f"프로젝트 실행 중 오류가 발생했습니다:\n\n{error[:500]}")
