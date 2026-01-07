# PROMETHEUS 테스트

## 테스트 실행 방법

```bash
# 전체 테스트 (Mock만)
pytest tests/ -v

# 통합 테스트 포함 (실제 API 사용)
pytest tests/ -v -m integration

# 특정 테스트만
pytest tests/test_agents.py::TestImports -v

# 커버리지 포함
pytest tests/ -v --cov=prometheus --cov-report=html
```

## 테스트 구조

- `test_agents.py`: Agent 유닛 테스트
  - Import 테스트
  - State 테스트
  - Agent 초기화 테스트 (Mock)
  - 출력 스키마 테스트
  - 워크플로우 테스트
  - 통합 테스트 (실제 API)
  - Tool 테스트

## 테스트 마커

- `@pytest.mark.integration`: 실제 API를 사용하는 통합 테스트
