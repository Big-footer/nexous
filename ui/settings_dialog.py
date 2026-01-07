"""
PROMETHEUS 설정 다이얼로그

API 키 및 모델 설정을 관리합니다.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QPushButton, QLabel,
    QTabWidget, QWidget, QGroupBox, QCheckBox,
    QSpinBox, QMessageBox, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


# 색상 상수
COLORS = {
    "bg_white": "#ffffff",
    "bg_light": "#f8f9fa",
    "bg_gray": "#e9ecef",
    "accent": "#5c6bc0",
    "accent_light": "#7986cb",
    "text_primary": "#212529",
    "text_secondary": "#495057",
    "text_muted": "#868e96",
    "border": "#dee2e6",
    "success": "#2e7d32",
    "error": "#c62828",
}


class SettingsDialog(QDialog):
    """설정 다이얼로그"""
    
    settings_changed = pyqtSignal(dict)
    
    # 설정 파일 경로
    CONFIG_PATH = Path.home() / ".prometheus" / "config.json"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = self.load_settings()
        self.setup_ui()
        self.load_ui_from_settings()
    
    def setup_ui(self):
        """UI 설정"""
        self.setWindowTitle("⚙️ PROMETHEUS 설정")
        self.setMinimumSize(600, 650)
        self.resize(650, 700)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_white']};
            }}
            QLabel {{
                color: {COLORS['text_primary']};
                font-size: 13px;
            }}
            QLineEdit {{
                background-color: {COLORS['bg_white']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 13px;
                color: {COLORS['text_primary']};
            }}
            QLineEdit:focus {{
                border-color: {COLORS['accent']};
            }}
            QComboBox {{
                background-color: {COLORS['bg_white']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 13px;
                color: {COLORS['text_primary']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QGroupBox {{
                font-weight: bold;
                font-size: 14px;
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 15px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }}
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 25px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_light']};
            }}
            QPushButton#cancelBtn {{
                background-color: {COLORS['bg_gray']};
                color: {COLORS['text_primary']};
            }}
            QPushButton#cancelBtn:hover {{
                background-color: {COLORS['border']};
            }}
            QPushButton#testBtn {{
                background-color: {COLORS['success']};
                color: white;
                padding: 10px 20px;
                min-height: 20px;
            }}
            QPushButton#testBtn:hover {{
                background-color: #388e3c;
            }}
            QTabWidget::pane {{
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                background-color: {COLORS['bg_white']};
            }}
            QTabBar::tab {{
                background-color: {COLORS['bg_light']};
                color: {COLORS['text_secondary']};
                padding: 10px 20px;
                margin-right: 5px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS['bg_white']};
                color: {COLORS['accent']};
                font-weight: bold;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)
        
        # 헤더
        header = QLabel("⚙️ 설정")
        header.setStyleSheet(f"""
            font-size: 22px;
            font-weight: bold;
            color: {COLORS['accent']};
        """)
        layout.addWidget(header)
        
        # 탭 위젯
        tabs = QTabWidget()
        
        # API 탭
        api_tab = self._create_api_tab()
        tabs.addTab(api_tab, "🔑 API 설정")
        
        # 모델 탭
        model_tab = self._create_model_tab()
        tabs.addTab(model_tab, "🤖 모델 설정")
        
        # 일반 탭
        general_tab = self._create_general_tab()
        tabs.addTab(general_tab, "📋 일반")
        
        layout.addWidget(tabs)
        
        # 버튼 영역
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("취소")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("저장")
        save_btn.clicked.connect(self.save_and_close)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def _create_api_tab(self) -> QWidget:
        """API 설정 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # OpenAI
        openai_group = QGroupBox("OpenAI")
        openai_layout = QVBoxLayout(openai_group)
        openai_layout.setSpacing(10)
        
        openai_label = QLabel("API Key:")
        openai_layout.addWidget(openai_label)
        
        self.openai_key = QLineEdit()
        self.openai_key.setPlaceholderText("sk-...")
        self.openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key.setMinimumWidth(400)
        openai_layout.addWidget(self.openai_key)
        
        openai_test_btn = QPushButton("연결 테스트")
        openai_test_btn.setObjectName("testBtn")
        openai_test_btn.setFixedWidth(120)
        openai_test_btn.clicked.connect(lambda: self.test_api("openai"))
        openai_layout.addWidget(openai_test_btn)
        
        layout.addWidget(openai_group)
        
        # Anthropic
        anthropic_group = QGroupBox("Anthropic (Claude)")
        anthropic_layout = QVBoxLayout(anthropic_group)
        anthropic_layout.setSpacing(10)
        
        anthropic_label = QLabel("API Key:")
        anthropic_layout.addWidget(anthropic_label)
        
        self.anthropic_key = QLineEdit()
        self.anthropic_key.setPlaceholderText("sk-ant-...")
        self.anthropic_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.anthropic_key.setMinimumWidth(400)
        anthropic_layout.addWidget(self.anthropic_key)
        
        anthropic_test_btn = QPushButton("연결 테스트")
        anthropic_test_btn.setObjectName("testBtn")
        anthropic_test_btn.setFixedWidth(120)
        anthropic_test_btn.clicked.connect(lambda: self.test_api("anthropic"))
        anthropic_layout.addWidget(anthropic_test_btn)
        
        layout.addWidget(anthropic_group)
        
        # Google
        google_group = QGroupBox("Google (Gemini)")
        google_layout = QVBoxLayout(google_group)
        google_layout.setSpacing(10)
        
        google_label = QLabel("API Key:")
        google_layout.addWidget(google_label)
        
        self.google_key = QLineEdit()
        self.google_key.setPlaceholderText("AIza...")
        self.google_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.google_key.setMinimumWidth(400)
        google_layout.addWidget(self.google_key)
        
        google_test_btn = QPushButton("연결 테스트")
        google_test_btn.setObjectName("testBtn")
        google_test_btn.setFixedWidth(120)
        google_test_btn.clicked.connect(lambda: self.test_api("google"))
        google_layout.addWidget(google_test_btn)
        
        layout.addWidget(google_group)
        
        layout.addStretch()
        return widget
    
    def _create_model_tab(self) -> QWidget:
        """모델 설정 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 기본 모델 선택
        model_group = QGroupBox("기본 모델")
        model_layout = QFormLayout(model_group)
        model_layout.setSpacing(12)
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["OpenAI", "Anthropic", "Google"])
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        model_layout.addRow("Provider:", self.provider_combo)
        
        self.model_combo = QComboBox()
        self._update_model_list("OpenAI")
        model_layout.addRow("Model:", self.model_combo)
        
        layout.addWidget(model_group)
        
        # 파라미터
        param_group = QGroupBox("생성 파라미터")
        param_layout = QFormLayout(param_group)
        param_layout.setSpacing(12)
        
        self.temperature_spin = QSpinBox()
        self.temperature_spin.setRange(0, 100)
        self.temperature_spin.setValue(70)
        self.temperature_spin.setSuffix(" %")
        param_layout.addRow("Temperature:", self.temperature_spin)
        
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(100, 8000)
        self.max_tokens_spin.setValue(2000)
        self.max_tokens_spin.setSingleStep(100)
        param_layout.addRow("Max Tokens:", self.max_tokens_spin)
        
        layout.addWidget(param_group)
        
        layout.addStretch()
        return widget
    
    def _create_general_tab(self) -> QWidget:
        """일반 설정 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 실행 모드
        mode_group = QGroupBox("실행 모드")
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.setSpacing(12)
        
        self.multiagent_checkbox = QCheckBox("🔥 Multi-Agent 모드 (LangGraph 워크플로우)")
        self.multiagent_checkbox.setChecked(False)
        self.multiagent_checkbox.setToolTip(
            "활성화 시 여러 AI Agent가 협업합니다:\n"
            "• Meta Agent: 요청 분석 및 LLM 선택\n"
            "• Planner: 작업 계획 수립\n"
            "• Executor: 코드 실행 및 Tool 호출\n"
            "• Writer: 보고서 작성\n"
            "• QA: 품질 검토"
        )
        mode_layout.addWidget(self.multiagent_checkbox)
        
        layout.addWidget(mode_group)
        
        # 대화 설정
        chat_group = QGroupBox("대화 설정")
        chat_layout = QVBoxLayout(chat_group)
        chat_layout.setSpacing(12)
        
        self.stream_checkbox = QCheckBox("스트리밍 응답 사용 (타이핑 효과)")
        self.stream_checkbox.setChecked(True)
        chat_layout.addWidget(self.stream_checkbox)
        
        self.save_history_checkbox = QCheckBox("대화 기록 자동 저장")
        self.save_history_checkbox.setChecked(True)
        chat_layout.addWidget(self.save_history_checkbox)
        
        layout.addWidget(chat_group)
        
        # 시스템 프롬프트
        prompt_group = QGroupBox("시스템 프롬프트")
        prompt_layout = QVBoxLayout(prompt_group)
        
        self.system_prompt = QLineEdit()
        self.system_prompt.setPlaceholderText("AI의 역할을 정의하세요...")
        self.system_prompt.setText("당신은 PROMETHEUS의 AI 어시스턴트입니다. 친절하고 정확하게 응답해주세요.")
        prompt_layout.addWidget(self.system_prompt)
        
        layout.addWidget(prompt_group)
        
        layout.addStretch()
        return widget
    
    def _on_provider_changed(self, provider: str):
        """Provider 변경 시 모델 목록 업데이트"""
        self._update_model_list(provider)
    
    def _update_model_list(self, provider: str):
        """모델 목록 업데이트"""
        self.model_combo.clear()
        
        models = {
            "OpenAI": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
            "Anthropic": ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
            "Google": ["gemini-2.0-flash", "gemini-1.5-pro-latest", "gemini-1.5-flash-latest"],
        }
        
        self.model_combo.addItems(models.get(provider, []))
    
    def test_api(self, provider: str):
        """API 연결 테스트"""
        import asyncio
        
        key = ""
        if provider == "openai":
            key = self.openai_key.text().strip()
        elif provider == "anthropic":
            key = self.anthropic_key.text().strip()
        elif provider == "google":
            key = self.google_key.text().strip()
        
        if not key:
            QMessageBox.warning(self, "경고", "API 키를 입력해주세요.")
            return
        
        try:
            if provider == "openai":
                import openai
                client = openai.OpenAI(api_key=key)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Hi"}],
                    max_tokens=5,
                )
                QMessageBox.information(self, "성공", "✅ OpenAI 연결 성공!")
            
            elif provider == "anthropic":
                import anthropic
                client = anthropic.Anthropic(api_key=key)
                response = client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=5,
                    messages=[{"role": "user", "content": "Hi"}],
                )
                QMessageBox.information(self, "성공", "✅ Anthropic 연결 성공!")
            
            elif provider == "google":
                import google.generativeai as genai
                genai.configure(api_key=key)
                model = genai.GenerativeModel('gemini-2.0-flash')
                response = model.generate_content("Hi")
                QMessageBox.information(self, "성공", "✅ Google 연결 성공!")
        
        except Exception as e:
            error_msg = str(e)
            # 429 에러는 인증 성공이지만 할당량 초과
            if "429" in error_msg or "quota" in error_msg.lower():
                QMessageBox.information(self, "성공", "✅ API 키 유효함!\n\n(할당량 초과 - 잠시 후 사용 가능)")
            else:
                QMessageBox.critical(self, "오류", f"❌ 연결 실패:\n{error_msg[:200]}")
    
    def load_settings(self) -> Dict[str, Any]:
        """설정 로드"""
        default_settings = {
            "api_keys": {
                "openai": "",
                "anthropic": "",
                "google": "",
            },
            "model": {
                "provider": "OpenAI",
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 2000,
            },
            "general": {
                "streaming": True,
                "save_history": True,
                "multiagent": False,
                "system_prompt": "당신은 PROMETHEUS의 AI 어시스턴트입니다. 친절하고 정확하게 응답해주세요.",
            },
        }
        
        if self.CONFIG_PATH.exists():
            try:
                with open(self.CONFIG_PATH, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    # 기본값과 병합
                    for key in default_settings:
                        if key in saved:
                            default_settings[key].update(saved[key])
            except:
                pass
        
        return default_settings
    
    def load_ui_from_settings(self):
        """설정을 UI에 로드"""
        # API 키
        self.openai_key.setText(self.settings["api_keys"].get("openai", ""))
        self.anthropic_key.setText(self.settings["api_keys"].get("anthropic", ""))
        self.google_key.setText(self.settings["api_keys"].get("google", ""))
        
        # 모델
        provider = self.settings["model"].get("provider", "OpenAI")
        idx = self.provider_combo.findText(provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        
        model = self.settings["model"].get("model", "gpt-4o-mini")
        idx = self.model_combo.findText(model)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        
        self.temperature_spin.setValue(int(self.settings["model"].get("temperature", 0.7) * 100))
        self.max_tokens_spin.setValue(self.settings["model"].get("max_tokens", 2000))
        
        # 일반
        self.multiagent_checkbox.setChecked(self.settings["general"].get("multiagent", False))
        self.stream_checkbox.setChecked(self.settings["general"].get("streaming", True))
        self.save_history_checkbox.setChecked(self.settings["general"].get("save_history", True))
        self.system_prompt.setText(self.settings["general"].get("system_prompt", ""))
    
    def save_settings(self):
        """설정 저장"""
        self.settings = {
            "api_keys": {
                "openai": self.openai_key.text().strip(),
                "anthropic": self.anthropic_key.text().strip(),
                "google": self.google_key.text().strip(),
            },
            "model": {
                "provider": self.provider_combo.currentText(),
                "model": self.model_combo.currentText(),
                "temperature": self.temperature_spin.value() / 100,
                "max_tokens": self.max_tokens_spin.value(),
            },
            "general": {
                "multiagent": self.multiagent_checkbox.isChecked(),
                "streaming": self.stream_checkbox.isChecked(),
                "save_history": self.save_history_checkbox.isChecked(),
                "system_prompt": self.system_prompt.text().strip(),
            },
        }
        
        # 디렉토리 생성
        self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # 저장
        with open(self.CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=2)
        
        return self.settings
    
    def save_and_close(self):
        """저장하고 닫기"""
        settings = self.save_settings()
        self.settings_changed.emit(settings)
        self.accept()
    
    def get_settings(self) -> Dict[str, Any]:
        """현재 설정 반환"""
        return self.settings
