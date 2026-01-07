# NEXOUS Trace Diff 필터 가이드

## 개요

Trace Diff는 두 실행 결과를 비교하는 강력한 도구입니다. 다양한 필터 옵션으로 원하는 정보만 빠르게 확인할 수 있습니다.

---

## 🎯 필터 옵션

### 1. --only (컨텐츠 필터)

특정 유형의 정보만 비교합니다.

#### --only llm
**LLM 호출만 비교**

```bash
nexous diff trace1.json trace2.json --only llm
```

**출력 정보:**
- 🤖 LLM call count
- 📊 Token usage (input/output/total)
- ⏱️ Latency (ms, percentage)
- 📋 각 call별 상세 정보
  - agent_id
  - provider/model
  - tokens
  - latency

**예시 출력:**
```
🤖 LLM Calls:
   Trace1: 1 calls
   Trace2: 1 calls
   Status: ✅ Same count

📊 Tokens:
   Trace1: 461
   Trace2: 425
   Diff: -36

⏱️  Latency:
   Trace1: 5,747ms
   Trace2: 7,146ms
   Diff: +1,399ms (+24.3%)

📋 LLM Call Details:
   Call #1:
      Trace1: assistant_01
         Model: openai/gpt-4o
         Tokens: 461
         Latency: 5747ms
      Trace2: assistant_01
         Model: openai/gpt-4o
         Tokens: 425
         Latency: 7146ms
```

**사용 시나리오:**
- 💰 LLM 비용 분석
- ⚡ 성능 최적화 검증
- 🔄 재현성 테스트

---

#### --only tool (또는 --only tools)
**Tool 호출만 비교**

```bash
nexous diff trace1.json trace2.json --only tool
```

**출력 정보:**
- 🔧 Tool call count
- 📋 각 call별 상세 정보
  - agent_id
  - tool_name
  - status (OK/ERROR)
  - input/output summary

**예시 출력:**
```
🔧 Tool Calls:
   Trace1: 0 calls
   Trace2: 6 calls
   Status: ❌ Different count

📋 Tool Call Details:
   Call #1:
      Trace1: (no call)
      Trace2: executor_01
         Tool: python_exec
         Status: ERROR
         Input: # Python 코드 실행
                rainfall_data_path = "/absolute/path/..."
```

**사용 시나리오:**
- 🔍 Tool 사용 패턴 분석
- 🐛 Tool 에러 디버깅
- 📊 Agent별 Tool 선택 검증

---

### 2. --show (표시 방식)

비교 결과를 어떻게 표시할지 선택합니다.

#### --show first
**첫 번째 차이점만 표시**

```bash
nexous diff trace1.json trace2.json --show first
```

**출력 정보:**
- 🎯 First Divergence 정확한 위치
- 📝 차이점 유형
- 📍 Agent/Step 위치 정보
- ✅ 동일성 검증

**Divergence 유형:**
- `AGENT_MISSING`: Agent 누락
- `AGENT_ID_DIFF`: Agent ID 차이
- `STATUS_DIFF`: Agent status 차이
- `STEPS_COUNT_DIFF`: Steps 개수 차이
- `STEP_TYPE_DIFF`: Step type 차이
- `STEP_STATUS_DIFF`: Step status 차이

**예시 출력 1 (차이 발견):**
```
🎯 First Divergence Found:
   Type: STEPS_COUNT_DIFF
   Location: Agent #1: planner_01
   Message: Steps 개수 차이: 2 vs 3

   Trace1: 2 steps
   Trace2: 3 steps
```

**예시 출력 2 (동일):**
```
✅ No Divergence: Traces are identical!
```

**사용 시나리오:**
- ⚡ 빠른 회귀 테스트
- 🔍 첫 에러 지점 파악
- ✅ 동일성 빠른 검증

---

#### --show all (기본값)
**모든 차이점 표시**

```bash
nexous diff trace1.json trace2.json --show all
# 또는 옵션 생략
nexous diff trace1.json trace2.json
```

**출력 정보:**
- 📋 Metadata 차이
- 🤖 Agent 차이 (모두)
- ❌ Error 차이
- 📊 Summary 차이

---

## 🔀 필터 조합

### 조합 가능

```bash
# LLM 호출만 + 첫 차이점만
nexous diff trace1.json trace2.json --only llm --show first

# Tool 호출만 + 첫 차이점만
nexous diff trace1.json trace2.json --only tool --show first
```

### 조합 불가

`--only`와 `--show first`를 함께 사용하면 `--only` 필터가 우선됩니다.

---

## 📊 사용 예시

### 예시 1: LLM 비용 모니터링

```bash
# Baseline vs PR
nexous diff \
  traces/baseline_v1/trace.json \
  traces/pr_123/trace.json \
  --only llm

# 확인:
# - Token 사용량 증가/감소
# - Latency 변화
# - 불필요한 LLM 호출 추가 여부
```

### 예시 2: 첫 에러 지점 빠른 파악

```bash
# 성공 trace vs 실패 trace
nexous diff \
  traces/successful_run/trace.json \
  traces/failed_run/trace.json \
  --show first

# 출력:
# 🎯 First Divergence Found:
#    Type: STEP_STATUS_DIFF
#    Location: Agent #2: executor_01, Step #3 (TOOL)
#    Message: Step status 차이: OK vs ERROR
```

### 예시 3: Tool 에러 디버깅

```bash
# 이전 버전 vs 현재 버전
nexous diff \
  traces/v1.0/trace.json \
  traces/v1.1/trace.json \
  --only tool

# 확인:
# - 어느 Agent가 Tool을 사용했는지
# - Tool call이 성공/실패 했는지
# - Input/Output 요약
```

### 예시 4: 재현성 검증

```bash
# 원본 vs FULL Replay
nexous diff \
  traces/original/trace.json \
  traces/replay_*/trace.json \
  --show first

# 기대:
# ✅ No Divergence: Traces are identical!
```

---

## 🐳 Docker 사용

모든 필터 옵션은 Docker에서도 동일하게 작동합니다.

```bash
docker run --rm \
  -v $(pwd)/traces:/app/traces \
  nexous:baseline \
  diff \
  /app/traces/trace1.json \
  /app/traces/trace2.json \
  --only llm \
  --show first
```

---

## 🎯 Best Practices

### 1. 개발 단계

```bash
# 빠른 회귀 테스트
nexous diff baseline.json pr.json --show first

# 차이 발견 → 상세 분석
nexous diff baseline.json pr.json
```

### 2. CI/CD

```bash
# PR 자동 검증
if nexous diff baseline.json pr.json --show first | grep "No Divergence"; then
  echo "✅ PR 통과"
else
  echo "❌ 차이점 발견, 상세 로그:"
  nexous diff baseline.json pr.json
fi
```

### 3. 성능 분석

```bash
# LLM 비용 분석
nexous diff old.json new.json --only llm > llm_diff.txt

# Tool 사용 패턴 분석
nexous diff old.json new.json --only tool > tool_diff.txt
```

### 4. 디버깅

```bash
# 1단계: 첫 에러 위치 파악
nexous diff success.json failure.json --show first

# 2단계: Tool 에러 확인
nexous diff success.json failure.json --only tool

# 3단계: 전체 비교
nexous diff success.json failure.json
```

---

## 📈 성능 비교

| 명령어 | 실행 시간 | 출력 크기 | 사용 시점 |
|--------|----------|----------|----------|
| `diff` | ~100ms | 큼 | 상세 분석 |
| `diff --show first` | ~50ms | 작음 | 빠른 검증 |
| `diff --only llm` | ~80ms | 중간 | LLM 분석 |
| `diff --only tool` | ~80ms | 중간 | Tool 분석 |

---

## 🔧 트러블슈팅

### 문제 1: 출력이 너무 많음

**해결:**
```bash
# --show first 사용
nexous diff trace1.json trace2.json --show first
```

### 문제 2: 특정 정보만 필요

**해결:**
```bash
# --only 필터 사용
nexous diff trace1.json trace2.json --only llm
nexous diff trace1.json trace2.json --only tool
```

### 문제 3: "No Divergence"인데 실제로는 차이가 있음

**원인:** Agent/Step 구조는 동일하지만 내용이 다름

**해결:**
```bash
# 전체 비교 (필터 없이)
nexous diff trace1.json trace2.json

# LLM/Tool 내용 비교
nexous diff trace1.json trace2.json --only llm
nexous diff trace1.json trace2.json --only tool
```

---

## 📚 추가 리소스

- [TRACE_COMMANDS.md](./TRACE_COMMANDS.md) - Trace 전체 명령어 가이드
- [LLM_TEST_RESULTS.md](./LLM_TEST_RESULTS.md) - LLM 테스트 결과
- [CI_CD_GUIDE.md](./CI_CD_GUIDE.md) - CI/CD 통합 가이드

---

## ✨ 요약

| 필터 | 용도 | 출력 |
|------|------|------|
| `--only llm` | LLM 호출 비교 | Calls, Tokens, Latency |
| `--only tool` | Tool 호출 비교 | Calls, Status, I/O |
| `--show first` | 첫 차이점만 | Location, Type, Message |
| `--show all` | 전체 비교 | Metadata, Agents, Errors |

**기본 사용:**
```bash
nexous diff trace1.json trace2.json
```

**빠른 검증:**
```bash
nexous diff trace1.json trace2.json --show first
```

**특정 분석:**
```bash
nexous diff trace1.json trace2.json --only llm
nexous diff trace1.json trace2.json --only tool
```

**최적 조합:**
```bash
nexous diff trace1.json trace2.json --only llm --show first
```
