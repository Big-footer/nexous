# NEXOUS CI/CD 가이드

## 개요

NEXOUS는 GitHub Actions를 사용한 완전 자동화된 CI/CD 파이프라인을 제공합니다.

---

## 🔄 워크플로우 구조

### 1. PR Test & Trace Diff
**트리거**: Pull Request to main
**파일**: `.github/workflows/pr-test.yml`

#### 실행 단계
1. **Baseline 검증**: DRY replay로 baseline trace 확인
2. **PR 실행**: Mock 모드로 PR 코드 실행
3. **Diff 비교**: Baseline vs PR trace 비교
4. **성능 검사**: 50% 이상 느려지면 경고
5. **PR 코멘트**: 결과를 PR에 자동 게시

#### 성능 회귀 기준
- **경고**: PR이 baseline보다 50% 이상 느림
- **통과**: 50% 이내

#### 예시 PR 코멘트
```markdown
## 🔍 NEXOUS Trace Diff Report

### Comparison
- **Baseline**: `baseline_002_docker`
- **PR Run**: `pr_123_abc123`

### ✅ Performance OK

### Diff Output
```
📋 Metadata:
   project_id: ✅
   status: ✅
   duration_ms:
      Trace1: 35
      Trace2: 42
      Diff: 7
```
```

---

### 2. Docker Build & Test
**트리거**: Push to main, PR (Dockerfile 변경)
**파일**: `.github/workflows/docker-build.yml`

#### 실행 단계
1. **Docker 빌드**: Multi-stage build
2. **기본 테스트**: `--version`, `--help`
3. **DRY Replay**: Docker 내에서 trace replay
4. **Registry 푸시**: main 브랜치일 경우 GHCR에 푸시

#### 이미지 태그
- `latest`: main 브랜치 최신
- `main-{sha}`: 커밋별
- `pr-{number}`: PR별

---

### 3. Tests (Pytest)
**트리거**: Push, Pull Request
**파일**: `.github/workflows/tests.yml`

#### 실행 단계
1. **Multi Python**: 3.10, 3.11, 3.12
2. **Pytest 실행**: 전체 테스트
3. **Coverage**: Python 3.11에서 실행
4. **Codecov 업로드**: 커버리지 리포트

---

### 4. Performance Benchmark
**트리거**: 매일 오전 2시 (UTC), 수동 실행
**파일**: `.github/workflows/benchmark.yml`

#### 실행 단계
1. **5회 반복 실행**: Mock 모드
2. **통계 분석**: 평균, 최소, 최대
3. **결과 저장**: JSON 형식
4. **Artifact 업로드**: 90일 보관

#### 벤치마크 결과 예시
```json
{
  "date": "2026-01-07",
  "runs": 5,
  "average_ms": 45.2,
  "min_ms": 42,
  "max_ms": 49,
  "durations": [45, 42, 46, 49, 44]
}
```

---

## 🔐 Secrets 설정

### 필수 Secrets

#### OPENAI_API_KEY
- **용도**: 실제 LLM 테스트
- **설정**: Settings → Secrets → Actions
- **값**: `sk-proj-...`

#### ANTHROPIC_API_KEY
- **용도**: Claude 모델 사용
- **설정**: Settings → Secrets → Actions
- **값**: `sk-ant-...`

#### GOOGLE_API_KEY
- **용도**: Gemini 모델 사용
- **설정**: Settings → Secrets → Actions
- **값**: `AIza...`

### 자동 제공 Secrets
- `GITHUB_TOKEN`: GitHub API 접근 (자동)

---

## 📊 배지 (Badges)

README에 추가된 배지:

```markdown
[![Tests](https://github.com/Big-footer/nexous/actions/workflows/tests.yml/badge.svg)](https://github.com/Big-footer/nexous/actions/workflows/tests.yml)
[![Docker Build](https://github.com/Big-footer/nexous/actions/workflows/docker-build.yml/badge.svg)](https://github.com/Big-footer/nexous/actions/workflows/docker-build.yml)
[![PR Test](https://github.com/Big-footer/nexous/actions/workflows/pr-test.yml/badge.svg)](https://github.com/Big-footer/nexous/actions/workflows/pr-test.yml)
```

---

## 🚀 사용 방법

### PR 워크플로우

1. **브랜치 생성**
```bash
git checkout -b feature/my-feature
```

2. **코드 수정**
```bash
# nexous 코드 수정
vim nexous/core/runner.py
```

3. **커밋 & 푸시**
```bash
git add .
git commit -m "feat: add new feature"
git push origin feature/my-feature
```

4. **PR 생성**
- GitHub에서 PR 생성
- 자동으로 워크플로우 실행
- PR 코멘트에 결과 표시

5. **결과 확인**
- ✅ 모든 체크 통과 → 머지 가능
- ❌ 실패 → 로그 확인 후 수정

---

### 수동 벤치마크 실행

1. **Actions 탭 이동**
2. **Performance Benchmark 선택**
3. **Run workflow 클릭**
4. **결과 확인**: Artifacts에서 다운로드

---

## 🐛 트러블슈팅

### 문제 1: PR 테스트 실패 (Baseline 없음)

**증상:**
```
⚠️  Baseline trace not found: baseline_002_docker
```

**해결:**
```bash
# Baseline trace 생성
python -m nexous.cli.main run \
  projects/flood_analysis_ulsan/project.yaml \
  --run-id baseline_002_docker

# Commit & Push
git add traces/
git commit -m "chore: add baseline trace"
git push
```

### 문제 2: Docker 빌드 실패

**증상:**
```
ERROR: failed to solve: failed to read dockerfile
```

**해결:**
1. Dockerfile 문법 확인
2. `.dockerignore` 확인
3. 로컬에서 빌드 테스트
```bash
docker build -t nexous:test .
```

### 문제 3: 성능 회귀 경고

**증상:**
```
⚠️  Performance regression detected!
Baseline: 35ms
PR: 60ms
Increase: 71.4%
```

**해결:**
1. Trace diff 확인
2. 코드 최적화
3. 또는 baseline 갱신

---

## 📈 모니터링

### Actions 탭
- 모든 워크플로우 실행 기록
- 로그 확인
- Artifacts 다운로드

### Insights 탭
- Dependency graph
- Network activity
- Contributors

---

## 🎯 Best Practices

### 1. Baseline 관리
- 주요 릴리스마다 baseline 갱신
- `baseline_v1.0`, `baseline_v2.0` 등으로 버전 관리
- traces 디렉토리를 git에 포함

### 2. PR 전략
- 작은 단위로 PR 생성
- CI 통과 후 머지
- 성능 회귀 주의

### 3. 테스트 작성
- 새 기능마다 테스트 추가
- Mock 테스트 우선
- LLM 테스트는 최소화 (비용)

### 4. Docker 이미지
- main 브랜치만 latest 태그
- PR은 임시 태그
- 정기적으로 이미지 정리

---

## 🔧 커스터마이징

### 성능 회귀 임계값 변경

`.github/workflows/pr-test.yml`:
```yaml
# 50% → 30%로 변경
THRESHOLD=$(echo "$BASELINE_MS * 1.3" | bc)
```

### 벤치마크 실행 횟수 변경

`.github/workflows/benchmark.yml`:
```yaml
env:
  BENCHMARK_RUNS: 10  # 5 → 10으로 변경
```

### 스케줄 변경

`.github/workflows/benchmark.yml`:
```yaml
schedule:
  - cron: '0 0 * * 0'  # 매주 일요일 자정
```

---

## 📚 추가 리소스

- [GitHub Actions 문서](https://docs.github.com/en/actions)
- [Docker 문서](https://docs.docker.com/)
- [NEXOUS Trace Commands](./TRACE_COMMANDS.md)
- [LLM Test Results](./LLM_TEST_RESULTS.md)
