# NEXOUS Trace Replay & Diff 실행 명령어 세트

## 전제 조건

- ✅ `nexous:baseline` 이미지 존재
- ✅ `BASELINE_RUN_ID` 설정됨
- ✅ `traces/` 볼륨 마운트 사용

### 환경 확인

```bash
# Baseline 설정 확인
echo "BASELINE_RUN_ID=$BASELINE_RUN_ID"

# Trace 파일 존재 확인
ls traces/flood_analysis_ulsan/$BASELINE_RUN_ID/trace.json

# Docker 이미지 확인
docker images nexous:baseline
```

---

## 1️⃣ DRY Replay (항상 가능, 재현 확인)

**용도**: LLM/Tool 호출 없이 trace 타임라인을 재생

### 로컬 실행

```bash
python3 -m nexous.cli.main replay \
  traces/flood_analysis_ulsan/$BASELINE_RUN_ID/trace.json \
  --mode dry
```

### Docker 실행

```bash
docker run --rm \
  -v $(pwd)/traces:/app/traces \
  nexous:baseline \
  replay /app/traces/flood_analysis_ulsan/$BASELINE_RUN_ID/trace.json --mode dry
```

**출력 예시:**
```
🎭 DRY RUN: baseline_002_docker
   Project: flood_analysis_ulsan
   Status: FAILED
   Duration: 35ms
   Mode: DRY
   ℹ️  LLM/Tool 호출 없이 타임라인만 재생

✅ planner_01
   Preset: planner
   Purpose: 침수 분석 계획 수립
   Status: COMPLETED
   Steps: 2
      - INPUT: OK
      - OUTPUT: OK

❌ executor_01
   Preset: executor
   Purpose: SWMM 기반 침수 시뮬레이션 실행
   Status: FAILED
   Steps: 1
      - INPUT: OK

📊 Summary:
   Total Agents: 2
   Completed: 1
   Failed: 1
   LLM Calls: 0
   Duration: 35ms
```

**특징:**
- ⚡ 빠른 실행 (수십 ms)
- 💰 비용 없음 (API 호출 없음)
- 🔍 타임라인 검증
- ✅ 항상 실행 가능

---

## 2️⃣ FULL Replay (실제 재실행)

**용도**: 실제 LLM/Tool을 호출하여 재실행

### 로컬 실행

```bash
python3 -m nexous.cli.main replay \
  traces/flood_analysis_ulsan/$BASELINE_RUN_ID/trace.json \
  --mode full
```

### Docker 실행 (환경 변수 필요)

```bash
docker run --rm \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -v $(pwd)/traces:/app/traces \
  nexous:baseline \
  replay /app/traces/flood_analysis_ulsan/$BASELINE_RUN_ID/trace.json --mode full
```

**특징:**
- ⏱️ 실제 실행 시간 소요
- 💰 API 비용 발생
- 🔄 재현성 검증
- ⚠️ 환경 변수 필수 (API 키)

---

## 3️⃣ Diff (두 trace 비교)

**용도**: 두 실행 결과의 차이점 분석

### 로컬 실행

```bash
python3 -m nexous.cli.main diff \
  traces/flood_analysis_ulsan/baseline_001/trace.json \
  traces/flood_analysis_ulsan/baseline_002_docker/trace.json
```

### Docker 실행

```bash
docker run --rm \
  -v $(pwd)/traces:/app/traces \
  nexous:baseline \
  diff \
  /app/traces/flood_analysis_ulsan/baseline_001/trace.json \
  /app/traces/flood_analysis_ulsan/baseline_002_docker/trace.json
```

**출력 예시:**
```
🔍 Comparing Traces:
   Trace 1: baseline_001
   Trace 2: baseline_002_docker

📋 Metadata:
   project_id: ✅
   status: ✅
   duration_ms:
      Trace1: 134
      Trace2: 35
      Diff: 99

🤖 Agents: ✅ All same

❌ Errors:
   Trace1: 2
   Trace2: 2
   Status: ✅ Same count

📊 Summary:
   total_agents: ✅
   completed_agents: ✅
   failed_agents: ✅
   total_duration_ms: ❌
      Trace1: 134
      Trace2: 35
```

**특징:**
- 📊 상세한 비교 리포트
- ✅ 재현성 검증
- ⚡ 성능 차이 확인
- 🐛 회귀 테스트

---

## 4️⃣ Verify (Baseline 검증)

**용도**: Baseline trace가 유효한지 검증

### 로컬 실행

```bash
# DRY replay로 검증
python3 -m nexous.cli.main replay \
  traces/flood_analysis_ulsan/$BASELINE_RUN_ID/trace.json \
  --mode dry

# 종료 코드 확인
echo "Exit code: $?"
```

### Docker 실행

```bash
docker run --rm \
  -v $(pwd)/traces:/app/traces \
  nexous:baseline \
  replay /app/traces/flood_analysis_ulsan/$BASELINE_RUN_ID/trace.json --mode dry

# 종료 코드 확인
echo "Exit code: $?"
```

**성공 기준:**
- Exit code: 0
- Trace 파일 로드 성공
- 모든 Agent 정보 출력
- Summary 정상 표시

---

## 🎯 실전 사용 시나리오

### 시나리오 1: PR 검증

```bash
# 1. 기존 baseline replay
docker run --rm \
  -v $(pwd)/traces:/app/traces \
  nexous:baseline \
  replay /app/traces/flood_analysis_ulsan/baseline_001/trace.json --mode dry

# 2. PR 브랜치 실행
docker run --rm \
  -v $(pwd)/traces:/app/traces \
  -v $(pwd)/projects:/app/projects \
  nexous:pr-branch \
  run projects/flood_analysis_ulsan/project.yaml \
  --trace-dir /app/traces \
  --run-id pr_test_001

# 3. Diff 비교
docker run --rm \
  -v $(pwd)/traces:/app/traces \
  nexous:baseline \
  diff \
  /app/traces/flood_analysis_ulsan/baseline_001/trace.json \
  /app/traces/flood_analysis_ulsan/pr_test_001/trace.json
```

### 시나리오 2: 성능 회귀 테스트

```bash
# 1. 여러 실행 trace 수집
for i in {1..5}; do
  docker run --rm \
    -v $(pwd)/traces:/app/traces \
    -v $(pwd)/projects:/app/projects \
    nexous:baseline \
    run projects/flood_analysis_ulsan/project.yaml \
    --trace-dir /app/traces \
    --run-id perf_test_$i
done

# 2. 각 실행을 baseline과 비교
for i in {1..5}; do
  echo "=== Run $i vs Baseline ==="
  docker run --rm \
    -v $(pwd)/traces:/app/traces \
    nexous:baseline \
    diff \
    /app/traces/flood_analysis_ulsan/baseline_001/trace.json \
    /app/traces/flood_analysis_ulsan/perf_test_$i/trace.json
done
```

### 시나리오 3: LLM 응답 재현성 검증

```bash
# 1. Mock 실행 (baseline)
docker run --rm \
  -v $(pwd)/traces:/app/traces \
  -v $(pwd)/projects:/app/projects \
  nexous:baseline \
  run projects/llm_test_simple/project.yaml \
  --trace-dir /app/traces \
  --run-id llm_baseline

# 2. 실제 LLM 실행
docker run --rm \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -v $(pwd)/traces:/app/traces \
  -v $(pwd)/projects:/app/projects \
  nexous:baseline \
  run projects/llm_test_simple/project.yaml \
  --use-llm \
  --trace-dir /app/traces \
  --run-id llm_real_001

# 3. 비교
docker run --rm \
  -v $(pwd)/traces:/app/traces \
  nexous:baseline \
  diff \
  /app/traces/llm_test_simple/llm_baseline/trace.json \
  /app/traces/llm_test_simple/llm_real_001/trace.json
```

---

## 📊 모드 비교표

| 기능 | DRY | FULL |
|------|-----|------|
| 실행 시간 | 수십 ms | 실제 시간 |
| API 호출 | ❌ | ✅ |
| 비용 | $0 | 실제 비용 |
| 환경 변수 | 불필요 | 필수 |
| 재현성 검증 | 타임라인 | 전체 |
| 주 용도 | 빠른 검증 | 완전 재실행 |

---

## 🔧 트러블슈팅

### 문제 1: Trace 파일을 찾을 수 없음

```bash
# 원인: 잘못된 경로 또는 run_id
# 해결: 경로 확인
ls traces/flood_analysis_ulsan/$BASELINE_RUN_ID/trace.json

# Docker 볼륨 마운트 확인
docker run --rm \
  -v $(pwd)/traces:/app/traces \
  nexous:baseline \
  sh -c "ls /app/traces/flood_analysis_ulsan/"
```

### 문제 2: API 키 오류 (FULL 모드)

```bash
# 원인: 환경 변수 미설정
# 해결: -e 옵션으로 전달
docker run --rm \
  -e OPENAI_API_KEY="sk-..." \
  -v $(pwd)/traces:/app/traces \
  nexous:baseline \
  replay /app/traces/.../trace.json --mode full
```

### 문제 3: Docker 이미지가 없음

```bash
# 원인: 이미지 빌드 필요
# 해결: 빌드 및 태그
docker build -t nexous:baseline .

# 확인
docker images nexous:baseline
```

---

## 📝 Best Practices

### 1. Baseline 관리
- 안정적인 실행을 baseline으로 지정
- 버전별로 태그 관리 (`baseline_v1.0`, `baseline_v2.0`)
- 주기적으로 baseline 갱신

### 2. Trace 파일 구조
```
traces/
└── {project_id}/
    ├── baseline_001/trace.json      ← 공식 baseline
    ├── pr_123_001/trace.json         ← PR 테스트
    ├── perf_test_001/trace.json      ← 성능 테스트
    └── llm_real_001/trace.json       ← LLM 테스트
```

### 3. CI/CD 통합
- PR마다 DRY replay 실행
- Baseline과 자동 diff
- 성능 회귀 검사 (duration_ms)
- 테스트 실패 시 trace 아티팩트 저장

---

## 🚀 다음 단계

- [ ] GitHub Actions 워크플로우 추가
- [ ] 자동 Diff 리포트 생성
- [ ] Slack/Email 알림 연동
- [ ] 성능 벤치마크 대시보드
- [ ] Trace 비교 시각화 (HTML)
