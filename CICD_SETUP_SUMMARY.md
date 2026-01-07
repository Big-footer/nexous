# NEXOUS LEVEL 3 CI/CD 구축 완료 보고서

## ✅ 구축 완료 항목

### 📁 추가/수정된 파일

1. **pytest.ini** (수정)
   - E2E 마커 추가
   - 테스트 결과 출력 경로 설정
   - Coverage 리포트 설정

2. **.github/workflows/ci.yml** (신규)
   - PR/Push 시 자동 테스트
   - E2E 제외 (`pytest -m "not e2e"`)
   - Python 3.10, 3.11, 3.12 멀티 버전
   - 병렬 실행 (pytest-xdist)
   - Linting (black, isort, ruff)

3. **.github/workflows/e2e.yml** (신규)
   - E2E 테스트 전용
   - 수동 실행 (workflow_dispatch)
   - 스케줄 실행 (매일 오전 3시 KST)
   - API 키 주입
   - 실패 시 Issue 자동 생성

4. **.gitignore** (신규)
   - test-results/ 제외
   - .pytest_cache/ 제외
   - coverage 파일 제외

5. **tests/test_llm.py** (수정)
   - `@pytest.mark.e2e` 마커 추가

6. **tests/test_integration.py** (수정)
   - `@pytest.mark.e2e` 마커 추가

7. **docs/CI_CD_GUIDE.md** (신규)
   - 전체 CI/CD 설정 가이드
   - 워크플로우 실행 방법
   - 트러블슈팅 가이드

8. **test-results/** (신규 디렉토리)
   - 테스트 결과 저장 디렉토리
   - README.md 포함

---

## 🔑 GitHub Secrets 등록 필수

다음 Secrets를 GitHub 저장소에 등록해야 합니다:

### 필수 (E2E 테스트용)
```
OPENAI_API_KEY       - OpenAI API 키
ANTHROPIC_API_KEY    - Anthropic (Claude) API 키  
GOOGLE_API_KEY       - Google (Gemini) API 키
```

### 선택 (Coverage용)
```
CODECOV_TOKEN        - Codecov 통합용 (선택사항)
```

### 등록 방법
1. GitHub 저장소 → **Settings**
2. **Secrets and variables** → **Actions**
3. **New repository secret** 클릭
4. Name과 Value 입력 후 **Add secret**

---

## 🚀 워크플로우 실행 방법

### 1. 자동 CI 테스트

**트리거:**
- `main` 또는 `develop` 브랜치에 Push
- Pull Request 생성

**실행 내용:**
```bash
pytest -m "not e2e" -n auto
```
- E2E 테스트 제외
- 병렬 실행
- Coverage 리포트 생성

**결과:**
- 테스트 실패 시 PR 머지 차단
- 테스트 리포트가 PR에 자동 코멘트
- 아티팩트로 결과 저장 (30일 보관)

---

### 2. E2E 테스트 (수동 실행)

**실행 방법:**
1. GitHub 저장소 → **Actions** 탭
2. "E2E Tests (LLM API Calls)" 선택
3. **Run workflow** 버튼 클릭
4. (선택) Test pattern 입력
   - 예: `test_llm` - test_llm.py만 실행
   - 예: `test_integration` - test_integration.py만 실행
   - 비워두면 모든 E2E 테스트 실행
5. **Run workflow** 확인

**실행 내용:**
```bash
pytest -m e2e --timeout=300
```
- E2E 테스트만 실행
- 실제 LLM API 호출
- 타임아웃 5분

**결과:**
- 실패 시 GitHub Issue 자동 생성
- Trace 파일 아티팩트로 저장 (7일 보관)


---

### 3. E2E 테스트 (스케줄 실행)

**자동 실행:**
- 매일 오전 3시 (KST) / 오후 6시 (UTC)
- cron: `'0 18 * * *'`

**실행 내용:**
- 모든 E2E 테스트 자동 실행
- 결과를 Actions에서 확인 가능

---

## 📊 테스트 결과 확인

### GitHub Actions에서 확인

1. **Actions 탭** 이동
2. 완료된 워크플로우 클릭
3. **Summary** 섹션 확인
   - 테스트 통과/실패 수
   - Coverage 퍼센트
   - 실행 시간

4. **Artifacts** 섹션에서 다운로드
   - `test-results-py3.X`: 테스트 결과 + Coverage
   - `e2e-test-results-py3.X`: E2E 결과
   - `e2e-traces-py3.X`: Trace 파일

### 로컬에서 확인

```bash
# 테스트 실행
pytest -m "not e2e" --cov=nexous --cov-report=html

# Coverage 리포트 확인
open test-results/htmlcov/index.html
```

---

## 🏷️ 테스트 마커 사용법


### 전체 파일 마킹

```python
import pytest

# test_llm.py 전체를 E2E로 마킹
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set"
    )
]
```

### 클래스 마킹

```python
@pytest.mark.e2e
@pytest.mark.integration
class TestLLMIntegration:
    def test_openai(self):
        # 실제 API 호출
        pass
```

### 개별 테스트 마킹

```python
@pytest.mark.e2e
def test_real_llm_call():
    # 실제 LLM 호출
    pass
```

### 마커로 선택 실행

```bash
# E2E 제외 (CI에서 사용)
pytest -m "not e2e"

# E2E만 실행
pytest -m e2e

# 특정 테스트만
pytest -m e2e -k test_llm

# 복합 조건
pytest -m "e2e and integration"
pytest -m "not (e2e or slow)"
```


---

## 📋 초기 설정 체크리스트

### 1단계: GitHub Secrets 등록
- [ ] OPENAI_API_KEY 등록
- [ ] ANTHROPIC_API_KEY 등록
- [ ] GOOGLE_API_KEY 등록
- [ ] (선택) CODECOV_TOKEN 등록

### 2단계: CI 워크플로우 확인
- [ ] PR 생성 후 자동 실행 확인
- [ ] 테스트 통과 확인
- [ ] PR 코멘트에 결과 표시 확인

### 3단계: E2E 워크플로우 테스트
- [ ] Actions 탭에서 수동 실행
- [ ] E2E 테스트 통과 확인
- [ ] 아티팩트 다운로드 확인

### 4단계: 로컬 환경 설정
- [ ] 의존성 설치: `pip install -r requirements.txt`
- [ ] pytest 플러그인 설치
- [ ] 로컬에서 테스트 실행 확인

---

## 🔍 테스트 작성 가이드

### E2E 테스트 작성 시 주의사항

1. **API 키 체크**
   ```python
   pytestmark = pytest.mark.skipif(
       not os.getenv("OPENAI_API_KEY"),
       reason="API key not set"
   )
   ```

2. **타임아웃 설정**
   ```python
   @pytest.mark.timeout(300)
   def test_long_running():
       pass
   ```


3. **비용 관리**
   - E2E 테스트는 최소한으로 작성
   - Mock을 사용할 수 있으면 Mock 사용
   - 스케줄 실행 빈도 조정 (필요시)

4. **Trace 파일 생성**
   ```python
   def test_with_trace(test_trace_dir):
       trace = TraceWriter(base_dir=str(test_trace_dir))
       # ... trace 사용
   ```

---

## 🛠️ 트러블슈팅

### 문제: CI 테스트 실패
**해결:**
1. Actions 로그 확인
2. 실패한 테스트 식별
3. 로컬에서 재현: `pytest tests/test_xxx.py -v`
4. 수정 후 커밋

### 문제: E2E 테스트 실패
**해결:**
1. API 키 확인
2. API 키 유효성 확인 (만료, 권한)
3. 로컬에서 실행: `pytest -m e2e -v`
4. 로그 확인: `test-results/pytest.log`

### 문제: Coverage가 낮음
**해결:**
1. HTML 리포트 확인: `test-results/htmlcov/index.html`
2. 커버되지 않은 코드 확인
3. 테스트 추가

### 문제: 테스트가 너무 느림
**해결:**
1. 병렬 실행: `pytest -n auto`
2. 느린 테스트에 `@pytest.mark.slow` 추가
3. 선택적 실행: `pytest -m "not slow"`


---

## 📈 다음 단계 (선택사항)

### 1. Coverage 목표 설정
```yaml
# ci.yml에 추가
- name: Check coverage threshold
  run: |
    pytest --cov=nexous --cov-fail-under=80
```

### 2. PR 템플릿 추가
`.github/pull_request_template.md` 생성:
```markdown
## 변경 사항
- 

## 테스트
- [ ] 로컬에서 테스트 통과
- [ ] CI 테스트 통과
- [ ] E2E 테스트 필요 시 수동 실행

## 체크리스트
- [ ] 코드 리뷰 요청
- [ ] 문서 업데이트
```

### 3. 배포 워크플로우 추가
`deploy.yml` 생성하여 자동 배포 구성

### 4. 성능 테스트 추가
`pytest-benchmark` 사용

### 5. 보안 스캔 추가
`bandit`, `safety` 통합

---

## 📚 참고 문서

- **전체 가이드**: `docs/CI_CD_GUIDE.md`
- **pytest 설정**: `pytest.ini`
- **CI 워크플로우**: `.github/workflows/ci.yml`
- **E2E 워크플로우**: `.github/workflows/e2e.yml`


---

## 🎯 요약

### 구축 완료
✅ **자동 CI 테스트** - PR/Push 시 자동 실행  
✅ **E2E 분리** - 비용 관리 및 선택적 실행  
✅ **멀티 Python 버전** - 3.10, 3.11, 3.12  
✅ **병렬 실행** - pytest-xdist 활용  
✅ **결과 보관** - 아티팩트로 30일 보관  
✅ **머지 게이트** - 테스트 실패 시 차단  
✅ **자동 리포트** - PR 코멘트로 결과 표시  

### 다음 작업
1. GitHub Secrets 등록 (3개 API 키)
2. PR 생성하여 CI 확인
3. E2E 테스트 수동 실행
4. 팀원에게 가이드 공유

---

**구축 완료일**: 2026-01-07  
**문서 버전**: 1.0  
**작성자**: NEXOUS CI/CD Team
