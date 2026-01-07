"""
NEXUS Desktop App - 메인 윈도우 (Light Theme)

Claude 스타일의 독립 실행형 채팅 애플리케이션
"""

import sys
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import asyncio
import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QListWidget, QListWidgetItem, QTextEdit, QLineEdit,
    QPushButton, QLabel, QFrame, QScrollArea, QSizePolicy,
    QMenu, QMenuBar, QStatusBar, QToolBar, QMessageBox,
    QInputDialog, QFileDialog, QComboBox, QProgressBar,
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QSize, QTimer, QPropertyAnimation,
    QEasingCurve, QPoint,
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QIcon, QPixmap, QAction,
    QTextCursor, QPainter, QBrush, QPen, QLinearGradient,
)

# PROMETHEUS 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# LangGraph 워크플로우
from prometheus.graphs import PrometheusWorkflow, create_initial_state
from prometheus import __version__

# GUI 워크플로우 프로세서
from ui.workflow_processor import WorkflowProcessor, format_workflow_result, format_agent_status

# 설정 다이얼로그
from ui.settings_dialog import SettingsDialog


# =============================================================================
# 스타일 상수 - 밝은 테마
# =============================================================================
COLORS = {
    "bg_white": "#ffffff",
    "bg_light": "#f8f9fa",
    "bg_gray": "#e9ecef",
    "bg_sidebar": "#f1f3f5",
    "accent": "#5c6bc0",          # 인디고
    "accent_light": "#7986cb",
    "accent_dark": "#3f51b5",
    "text_primary": "#212529",
    "text_secondary": "#495057",
    "text_muted": "#868e96",
    "border": "#dee2e6",
    "border_light": "#e9ecef",
    "user_bubble": "#5c6bc0",     # 인디고
    "user_bubble_end": "#7c4dff", # 보라
    "assistant_bubble": "#ffffff",
    "success": "#2e7d32",
    "warning": "#f57c00",
    "error": "#c62828",
    "shadow": "rgba(0,0,0,0.1)",
}

STYLESHEET = f"""
QMainWindow {{
    background-color: {COLORS['bg_white']};
}}

QWidget {{
    background-color: {COLORS['bg_white']};
    color: {COLORS['text_primary']};
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Apple SD Gothic Neo', sans-serif;
    font-size: 14px;
}}

QSplitter::handle {{
    background-color: {COLORS['border_light']};
    width: 1px;
}}

QListWidget {{
    background-color: {COLORS['bg_sidebar']};
    border: none;
    border-radius: 0px;
    padding: 8px;
    outline: none;
}}

QListWidget::item {{
    background-color: transparent;
    color: {COLORS['text_primary']};
    padding: 12px 15px;
    border-radius: 10px;
    margin: 3px 5px;
}}

QListWidget::item:selected {{
    background-color: {COLORS['bg_gray']};
}}

QListWidget::item:hover {{
    background-color: {COLORS['bg_gray']};
}}

QLineEdit {{
    background-color: {COLORS['bg_white']};
    border: 2px solid {COLORS['border']};
    border-radius: 24px;
    padding: 14px 22px;
    font-size: 15px;
    color: {COLORS['text_primary']};
}}

QLineEdit:focus {{
    border-color: {COLORS['accent']};
}}

QLineEdit::placeholder {{
    color: {COLORS['text_muted']};
}}

QPushButton {{
    background-color: {COLORS['accent']};
    color: white;
    border: none;
    border-radius: 22px;
    padding: 12px 28px;
    font-weight: 600;
    font-size: 14px;
}}

QPushButton:hover {{
    background-color: {COLORS['accent_light']};
}}

QPushButton:pressed {{
    background-color: {COLORS['accent_dark']};
}}

QPushButton#sidebarBtn {{
    background-color: transparent;
    color: {COLORS['text_secondary']};
    text-align: left;
    padding: 12px 15px;
    border-radius: 10px;
    font-weight: normal;
}}

QPushButton#sidebarBtn:hover {{
    background-color: {COLORS['bg_gray']};
}}

QPushButton#newChatBtn {{
    background-color: {COLORS['bg_white']};
    color: {COLORS['text_primary']};
    border: 2px solid {COLORS['border']};
    border-radius: 10px;
    padding: 12px 20px;
    font-weight: 600;
}}

QPushButton#newChatBtn:hover {{
    background-color: {COLORS['bg_gray']};
    border-color: {COLORS['accent']};
}}

QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    border-radius: 4px;
    margin: 4px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['border']};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['text_muted']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QLabel#title {{
    font-size: 20px;
    font-weight: bold;
    color: {COLORS['accent']};
}}

QLabel#subtitle {{
    font-size: 12px;
    color: {COLORS['text_muted']};
}}

QStatusBar {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['text_secondary']};
    border-top: 1px solid {COLORS['border_light']};
}}

QMenuBar {{
    background-color: {COLORS['bg_white']};
    color: {COLORS['text_primary']};
    border-bottom: 1px solid {COLORS['border_light']};
    padding: 4px;
}}

QMenuBar::item {{
    padding: 6px 12px;
    border-radius: 6px;
}}

QMenuBar::item:selected {{
    background-color: {COLORS['bg_gray']};
}}

QMenu {{
    background-color: {COLORS['bg_white']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
    padding: 8px;
}}

QMenu::item {{
    padding: 10px 30px;
    border-radius: 6px;
}}

QMenu::item:selected {{
    background-color: {COLORS['bg_gray']};
}}

QComboBox {{
    background-color: {COLORS['bg_white']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px 15px;
    color: {COLORS['text_primary']};
}}

QComboBox::drop-down {{
    border: none;
    width: 30px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_white']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['bg_gray']};
}}
"""


# =============================================================================
# 메시지 버블 위젯
# =============================================================================
class MessageBubble(QFrame):
    """채팅 메시지 버블"""
    
    def __init__(
        self,
        message: str,
        is_user: bool = True,
        agent: str = "",
        timestamp: str = "",
        parent=None
    ):
        super().__init__(parent)
        self.is_user = is_user
        self.setup_ui(message, agent, timestamp)
    
    def setup_ui(self, message: str, agent: str, timestamp: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)
        
        # 메시지 컨테이너
        bubble = QFrame()
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(18, 14, 18, 14)
        bubble_layout.setSpacing(6)
        
        if self.is_user:
            bubble.setStyleSheet(f"""
                QFrame {{
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:1,
                        stop:0 {COLORS['user_bubble']},
                        stop:1 {COLORS['user_bubble_end']}
                    );
                    border-radius: 20px;
                    border-bottom-right-radius: 6px;
                }}
            """)
            text_color = "#ffffff"
            time_color = "rgba(255,255,255,0.7)"
        else:
            bubble.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['assistant_bubble']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 20px;
                    border-bottom-left-radius: 6px;
                }}
            """)
            text_color = COLORS['text_primary']
            time_color = COLORS['text_muted']
        
        # Agent 태그 (어시스턴트만)
        if not self.is_user and agent:
            agent_colors = {
                "Planner": "#3498db",
                "Executor": "#e74c3c",
                "Writer": "#27ae60",
                "Qa": "#9b59b6",
            }
            agent_color = agent_colors.get(agent, COLORS['accent'])
            
            agent_label = QLabel(f"🤖 {agent}")
            agent_label.setStyleSheet(f"""
                color: {agent_color};
                font-size: 12px;
                font-weight: 600;
            """)
            bubble_layout.addWidget(agent_label)
        
        # 메시지 텍스트
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setTextFormat(Qt.TextFormat.RichText)
        msg_label.setStyleSheet(f"""
            color: {text_color};
            font-size: 15px;
            line-height: 1.6;
        """)
        bubble_layout.addWidget(msg_label)
        
        # 타임스탬프
        if timestamp:
            time_label = QLabel(timestamp)
            time_label.setStyleSheet(f"""
                color: {time_color};
                font-size: 11px;
            """)
            time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            bubble_layout.addWidget(time_label)
        
        # 정렬
        container = QHBoxLayout()
        if self.is_user:
            container.addStretch()
            container.addWidget(bubble)
        else:
            container.addWidget(bubble)
            container.addStretch()
        
        bubble.setMaximumWidth(650)
        layout.addLayout(container)


# =============================================================================
# 프로젝트 목록 위젯
# =============================================================================
class ProjectListWidget(QWidget):
    """왼쪽 사이드바 - 프로젝트 목록"""
    
    project_selected = pyqtSignal(str)
    new_chat_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {COLORS['bg_sidebar']};")
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(15)
        
        # 헤더
        header = QHBoxLayout()
        header.setSpacing(10)
        
        logo_label = QLabel("🔗")
        logo_label.setStyleSheet("font-size: 32px; background: transparent;")
        header.addWidget(logo_label)
        
        title_container = QVBoxLayout()
        title_container.setSpacing(2)
        
        title = QLabel("NEXUS")
        title.setStyleSheet(f"""
            font-size: 20px;
            font-weight: bold;
            color: {COLORS['accent']};
            background: transparent;
        """)
        title_container.addWidget(title)
        
        version = QLabel(f"v{__version__}")
        version.setStyleSheet(f"""
            font-size: 11px;
            color: {COLORS['text_muted']};
            background: transparent;
        """)
        title_container.addWidget(version)
        
        header.addLayout(title_container)
        header.addStretch()
        
        layout.addLayout(header)
        
        # 새 대화 버튼
        new_chat_btn = QPushButton("＋ 새 대화")
        new_chat_btn.setObjectName("newChatBtn")
        new_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_chat_btn.clicked.connect(self.new_chat_requested.emit)
        layout.addWidget(new_chat_btn)
        
        # 프로젝트 실행 버튼 (NEW!)
        self.project_btn = QPushButton("📂 프로젝트 실행")
        self.project_btn.setObjectName("projectBtn")
        self.project_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.project_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_light']};
            }}
        """)
        layout.addWidget(self.project_btn)
        
        # 구분선
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {COLORS['border']};")
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        
        # 프로젝트 라벨
        projects_label = QLabel("💬 대화 기록")
        projects_label.setStyleSheet(f"""
            font-size: 13px;
            font-weight: 600;
            color: {COLORS['text_secondary']};
            padding: 5px 0;
            background: transparent;
        """)
        layout.addWidget(projects_label)
        
        # 프로젝트 리스트
        self.project_list = QListWidget()
        self.project_list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.project_list)
        
        # 하단 버튼들
        bottom_layout = QVBoxLayout()
        bottom_layout.setSpacing(5)
        
        settings_btn = QPushButton("⚙️  설정")
        settings_btn.setObjectName("sidebarBtn")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        bottom_layout.addWidget(settings_btn)
        
        help_btn = QPushButton("❓  도움말")
        help_btn.setObjectName("sidebarBtn")
        help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        bottom_layout.addWidget(help_btn)
        
        layout.addLayout(bottom_layout)
    
    def add_project(self, name: str, is_active: bool = False):
        """프로젝트 추가"""
        item = QListWidgetItem(f"💬  {name}")
        item.setData(Qt.ItemDataRole.UserRole, name)
        self.project_list.insertItem(0, item)
        
        if is_active:
            self.project_list.setCurrentItem(item)
    
    def _on_item_clicked(self, item: QListWidgetItem):
        project_name = item.data(Qt.ItemDataRole.UserRole)
        self.project_selected.emit(project_name)


# =============================================================================
# 채팅 영역 위젯
# =============================================================================
class ChatAreaWidget(QWidget):
    """메인 채팅 영역"""
    
    message_sent = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.messages: List[Dict] = []
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 헤더
        header = QFrame()
        header.setStyleSheet(f"""
            background-color: {COLORS['bg_white']};
            border-bottom: 1px solid {COLORS['border_light']};
        """)
        header.setFixedHeight(65)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(25, 12, 25, 12)
        
        self.chat_title = QLabel("새 대화")
        self.chat_title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 600;
            color: {COLORS['text_primary']};
        """)
        header_layout.addWidget(self.chat_title)
        
        header_layout.addStretch()
        
        # Agent 상태
        self.agent_status = QLabel("● 준비됨")
        self.agent_status.setStyleSheet(f"""
            font-size: 13px;
            color: {COLORS['success']};
            font-weight: 500;
        """)
        header_layout.addWidget(self.agent_status)
        
        layout.addWidget(header)
        
        # 메시지 스크롤 영역
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setStyleSheet(f"background-color: {COLORS['bg_light']};")
        
        self.messages_container = QWidget()
        self.messages_container.setStyleSheet(f"background-color: {COLORS['bg_light']};")
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(30, 30, 30, 30)
        self.messages_layout.setSpacing(15)
        self.messages_layout.addStretch()
        
        self.scroll_area.setWidget(self.messages_container)
        layout.addWidget(self.scroll_area)
        
        # 환영 메시지
        self.welcome_widget = self._create_welcome_widget()
        self.messages_layout.insertWidget(0, self.welcome_widget)
        
        # 입력 영역
        input_container = QFrame()
        input_container.setStyleSheet(f"""
            background-color: {COLORS['bg_white']};
            border-top: 1px solid {COLORS['border_light']};
        """)
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(25, 18, 25, 18)
        input_layout.setSpacing(12)
        
        # 파일 첨부 버튼
        self.attach_btn = QPushButton("📎")
        self.attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attach_btn.clicked.connect(self._attach_file)
        self.attach_btn.setFixedSize(48, 48)
        self.attach_btn.setToolTip("파일 첨부 (이미지, CSV, Excel, JSON 등)")
        self.attach_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_light']};
                color: {COLORS['text_primary']};
                border: 2px solid {COLORS['border']};
                border-radius: 24px;
                font-size: 20px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['bg_gray']};
                border-color: {COLORS['accent']};
            }}
        """)
        input_layout.addWidget(self.attach_btn)
        
        # 첨부 파일 표시 라벨 (숨김 상태로 시작)
        self.attached_file_label = QLabel("")
        self.attached_file_label.setStyleSheet(f"""
            color: {COLORS['accent']};
            font-size: 12px;
            padding: 5px 10px;
            background-color: {COLORS['bg_light']};
            border-radius: 10px;
        """)
        self.attached_file_label.hide()
        input_layout.addWidget(self.attached_file_label)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("메시지를 입력하세요...")
        self.input_field.returnPressed.connect(self._send_message)
        input_layout.addWidget(self.input_field, 1)  # stretch factor 추가
        
        self.send_btn = QPushButton("전송")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self._send_message)
        self.send_btn.setFixedSize(90, 48)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border: none;
                border-radius: 24px;
                font-weight: 600;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_light']};
            }}
        """)
        input_layout.addWidget(self.send_btn)
        
        layout.addWidget(input_container)
    
    def _create_welcome_widget(self) -> QWidget:
        """환영 메시지 위젯"""
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        
        # 로고
        logo = QLabel("🔗")
        logo.setStyleSheet("font-size: 72px; background: transparent;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)
        
        # 제목
        title = QLabel("NEXUS")
        title.setStyleSheet(f"""
            font-size: 32px;
            font-weight: bold;
            color: {COLORS['accent']};
            background: transparent;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # 설명
        desc = QLabel("Multi-Agent Orchestration Framework")
        desc.setStyleSheet(f"""
            font-size: 16px;
            color: {COLORS['text_secondary']};
            background: transparent;
        """)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        
        # 예시 카드들
        examples_container = QHBoxLayout()
        examples_container.setSpacing(15)
        examples_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        example_texts = [
            ("📊", "데이터 분석", "데이터 분석 보고서를\n작성해주세요"),
            ("🐍", "코드 실행", "Python으로 피보나치\n수열을 계산해주세요"),
            ("📋", "계획 수립", "프로젝트 계획을\n세워주세요"),
        ]
        
        for icon, title_text, desc_text in example_texts:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['bg_white']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 12px;
                }}
                QFrame:hover {{
                    border-color: {COLORS['accent']};
                    background-color: {COLORS['bg_gray']};
                }}
                QFrame QLabel {{
                    background-color: transparent;
                }}
            """)
            card.setFixedSize(200, 130)
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(15, 15, 15, 15)
            card_layout.setSpacing(8)
            
            icon_label = QLabel(icon)
            icon_label.setStyleSheet(f"font-size: 28px; color: {COLORS['accent']};")
            card_layout.addWidget(icon_label)
            
            title_label = QLabel(title_text)
            title_label.setStyleSheet(f"""
                font-size: 14px;
                font-weight: 600;
                color: {COLORS['text_primary']};
            """)
            card_layout.addWidget(title_label)
            
            desc_label = QLabel(desc_text)
            desc_label.setStyleSheet(f"""
                font-size: 12px;
                color: {COLORS['text_muted']};
            """)
            card_layout.addWidget(desc_label)
            
            examples_container.addWidget(card)
        
        layout.addLayout(examples_container)
        
        return widget
    
    def add_message(
        self,
        content: str,
        is_user: bool,
        agent: str = "",
    ):
        """메시지 추가"""
        # 환영 메시지 숨기기
        if self.welcome_widget.isVisible():
            self.welcome_widget.hide()
        
        timestamp = datetime.now().strftime("%H:%M")
        
        bubble = MessageBubble(
            message=content,
            is_user=is_user,
            agent=agent,
            timestamp=timestamp,
        )
        
        # stretch 전에 삽입
        count = self.messages_layout.count()
        self.messages_layout.insertWidget(count - 1, bubble)
        
        # 스크롤 맨 아래로
        QTimer.singleShot(100, self._scroll_to_bottom)
        
        self.messages.append({
            "content": content,
            "is_user": is_user,
            "agent": agent,
            "timestamp": timestamp,
        })
        
        return bubble  # 버블 반환 (스트리밍용)
    
    def start_streaming_message(self, agent: str = ""):
        """스트리밍 메시지 시작 - 빈 버블 생성"""
        if self.welcome_widget.isVisible():
            self.welcome_widget.hide()
        
        self.streaming_bubble = MessageBubble(
            message="",
            is_user=False,
            agent=agent,
            timestamp=datetime.now().strftime("%H:%M"),
        )
        
        count = self.messages_layout.count()
        self.messages_layout.insertWidget(count - 1, self.streaming_bubble)
        QTimer.singleShot(100, self._scroll_to_bottom)
        
        self.streaming_content = ""
        return self.streaming_bubble
    
    def append_streaming_chunk(self, chunk: str):
        """스트리밍 청크 추가"""
        if hasattr(self, 'streaming_bubble') and self.streaming_bubble:
            self.streaming_content += chunk
            # 버블 내용 업데이트
            msg_label = self.streaming_bubble.findChild(QLabel)
            if msg_label:
                # 텍스트 라벨 찾기 (여러 라벨 중 메시지 라벨)
                labels = self.streaming_bubble.findChildren(QLabel)
                for label in labels:
                    if label.wordWrap():  # 메시지 라벨은 wordWrap이 True
                        label.setText(self.streaming_content)
                        break
            QTimer.singleShot(50, self._scroll_to_bottom)
    
    def finish_streaming_message(self, final_content: str, agent: str):
        """스트리밍 완료 - 최종 메시지로 교체"""
        if hasattr(self, 'streaming_bubble') and self.streaming_bubble:
            # 기존 스트리밍 버블 제거
            self.streaming_bubble.deleteLater()
            self.streaming_bubble = None
        
        # 최종 메시지 추가
        self.messages.append({
            "content": final_content,
            "is_user": False,
            "agent": agent,
            "timestamp": datetime.now().strftime("%H:%M"),
        })
    
    def _scroll_to_bottom(self):
        """스크롤을 맨 아래로"""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _send_message(self):
        """메시지 전송"""
        text = self.input_field.text().strip()
        if text:
            self.input_field.clear()
            self.message_sent.emit(text)
    
    def _attach_file(self):
        """파일 첨부 다이얼로그"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "파일 선택",
            "",
            "모든 파일 (*);;이미지 (*.png *.jpg *.jpeg *.gif *.bmp);;데이터 (*.csv *.xlsx *.xls *.json);;텍스트 (*.txt *.md)"
        )
        
        if file_path:
            self.attached_file_path = file_path
            file_name = os.path.basename(file_path)
            self.attached_file_label.setText(f"📄 {file_name} ✕")
            self.attached_file_label.show()
            self.attached_file_label.setCursor(Qt.CursorShape.PointingHandCursor)
            self.attached_file_label.mousePressEvent = lambda e: self._remove_attached_file()
    
    def _remove_attached_file(self):
        """첨부 파일 제거"""
        self.attached_file_path = None
        self.attached_file_label.hide()
        self.attached_file_label.setText("")
    
    def get_attached_file(self) -> Optional[str]:
        """첨부된 파일 경로 반환"""
        return getattr(self, 'attached_file_path', None)
    
    def clear_attached_file(self):
        """첨부 파일 클리어"""
        self._remove_attached_file()
    
    def clear_messages(self):
        """메시지 클리어"""
        # 버블들 제거
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            if item.widget() and item.widget() != self.welcome_widget:
                item.widget().deleteLater()
        
        self.messages.clear()
        self.welcome_widget.show()
    
    def set_processing(self, is_processing: bool):
        """처리 중 상태 설정"""
        if is_processing:
            self.agent_status.setText("● 처리 중...")
            self.agent_status.setStyleSheet(f"""
                font-size: 13px;
                color: {COLORS['warning']};
                font-weight: 500;
            """)
            self.send_btn.setEnabled(False)
            self.send_btn.setStyleSheet(f"""
                background-color: {COLORS['border']};
                color: {COLORS['text_muted']};
                border: none;
                border-radius: 22px;
                padding: 12px 28px;
                font-weight: 600;
            """)
        else:
            self.agent_status.setText("● 준비됨")
            self.agent_status.setStyleSheet(f"""
                font-size: 13px;
                color: {COLORS['success']};
                font-weight: 500;
            """)
            self.send_btn.setEnabled(True)
            self.send_btn.setStyleSheet(f"""
                background-color: {COLORS['accent']};
                color: white;
                border: none;
                border-radius: 22px;
                padding: 12px 28px;
                font-weight: 600;
            """)


# =============================================================================
# 메시지 처리 스레드 (스트리밍 지원)
# =============================================================================
class MessageProcessor(QThread):
    """비동기 메시지 처리 - 스트리밍 지원"""
    
    response_ready = pyqtSignal(str, str)  # content, agent (최종 완료)
    error_occurred = pyqtSignal(str)
    stream_chunk = pyqtSignal(str)  # 스트리밍 청크
    stream_started = pyqtSignal(str)  # 스트리밍 시작 (agent 이름)
    stream_finished = pyqtSignal()  # 스트리밍 완료
    
    CONFIG_PATH = Path.home() / ".prometheus" / "config.json"
    
    def __init__(self, message: str, conversation_history: List[Dict], settings: Dict = None):
        super().__init__()
        self.message = message
        self.conversation_history = conversation_history
        self.settings = settings or self._load_settings()
        self.use_streaming = self.settings.get("general", {}).get("streaming", True)
    
    def _load_settings(self) -> Dict:
        """설정 로드"""
        if self.CONFIG_PATH.exists():
            try:
                with open(self.CONFIG_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._process())
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            loop.close()
    
    async def _process(self):
        """실제 LLM으로 메시지 처리"""
        provider = self.settings.get("model", {}).get("provider", "OpenAI")
        model = self.settings.get("model", {}).get("model", "gpt-4o-mini")
        api_key = self.settings.get("api_keys", {}).get(provider.lower(), "")
        system_prompt = self.settings.get("general", {}).get(
            "system_prompt", 
            "당신은 NEXUS의 AI 어시스턴트입니다. 친절하고 정확하게 응답해주세요."
        )
        temperature = self.settings.get("model", {}).get("temperature", 0.7)
        max_tokens = self.settings.get("model", {}).get("max_tokens", 2000)
        
        # API 키가 없으면 기본 응답
        if not api_key:
            self.response_ready.emit(
                "⚠️ <b>API 키가 설정되지 않았습니다</b><br><br>"
                "설정 메뉴에서 API 키를 입력해주세요.",
                "System"
            )
            return
        
        # 대화 기록 구성
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # 이전 대화 추가 (최근 10개)
        for msg in self.conversation_history[-10:]:
            role = "user" if msg.get("is_user") else "assistant"
            content = msg.get("content", "")
            import re
            content = re.sub(r'<[^>]+>', '', content)
            messages.append({"role": role, "content": content})
        
        messages.append({"role": "user", "content": self.message})
        
        try:
            self.stream_started.emit(provider)
            
            if self.use_streaming:
                # 스트리밍 모드
                full_content = ""
                if provider == "OpenAI":
                    async for chunk in self._stream_openai(api_key, model, messages, temperature, max_tokens):
                        full_content += chunk
                        self.stream_chunk.emit(chunk)
                elif provider == "Anthropic":
                    async for chunk in self._stream_anthropic(api_key, model, messages, temperature, max_tokens):
                        full_content += chunk
                        self.stream_chunk.emit(chunk)
                elif provider == "Google":
                    async for chunk in self._stream_google(api_key, model, messages, temperature, max_tokens):
                        full_content += chunk
                        self.stream_chunk.emit(chunk)
                
                self.stream_finished.emit()
                content = self._markdown_to_html(full_content)
                self.response_ready.emit(content, provider)
            else:
                # 일반 모드
                if provider == "OpenAI":
                    content = await self._call_openai(api_key, model, messages, temperature, max_tokens)
                elif provider == "Anthropic":
                    content = await self._call_anthropic(api_key, model, messages, temperature, max_tokens)
                elif provider == "Google":
                    content = await self._call_google(api_key, model, messages, temperature, max_tokens)
                else:
                    content = "지원하지 않는 provider입니다."
                
                content = self._markdown_to_html(content)
                self.response_ready.emit(content, provider)
                
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    # =========================================================================
    # 스트리밍 API 호출
    # =========================================================================
    async def _stream_openai(self, api_key: str, model: str, messages: List, temperature: float, max_tokens: int):
        """OpenAI 스트리밍"""
        import openai
        client = openai.OpenAI(api_key=api_key)
        
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def _stream_anthropic(self, api_key: str, model: str, messages: List, temperature: float, max_tokens: int):
        """Anthropic 스트리밍"""
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        system = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                chat_messages.append(msg)
        
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=chat_messages,
        ) as stream:
            for text in stream.text_stream:
                yield text
    
    async def _stream_google(self, api_key: str, model: str, messages: List, temperature: float, max_tokens: int):
        """Google Gemini 스트리밍"""
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        gen_model = genai.GenerativeModel(model)
        
        history = []
        for msg in messages[:-1]:
            if msg["role"] == "user":
                history.append({"role": "user", "parts": [msg["content"]]})
            elif msg["role"] == "assistant":
                history.append({"role": "model", "parts": [msg["content"]]})
        
        chat = gen_model.start_chat(history=history)
        response = chat.send_message(messages[-1]["content"], stream=True)
        
        for chunk in response:
            if chunk.text:
                yield chunk.text
    
    # =========================================================================
    # 일반 API 호출 (스트리밍 비활성화 시)
    # =========================================================================
    
    async def _call_openai(self, api_key: str, model: str, messages: List, temperature: float, max_tokens: int) -> str:
        """OpenAI API 호출"""
        import openai
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        return response.choices[0].message.content
    
    async def _call_anthropic(self, api_key: str, model: str, messages: List, temperature: float, max_tokens: int) -> str:
        """Anthropic API 호출"""
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        # system 메시지 분리
        system = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                chat_messages.append(msg)
        
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=chat_messages,
        )
        
        return response.content[0].text
    
    async def _call_google(self, api_key: str, model: str, messages: List, temperature: float, max_tokens: int) -> str:
        """Google Gemini API 호출"""
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        gen_model = genai.GenerativeModel(model)
        
        # 대화 기록을 Gemini 형식으로 변환
        history = []
        for msg in messages[:-1]:  # 마지막 메시지 제외
            if msg["role"] == "user":
                history.append({"role": "user", "parts": [msg["content"]]})
            elif msg["role"] == "assistant":
                history.append({"role": "model", "parts": [msg["content"]]})
        
        chat = gen_model.start_chat(history=history)
        response = chat.send_message(messages[-1]["content"])
        
        return response.text
    
    def _markdown_to_html(self, text: str) -> str:
        """간단한 마크다운 -> HTML 변환"""
        import re
        
        # 코드 블록
        text = re.sub(r'```(\w+)?\n(.*?)```', r'<pre style="background-color: #f5f5f5; padding: 12px; border-radius: 8px; overflow-x: auto;">\2</pre>', text, flags=re.DOTALL)
        
        # 인라인 코드
        text = re.sub(r'`([^`]+)`', r'<code style="background-color: #f0f0f0; padding: 2px 6px; border-radius: 4px;">\1</code>', text)
        
        # 볼드
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        
        # 이탤릭
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        
        # 줄바꿈
        text = text.replace('\n', '<br>')
        
        return text


# =============================================================================
# 메인 윈도우
# =============================================================================
class MainWindow(QMainWindow):
    """NEXUS 메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.conversations: Dict[str, List] = {}
        self.current_conversation = None
        self.processor = None
        self.settings = self._load_settings()
        
        self.setup_ui()
        self.setup_menu()
        self.create_new_chat()
        self._connect_sidebar_settings()
        self._update_status_bar()  # 현재 AI 표시
    
    def _load_settings(self) -> Dict:
        """설정 로드"""
        config_path = Path.home() / ".prometheus" / "config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _connect_sidebar_settings(self):
        """사이드바 설정 버튼 연결"""
        # 사이드바의 설정 버튼 찾기
        for child in self.sidebar.findChildren(QPushButton):
            if "설정" in child.text():
                child.clicked.connect(self.show_settings)
            elif "프로젝트" in child.text():
                child.clicked.connect(self.show_project_runner)
    
    def setup_ui(self):
        """UI 설정"""
        self.setWindowTitle("🔗 NEXUS")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # 스타일시트 적용
        self.setStyleSheet(STYLESHEET)
        
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 스플리터
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 왼쪽 사이드바
        self.sidebar = ProjectListWidget()
        self.sidebar.setFixedWidth(280)
        self.sidebar.project_selected.connect(self._on_project_selected)
        self.sidebar.new_chat_requested.connect(self.create_new_chat)
        splitter.addWidget(self.sidebar)
        
        # 오른쪽 채팅 영역
        self.chat_area = ChatAreaWidget()
        self.chat_area.message_sent.connect(self._on_message_sent)
        splitter.addWidget(self.chat_area)
        
        # 스플리터 비율
        splitter.setSizes([280, 1120])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        
        # 상태바
        self.statusBar().showMessage("준비됨")
    
    def setup_menu(self):
        """메뉴 설정"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu("파일")
        
        new_action = QAction("새 대화", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.create_new_chat)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("대화 내보내기...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_conversation)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        quit_action = QAction("종료", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # 프로젝트 메뉴 (NEW!)
        project_menu = menubar.addMenu("프로젝트")
        
        run_project_action = QAction("📂 프로젝트 실행...", self)
        run_project_action.setShortcut("Ctrl+P")
        run_project_action.triggered.connect(self.show_project_runner)
        project_menu.addAction(run_project_action)
        
        project_menu.addSeparator()
        
        new_project_action = QAction("새 프로젝트 생성...", self)
        new_project_action.triggered.connect(self.create_new_project)
        project_menu.addAction(new_project_action)
        
        project_menu.addSeparator()
        
        view_traces_action = QAction("실행 기록 보기", self)
        view_traces_action.triggered.connect(self.show_traces)
        project_menu.addAction(view_traces_action)
        
        view_artifacts_action = QAction("결과물 보기", self)
        view_artifacts_action.triggered.connect(self.show_artifacts)
        project_menu.addAction(view_artifacts_action)
        
        # 편집 메뉴
        edit_menu = menubar.addMenu("편집")
        
        clear_action = QAction("대화 지우기", self)
        clear_action.triggered.connect(self.clear_current_chat)
        edit_menu.addAction(clear_action)
        
        edit_menu.addSeparator()
        
        settings_action = QAction("설정...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.show_settings)
        edit_menu.addAction(settings_action)
        
        # 도움말 메뉴
        help_menu = menubar.addMenu("도움말")
        
        about_action = QAction("NEXUS 정보", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_new_chat(self):
        """새 대화 생성"""
        chat_id = f"대화 {len(self.conversations) + 1}"
        self.conversations[chat_id] = []
        self.current_conversation = chat_id
        
        self.sidebar.add_project(chat_id, is_active=True)
        self.chat_area.clear_messages()
        self.chat_area.chat_title.setText(chat_id)
        
        self.statusBar().showMessage(f"새 대화 생성됨: {chat_id}")
    
    def _on_project_selected(self, project_name: str):
        """프로젝트 선택 시"""
        self.current_conversation = project_name
        self.chat_area.chat_title.setText(project_name)
        
        # 메시지 복원
        self.chat_area.clear_messages()
        messages = self.conversations.get(project_name, [])
        for msg in messages:
            self.chat_area.add_message(
                msg["content"],
                msg["is_user"],
                msg.get("agent", "")
            )
    
    def _on_message_sent(self, message: str):
        """메시지 전송 시"""
        # 첨부 파일 확인
        attached_file = self.chat_area.get_attached_file()
        
        # 첨부 파일이 있으면 메시지에 추가
        if attached_file:
            file_name = os.path.basename(attached_file)
            display_message = f"📎 {file_name}\n\n{message}"
            full_message = f"[첨부파일: {attached_file}]\n\n{message}"
            self.chat_area.clear_attached_file()
        else:
            display_message = message
            full_message = message
        
        # 사용자 메시지 추가
        self.chat_area.add_message(display_message, is_user=True)
        
        if self.current_conversation:
            self.conversations[self.current_conversation].append({
                "content": display_message,
                "is_user": True,
            })
        
        # 처리 시작
        self.chat_area.set_processing(True)
        self.statusBar().showMessage("🔗 Multi-Agent 워크플로우 시작...")
        
        # 항상 Multi-Agent 워크플로우 사용 (첨부파일 경로 포함)
        self._run_multiagent_workflow(full_message, attached_file)
        
        # 스트리밍 신호 연결
    def _run_single_llm(self, message: str):
        """단일 LLM 모드 실행"""
        # 현재 대화 기록 가져오기
        history = self.conversations.get(self.current_conversation, [])
        
        # 비동기 처리 - 실제 LLM 사용 (스트리밍)
        self.processor = MessageProcessor(message, history[:-1], self.settings)
        
        # 스트리밍 신호 연결
        self.processor.stream_started.connect(self._on_stream_started)
        self.processor.stream_chunk.connect(self._on_stream_chunk)
        self.processor.stream_finished.connect(self._on_stream_finished)
        self.processor.response_ready.connect(self._on_response_ready)
        self.processor.error_occurred.connect(self._on_error)
        self.processor.start()
    
    def _run_multiagent_workflow(self, message: str, attached_file: str = None):
        """Multi-Agent 워크플로우 실행"""
        from ui.workflow_processor import WorkflowProcessor, format_workflow_result, format_agent_status
        
        project_name = self.current_conversation or "unnamed"
        
        self.workflow_processor = WorkflowProcessor(
            request=message,
            project_name=project_name,
            settings=self.settings,
            attached_file=attached_file,
        )
        
        # 시그널 연결
        self.workflow_processor.workflow_started.connect(self._on_workflow_started)
        self.workflow_processor.agent_completed.connect(self._on_agent_completed)
        self.workflow_processor.workflow_completed.connect(self._on_workflow_completed)
        self.workflow_processor.workflow_error.connect(self._on_workflow_error)
        self.workflow_processor.progress_update.connect(self._on_workflow_progress)
        
        self.workflow_processor.start()
    
    def _on_workflow_started(self, trace_id: str):
        """워크플로우 시작"""
        self.statusBar().showMessage(f"🔗 Multi-Agent 실행 중... (ID: {trace_id[:8]})")
    
    def _on_agent_completed(self, agent: str, result: dict):
        """에이전트 완료"""
        from ui.workflow_processor import format_agent_status
        status = format_agent_status(agent, result)
        self.statusBar().showMessage(status)
    
    def _on_workflow_progress(self, current: int, total: int, message: str):
        """워크플로우 진행 상황"""
        self.statusBar().showMessage(f"[{current}/{total}] {message}")
    
    def _on_workflow_completed(self, final_state: dict):
        """워크플로우 완료"""
        from ui.workflow_processor import format_workflow_result
        
        # HTML 형식 결과 생성
        content = format_workflow_result(final_state)
        
        # 메시지 추가
        self.chat_area.add_message(content, is_user=False, agent="NEXUS")
        
        if self.current_conversation:
            self.conversations[self.current_conversation].append({
                "content": content,
                "is_user": False,
                "agent": "PROMETHEUS",
            })
        
        self.chat_area.set_processing(False)
        self._update_status_bar()
    
    def _on_workflow_error(self, error_msg: str):
        """워크플로우 에러"""
        self.chat_area.add_message(
            f"❌ Multi-Agent 오류:\n{error_msg}",
            is_user=False,
            agent="System"
        )
        self.chat_area.set_processing(False)
        self._update_status_bar()
    
    def _on_stream_started(self, agent: str):
        """스트리밍 시작"""
        self.chat_area.start_streaming_message(agent)
        self.statusBar().showMessage(f"🤖 {agent} 응답 중...")
    
    def _on_stream_chunk(self, chunk: str):
        """스트리밍 청크 수신"""
        self.chat_area.append_streaming_chunk(chunk)
    
    def _on_stream_finished(self):
        """스트리밍 완료"""
        pass  # response_ready에서 처리
    
    def _on_response_ready(self, content: str, agent: str):
        """응답 준비 완료"""
        # 스트리밍 버블이 있으면 완료 처리
        if hasattr(self.chat_area, 'streaming_bubble') and self.chat_area.streaming_bubble:
            self.chat_area.finish_streaming_message(content, agent)
            # 최종 버블 추가 (HTML 형식)
            self.chat_area.add_message(content, is_user=False, agent=agent)
        else:
            # 스트리밍 아닌 경우
            self.chat_area.add_message(content, is_user=False, agent=agent)
        
        if self.current_conversation:
            self.conversations[self.current_conversation].append({
                "content": content,
                "is_user": False,
                "agent": agent,
            })
        
        self.chat_area.set_processing(False)
        self._update_status_bar()
    
    def _on_error(self, error_msg: str):
        """에러 발생"""
        # 스트리밍 버블이 있으면 제거
        if hasattr(self.chat_area, 'streaming_bubble') and self.chat_area.streaming_bubble:
            self.chat_area.streaming_bubble.deleteLater()
            self.chat_area.streaming_bubble = None
        
        self.chat_area.add_message(
            f"❌ 오류가 발생했습니다: {error_msg}",
            is_user=False,
            agent="System"
        )
        self.chat_area.set_processing(False)
        self._update_status_bar()
    
    def clear_current_chat(self):
        """현재 대화 지우기"""
        if self.current_conversation:
            self.conversations[self.current_conversation] = []
            self.chat_area.clear_messages()
    
    def export_conversation(self):
        """대화 내보내기"""
        if not self.current_conversation:
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "대화 내보내기",
            f"{self.current_conversation}.json",
            "JSON Files (*.json)"
        )
        
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(
                    self.conversations[self.current_conversation],
                    f,
                    ensure_ascii=False,
                    indent=2
                )
            self.statusBar().showMessage(f"저장됨: {filename}")
    
    def show_about(self):
        """정보 다이얼로그"""
        QMessageBox.about(
            self,
            "NEXUS 정보",
            f"""<h2>🔗 NEXUS</h2>
<p>Version: {__version__}</p>
<p>Multi-Agent Orchestration Framework</p>
<br>
<p><b>Agents:</b></p>
<ul>
<li>📋 Planner - 작업 계획 수립</li>
<li>⚡ Executor - 작업 실행</li>
<li>✍️ Writer - 문서 작성</li>
<li>🔍 QA - 품질 검토</li>
</ul>
<br>
<p>Made with ❤️ by PROMETHEUS Team</p>
"""
        )
    
    def show_settings(self):
        """설정 다이얼로그 열기"""
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()
    
    def _on_settings_changed(self, settings: Dict):
        """설정 변경 시"""
        self.settings = settings
        self._update_status_bar()
    
    def _update_status_bar(self):
        """상태바에 현재 AI 표시"""
        provider = self.settings.get("model", {}).get("provider", "미설정")
        model = self.settings.get("model", {}).get("model", "미설정")
        api_key = self.settings.get("api_keys", {}).get(provider.lower(), "")
        
        if api_key:
            self.statusBar().showMessage(f"🤖 {provider} / {model} 사용 중")
        else:
            self.statusBar().showMessage("⚠️ API 키 미설정 - 설정에서 API 키를 입력하세요")
    
    # =========================================================================
    # 프로젝트 관련 메서드
    # =========================================================================
    
    def show_project_runner(self):
        """프로젝트 실행 다이얼로그"""
        from ui.project_runner import ProjectRunnerWidget
        from PyQt6.QtWidgets import QDialog, QVBoxLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("🔗 NEXUS 프로젝트 실행")
        dialog.setMinimumSize(700, 600)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        
        runner = ProjectRunnerWidget()
        runner.project_completed.connect(lambda result: self._on_project_completed(result, dialog))
        layout.addWidget(runner)
        
        dialog.exec()
    
    def _on_project_completed(self, result: dict, dialog):
        """프로젝트 완료 시"""
        if result.get("success"):
            # 결과를 채팅에 표시
            summary = f"""## 🎉 프로젝트 실행 완료!

**프로젝트:** {result.get('project_name', 'Unknown')}
**Trace ID:** {result.get('trace_id', 'N/A')}

### 실행 결과
"""
            for agent, data in result.get("results", {}).items():
                summary += f"\n**{agent.upper()}**: 완료 ✅"
            
            self.chat_area.add_message(summary, is_user=False, agent="NEXUS")
    
    def create_new_project(self):
        """새 프로젝트 생성"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QTextEdit, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("새 프로젝트 생성")
        dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(dialog)
        
        form = QFormLayout()
        
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("프로젝트 이름")
        form.addRow("이름:", name_edit)
        
        type_combo = QComboBox()
        type_combo.addItems(["general", "academic_paper", "data_analysis", "simulation"])
        form.addRow("유형:", type_combo)
        
        desc_edit = QTextEdit()
        desc_edit.setPlaceholderText("프로젝트 설명...")
        desc_edit.setMaximumHeight(100)
        form.addRow("설명:", desc_edit)
        
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(lambda: self._save_new_project(dialog, name_edit.text(), type_combo.currentText(), desc_edit.toPlainText()))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.exec()
    
    def _save_new_project(self, dialog, name: str, proj_type: str, description: str):
        """새 프로젝트 저장"""
        if not name:
            QMessageBox.warning(self, "경고", "프로젝트 이름을 입력하세요.")
            return
        
        # project.yaml 생성
        yaml_content = f"""name: {name}
type: {proj_type}
description: |
  {description}

agents:
  - planner
  - executor
  - writer
  - qa

output:
  format: markdown
"""
        
        # 파일 저장
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "프로젝트 저장",
            f"{name}.yaml",
            "YAML 파일 (*.yaml)"
        )
        
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
            
            QMessageBox.information(self, "성공", f"프로젝트가 저장되었습니다:\n{file_path}")
            dialog.accept()
    
    def show_traces(self):
        """실행 기록 보기"""
        from prometheus.core import get_trace_store
        
        store = get_trace_store()
        traces = store.list_recent(20)
        
        if not traces:
            QMessageBox.information(self, "실행 기록", "실행 기록이 없습니다.")
            return
        
        # 간단한 목록 표시
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget
        
        dialog = QDialog(self)
        dialog.setWindowTitle("📋 실행 기록")
        dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(dialog)
        
        list_widget = QListWidget()
        for trace in traces:
            item_text = f"[{trace.get('status', 'unknown')}] {trace.get('project_name', 'Unknown')} - {trace.get('trace_id', '')}"
            list_widget.addItem(item_text)
        
        layout.addWidget(list_widget)
        dialog.exec()
    
    def show_artifacts(self):
        """결과물 보기"""
        from prometheus.core import get_artifact_manager
        
        am = get_artifact_manager()
        artifacts = am.list_all()
        
        if not artifacts:
            QMessageBox.information(self, "결과물", "결과물이 없습니다.")
            return
        
        # 간단한 목록 표시
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget
        
        dialog = QDialog(self)
        dialog.setWindowTitle("📦 결과물")
        dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(dialog)
        
        list_widget = QListWidget()
        for artifact in artifacts:
            item_text = f"[{artifact.type.value}] {artifact.name} - {artifact.created_by or 'Unknown'}"
            list_widget.addItem(item_text)
        
        layout.addWidget(list_widget)
        dialog.exec()


# =============================================================================
# 메인 실행
# =============================================================================
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PROMETHEUS")
    app.setApplicationVersion(__version__)
    
    # 라이트 팔레트
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(COLORS['bg_white']))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(COLORS['text_primary']))
    palette.setColor(QPalette.ColorRole.Base, QColor(COLORS['bg_white']))
    palette.setColor(QPalette.ColorRole.Text, QColor(COLORS['text_primary']))
    palette.setColor(QPalette.ColorRole.Button, QColor(COLORS['bg_light']))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(COLORS['text_primary']))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(COLORS['accent']))
    app.setPalette(palette)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
