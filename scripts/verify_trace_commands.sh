#!/bin/bash
# NEXOUS Trace Replay & Diff 검증 스크립트

set -e

echo "🔍 NEXOUS Trace 명령어 검증 시작"
echo ""

# 전제 조건 확인
echo "1️⃣ 전제 조건 확인..."
BASELINE_RUN_ID=${BASELINE_RUN_ID:-baseline_002_docker}

echo "   BASELINE_RUN_ID: $BASELINE_RUN_ID"

if [ ! -f "traces/flood_analysis_ulsan/$BASELINE_RUN_ID/trace.json" ]; then
    echo "   ❌ Trace 파일을 찾을 수 없습니다"
    exit 1
fi
echo "   ✅ Trace 파일 존재 확인"

if ! docker images nexous:baseline | grep -q baseline; then
    echo "   ⚠️  nexous:baseline 이미지 빌드 중..."
    docker build -t nexous:baseline .
fi
echo "   ✅ Docker 이미지 확인"
echo ""

# DRY Replay 테스트
echo "2️⃣ DRY Replay 테스트..."
python3 -m nexous.cli.main replay \
  traces/flood_analysis_ulsan/$BASELINE_RUN_ID/trace.json \
  --mode dry > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "   ✅ DRY Replay 성공"
else
    echo "   ❌ DRY Replay 실패"
    exit 1
fi
echo ""

echo "🎉 검증 완료!"
