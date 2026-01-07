#!/bin/bash
# PROMETHEUS Chat UI 실행 스크립트

# 스크립트 위치로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# PYTHONPATH 설정
export PYTHONPATH="$SCRIPT_DIR/..:$PYTHONPATH"

# Streamlit 실행
echo "🔥 PROMETHEUS Chat UI 시작..."
echo "   URL: http://localhost:8501"
echo ""

streamlit run ui/chat_app.py \
    --server.port 8501 \
    --server.headless true \
    --browser.gatherUsageStats false \
    --theme.base dark \
    --theme.primaryColor "#667eea"
