# NEXOUS CI/CD 설정 가이드

## 📋 개요

NEXOUS 프로젝트의 **LEVEL 3 CI/CD** 구축을 완료했습니다.

- **자동 테스트**: PR/Push 시 자동으로 pytest 실행
- **E2E 분리**: 실제 LLM 호출 테스트는 별도 워크플로우로 분리
- **머지 게이트**: 테스트 실패 시 자동으로 머지 차단
- **결과 보관**: 테스트 결과와 trace를 아티팩트로 저장

---

## 🔧 설정된 파일

### 1. pytest.ini (업데이트)
- E2E 마커 추가: `@pytest.mark.e2e`
- 테스트 결과 출력 경로: `test-results/`
- Coverage 리포트 생성

### 2. .github/workflows/ci.yml
**PR/Push 시 자동 실행**
- Python 3.10, 3.11, 3.12 멀티 버전 테스트
- E2E 테스트 제외: `pytest -m "not e2e"`
- 병렬 실행: pytest-xdist 사용
- 린팅: black, isort, ruff

### 3. .github/workflows/e2e.yml
**E2E 테스트 (수동/스케줄)**
- 수동 실행: GitHub Actions UI에서 실행
- 자동 실행: 매일 오전 3시 (KST)
- E2E 테스트만 실행: `pytest -m e2e`
- API 키 주입: GitHub Secrets 사용

### 4. .gitignore (추가)
- 테스트 결과 디렉토리 제외
- Coverage 리포트 제외
- 환경 변수 파일 제외

---

## 🔑 GitHub Secrets 설정

다음 Secrets를 GitHub 저장소에 등록해야 합니다:

### 필수 (E2E 테스트용)
```
OPENAI_API_KEY       # OpenAI API 키
ANTHROPIC_API_KEY    # Anthropic (Claude) API 키
GOOGLE_API_KEY       # Google (Gemini) API 키
```

### 선택 (Coverage 리포트용)
```
CODECOV_TOKEN        # Codecov 토큰 (선택사항)
```

### Secrets 등록 방법
1. GitHub 저장소 → Settings → Secrets and variables → Actions
2. "New repository secret" 클릭
3. Name과 Value 입력 후 저장


---

## 🚀 워크플로우 실행 방법

### 1. 자동 CI 테스트 (ci.yml)

**자동 트리거:**
- `main` 또는 `develop` 브랜치에 Push
- PR 생성 시 자동 실행

**테스트 범위:**
- E2E 테스트 제외 (`pytest -m "not e2e"`)
- Unit 테스트 + Integration 테스트 (Mock 사용)

**결과:**
- 테스트 실패 시 PR 머지 차단
- 테스트 리포트가 PR에 자동 코멘트

---

### 2. E2E 테스트 (e2e.yml)

#### 수동 실행
1. GitHub 저장소 → Actions 탭
2. "E2E Tests (LLM API Calls)" 선택
3. "Run workflow" 클릭
4. (선택) Test pattern 입력 (예: `test_llm`, `test_integration`)
5. "Run workflow" 확인

#### 스케줄 자동 실행
- 매일 오전 3시 (KST) / 오후 6시 (UTC)
- 모든 E2E 테스트 자동 실행

**테스트 범위:**
- E2E 테스트만 실행 (`pytest -m e2e`)
- 실제 LLM API 호출
- API 키 필수

**결과:**
- 실패 시 GitHub Issue 자동 생성
- Trace 파일과 결과를 아티팩트로 저장

---

## 📊 테스트 결과 확인

### Actions 아티팩트
1. GitHub 저장소 → Actions 탭
2. 완료된 워크플로우 선택
3. "Artifacts" 섹션에서 다운로드

**저장되는 아티팩트:**
- `test-results-py3.X`: JUnit XML, Coverage 리포트
- `e2e-test-results-py3.X`: E2E 테스트 결과
- `e2e-traces-py3.X`: Trace 파일 및 outputs

### Coverage 리포트
- HTML 리포트: `test-results/htmlcov/index.html`
- XML 리포트: `test-results/coverage.xml`
- Codecov (선택): https://codecov.io

---

## 🏷️ 테스트 마커 사용법

### 마커 종류
```python
@pytest.mark.e2e          # E2E 테스트 (실제 LLM 호출)
@pytest.mark.unit         # Unit 테스트
@pytest.mark.integration  # Integration 테스트
@pytest.mark.slow         # 느린 테스트
```


### E2E 테스트 작성 예시

```python
import pytest

# 전체 파일을 E2E로 마킹
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set"
    )
]

class TestRealLLM:
    def test_openai_call(self):
        # 실제 OpenAI API 호출
        pass
```

### 마커로 선택 실행

```bash
# E2E 제외하고 실행 (CI에서 사용)
pytest -m "not e2e"

# E2E만 실행
pytest -m e2e

# 특정 테스트만 실행
pytest -m e2e -k test_llm

# 느린 테스트 제외
pytest -m "not slow"
```

---

## 🛠️ 로컬 개발 환경

### 의존성 설치
```bash
pip install -r requirements.txt
pip install pytest pytest-cov pytest-xdist pytest-timeout pytest-asyncio
```


### 로컬에서 테스트 실행

```bash
# E2E 제외 테스트
pytest -m "not e2e"

# E2E 테스트 (API 키 필요)
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
pytest -m e2e

# Coverage 포함
pytest --cov=nexous --cov-report=html

# 병렬 실행
pytest -n auto
```

### 테스트 디렉토리 생성
```bash
mkdir -p test-results
```

---

## 📝 체크리스트

### 초기 설정
- [ ] GitHub Secrets 등록 (OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY)
- [ ] CI 워크플로우 확인 (PR 생성 후 자동 실행 확인)
- [ ] E2E 워크플로우 수동 실행 테스트
- [ ] 테스트 결과 아티팩트 다운로드 확인

### 테스트 작성 시
- [ ] E2E 테스트는 `@pytest.mark.e2e` 마커 추가
- [ ] API 키 없을 때 skipif 처리
- [ ] 타임아웃 설정 (--timeout=300)
- [ ] Trace 파일 생성 확인


---

## 🔍 트러블슈팅

### 문제: CI에서 테스트 실패
**해결:**
1. Actions 탭에서 실패 로그 확인
2. 아티팩트 다운로드하여 상세 리포트 확인
3. 로컬에서 동일한 Python 버전으로 재현

### 문제: E2E 테스트 실패
**해결:**
1. GitHub Secrets에 API 키가 올바르게 설정되었는지 확인
2. API 키 유효성 확인 (만료, 권한)
3. 로컬에서 `pytest -m e2e -v` 실행하여 상세 로그 확인

### 문제: Coverage가 너무 낮음
**해결:**
1. `test-results/htmlcov/index.html` 확인
2. 커버되지 않은 코드 확인
3. 누락된 테스트 추가

### 문제: 테스트 타임아웃
**해결:**
1. `--timeout=300` 옵션 확인
2. 느린 테스트에 `@pytest.mark.slow` 추가
3. Mock을 사용하여 외부 의존성 제거

---

## 📚 참고 자료

- [pytest 공식 문서](https://docs.pytest.org/)
- [GitHub Actions 문서](https://docs.github.com/en/actions)
- [pytest-cov 문서](https://pytest-cov.readthedocs.io/)
- [pytest-xdist 문서](https://pytest-xdist.readthedocs.io/)

