# NEXOUS STEP 3 - Baseline 보호 & 승인

## 📅 구현 날짜
2026-01-07

---

## 🎯 STEP 3의 목적

NEXOUS를 **감사·재현·책임 가능한 AI 실행 플랫폼**으로 전환합니다.

### 핵심 목표
- ✅ 특정 실행(run)을 공식 Baseline으로 선언
- ✅ Baseline 결과를 변경 불가(Read-only) 상태로 보호
- ✅ 모든 Diff / Replay / 검증의 절대 기준선으로 고정
- ✅ CI/운영 환경에서도 Baseline 무단 변경 차단

---

## 📁 Baseline 구조

Baseline은 다음 요소로 구성됩니다:

```
traces/{project}/{run_id}/
├── trace.json          # 실행 전체 기록
├── approval.json       # 승인 메타데이터 ✨ NEW!
└── snapshot/           # project.yaml, preset.yaml 스냅샷

projects/{project}/
└── baseline.yaml       # 공식 기준선 선언 (Git 관리) ✨ NEW!
```

---

## 📋 데이터 구조

### approval.json

**목적**: Baseline 승인 상태 명시

**스키마**:
```json
{
  "baseline": true,
  "project": "flood_analysis_ulsan",
  "approved_by": "DPA Solutions",
  "approved_at": "2026-01-07T14:41:15+00:00",
  "reason": "Initial baseline for flood analysis project",
  "engine_version": "nexous:latest",
  "lock": true,
  "schema_version": "1.0"
}
```

**규칙**:
- ✅ `lock=true`: Baseline 변경 불가
- ✅ Read-only 파일 (chmod 444)
- ✅ Trace 디렉토리 내부에 위치

---

### baseline.yaml

**목적**: Git으로 관리되는 공식 기준 선언

**스키마**:
```yaml
project: flood_analysis_ulsan
baseline_run_id: baseline_002_docker
trace_path: traces/flood_analysis_ulsan/baseline_002_docker/trace.json
approved: true
approved_at: '2026-01-07T14:41:15+00:00'
policy:
  diff_required: true           # Diff 필수
  replay_allowed: true          # Replay 허용
  overwrite_forbidden: true     # 덮어쓰기 금지
```

**규칙**:
- ✅ Git으로 버전 관리
- ✅ Diff는 baseline.yaml만 기준으로 허용
- ✅ baseline.yaml 변경은 명시적 승인 필요

---

## 🔧 CLI 명령어

### 1. baseline approve

**목적**: Run을 Baseline으로 승인

**명령어**:
```bash
nexous baseline approve \
  traces/{project}/{run_id} \
  --project {project_name} \
  --approved-by "{approver}" \
  --reason "{reason}" \
  --engine-version "nexous:v1.0"
```

**예시**:
```bash
nexous baseline approve \
  traces/flood_analysis_ulsan/baseline_002_docker \
  --project flood_analysis_ulsan \
  --approved-by "DPA Solutions" \
  --reason "Initial baseline for flood analysis project"
```

**실행 결과**:
```
[NEXOUS] Baseline Approve started
[NEXOUS] Trace dir: traces/flood_analysis_ulsan/baseline_002_docker
[NEXOUS] Project: flood_analysis_ulsan
[NEXOUS] Approved by: DPA Solutions
✅ approval.json created: traces/.../approval.json
✅ baseline.yaml created: projects/flood_analysis_ulsan/baseline.yaml

[NEXOUS] Baseline approved successfully
   Run ID: baseline_002_docker
   Project: flood_analysis_ulsan
   Approved by: DPA Solutions
```

**생성되는 파일**:
1. `traces/{project}/{run_id}/approval.json`
2. `projects/{project}/baseline.yaml`

---

### 2. baseline verify

**목적**: Baseline 무결성 검증

**명령어**:
```bash
nexous baseline verify {project_name}
```

**예시**:
```bash
nexous baseline verify flood_analysis_ulsan
```

**성공 시 출력**:
```
[NEXOUS] Baseline Verify started
[NEXOUS] Project: flood_analysis_ulsan

✅ Baseline Verification Passed
   ✔ Baseline exists
   ✔ approval.json found
   ✔ lock=true
   ✔ trace schema valid
   ✔ baseline verified
```

**실패 시 출력**:
```
❌ Baseline Verification Failed
   ✗ baseline.yaml not found
   ✗ trace.json not found
   ✗ approval.json load error: ...
```

**검증 항목**:
1. ✅ `baseline.yaml` 존재
2. ✅ `trace.json` 존재
3. ✅ `approval.json` 존재 및 유효성
4. ✅ `lock=true` 확인
5. ✅ `approved=true` 확인

---

### 3. baseline list

**목적**: 모든 Baseline 목록 확인

**명령어**:
```bash
nexous baseline list
```

**출력 예시**:
```
[NEXOUS] Baseline List

Found 1 baseline(s):

📌 flood_analysis_ulsan
   Run ID: baseline_002_docker
   Approved: True
   Approved at: 2026-01-07T14:41:15+00:00
   Trace: traces/flood_analysis_ulsan/baseline_002_docker/trace.json
```

---

## 🔒 보호 규칙

### 1. Read-only 보호

**규칙**:
- ✅ Baseline trace 디렉토리는 Read-only
- ✅ `approval.json`은 chmod 444
- ✅ 운영 환경에서도 동일 규칙 적용

**적용 방법**:
```python
# approval.json 저장 후
os.chmod(approval_path, 0o444)  # r--r--r--

# 디렉토리
os.chmod(trace_dir, 0o555)  # r-xr-xr-x
```

### 2. Diff 강제 규칙

**허용**:
```bash
# baseline.yaml 기반
nexous diff \
  --baseline flood_analysis_ulsan \
  --new traces/.../trace.json
```

**금지**:
```bash
# 임의 trace 간 비교
nexous diff trace1.json trace2.json  ❌
```

### 3. Git 관리

**baseline.yaml 변경 시**:
1. PR 생성 필수
2. 리뷰어 최소 2명
3. 승인 이유 명시
4. CI 검증 통과

---

## 🚀 실전 워크플로우

### 워크플로우 1: 초기 Baseline 설정

```bash
# 1. 프로젝트 실행
nexous run projects/my_project/project.yaml --use-llm

# 2. 결과 확인
nexous replay traces/my_project/run_001/trace.json --mode dry

# 3. Baseline 승인
nexous baseline approve \
  traces/my_project/run_001 \
  --project my_project \
  --approved-by "Tech Lead" \
  --reason "Initial production baseline"

# 4. 검증
nexous baseline verify my_project

# 5. Git 커밋
git add projects/my_project/baseline.yaml
git add traces/my_project/run_001/approval.json
git commit -m "baseline: Set initial baseline for my_project"
git push
```

---

### 워크플로우 2: Baseline 기반 회귀 테스트

```bash
# 1. Baseline 확인
nexous baseline list

# 2. 코드 변경 후 실행
nexous run projects/my_project/project.yaml --use-llm

# 3. Baseline과 비교
nexous diff \
  --baseline my_project \
  --new traces/my_project/run_002/trace.json

# 4. 차이 없으면 통과
# ✅ No Divergence: Traces are identical!

# 5. 차이 있으면 분석
nexous diff \
  --baseline my_project \
  --new traces/my_project/run_002/trace.json \
  --only llm

# 6. 승인 후 새 Baseline으로 교체
nexous baseline approve \
  traces/my_project/run_002 \
  --project my_project \
  --approved-by "Tech Lead" \
  --reason "Performance optimization - 30% token reduction"
```

---

### 워크플로우 3: CI/CD 통합

```yaml
# .github/workflows/baseline-check.yml
name: Baseline Check

on:
  pull_request:
    paths:
      - 'nexous/**'
      - 'projects/**'

jobs:
  baseline-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Verify Baseline
        run: |
          nexous baseline verify flood_analysis_ulsan
      
      - name: Run Project
        run: |
          nexous run projects/flood_analysis_ulsan/project.yaml
      
      - name: Compare with Baseline
        run: |
          nexous diff \
            --baseline flood_analysis_ulsan \
            --new traces/flood_analysis_ulsan/*/trace.json \
            --show first
      
      - name: Check for Divergence
        run: |
          if grep "No Divergence" diff_output.txt; then
            echo "✅ Baseline check passed"
          else
            echo "❌ Divergence detected"
            exit 1
          fi
```

---

## 📊 STEP 3 완료 조건

### ✅ 달성한 것

1. **데이터 구조**
   - ✅ `approval.json` 스키마 정의
   - ✅ `baseline.yaml` 스키마 정의
   - ✅ `Approval` 클래스 구현
   - ✅ `BaselineManager` 클래스 구현

2. **CLI 명령어**
   - ✅ `baseline approve` 구현
   - ✅ `baseline verify` 구현
   - ✅ `baseline list` 구현

3. **보호 로직**
   - ✅ Read-only 파일 설정
   - ✅ 승인 검증 로직
   - ✅ Baseline 무결성 체크

4. **문서화**
   - ✅ 완전한 사용 가이드
   - ✅ 워크플로우 예시
   - ✅ CI/CD 통합 가이드

---

## 🎯 STEP 3의 의미

### Before STEP 3
```
실험용 AI ❌
챗봇 ❌
단순 자동화 ❌
```

### After STEP 3
```
✅ 감사 가능 (Auditable)
   - 모든 실행 기록 보존
   - 승인 이력 추적
   - 변경 불가 보호

✅ 재현 가능 (Reproducible)
   - Baseline 기준 고정
   - FULL Replay 지원
   - 동일 환경 재현

✅ 책임 가능 (Accountable)
   - 승인자 명시
   - 승인 이유 기록
   - 변경 이력 Git 관리
```

**➡ 감사·재현·책임 가능한 AI 실행 플랫폼 ✅**

---

## 📁 생성된 파일

```
nexous/baseline/
├── __init__.py         # 모듈 초기화
├── approval.py         # Approval 클래스 (177 lines)
└── manager.py          # BaselineManager 클래스 (176 lines)

nexous/cli/
└── main.py             # CLI 명령어 추가 (+146 lines)

projects/{project}/
└── baseline.yaml       # 공식 기준선 선언

traces/{project}/{run_id}/
└── approval.json       # 승인 메타데이터

docs/
└── BASELINE_GUIDE.md   # 완전한 가이드 (이 문서)
```

---

## 🚀 다음 단계 (선택)

### STEP 4A: GUI 통합
- Baseline/Diff/Replay 버튼 연동
- 시각화 대시보드
- 승인 워크플로우 UI

### STEP 4B: 프로덕션 배포
- Cloud Run / ECS 배포
- 자동화된 Baseline 관리
- 모니터링 & 알림

### STEP 4C: 엔터프라이즈 기능
- RBAC (Role-Based Access Control)
- Audit 로그
- Compliance 리포트

---

## 🎊 결론

**NEXOUS는 이제 엔터프라이즈급 AI 실행 플랫폼입니다!**

- 🛡️ Baseline 보호
- ✅ 승인 시스템
- 📋 감사 추적
- 🔄 재현 보장
- 👤 책임 명시

**프로덕션 준비 완료!** 🚀
