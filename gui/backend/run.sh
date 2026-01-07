#!/bin/bash
# NEXOUS Backend 실행

cd "$(dirname "$0")/.."

echo "🚀 Starting NEXOUS Backend..."
echo "   API: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo ""

PYTHONPATH="$(pwd)" python -m uvicorn gui.backend.main:app --reload --host 0.0.0.0 --port 8000
