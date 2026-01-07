#!/bin/bash
# PROMETHEUS Desktop App 실행 스크립트

# 스크립트 위치로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# PYTHONPATH 설정
export PYTHONPATH="$SCRIPT_DIR/..:$PYTHONPATH"

echo "🔥 PROMETHEUS Desktop App 시작..."
python3 ui/desktop_app.py
