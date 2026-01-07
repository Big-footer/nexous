# NEXOUS LEVEL 3 - 플랫폼 고도화 로드맵

> "플랫폼 자체를 키우는 단계"
> 
> 진행 시점: 팀 협업 또는 대규모 운영 필요 시

---

## 1. LangSmith 연동 [우선순위: 높음]

### 목적
- 실행 모니터링 및 디버깅
- LLM 호출 추적
- 비용 분석

### 구현 방향
```python
# nexous/integrations/langsmith.py
from langsmith import Client

class LangSmithTracer:
    def trace_llm_call(self, ...)
    def trace_tool_call(self, ...)
    def flush(self)
```

---

## 2. Trace Replay [우선순위: 중간]

### 목적
- 과거 실행 재현
- A/B 테스트 (Preset 비교)
- 디버깅

### 구현 방향
```bash
nexous replay traces/project/run_xxx/trace.json
nexous replay --compare run_001 run_002
```

---

## 3. Job Queue / 분산 실행 [우선순위: 중간]

### 아키텍처
```
┌──────────┐     ┌─────────┐     ┌──────────┐
│ API/CLI  │ ──> │  Redis  │ ──> │  Worker  │
└──────────┘     │  Queue  │     │ (Celery) │
                 └─────────┘     └──────────┘
```

---

## 4. Preset 버저닝/승인 [우선순위: 낮음]

### 워크플로우
1. Preset 수정 → Draft
2. 검토 → Approve/Reject
3. Approve → Active

---

## 5. 조직별 권한 (RBAC) [우선순위: 낮음]

### 역할
- Admin: 모든 권한
- Editor: Preset/Project 수정
- Runner: 실행만
- Viewer: 조회만

---

## 진행 조건

- [ ] LEVEL 1-2 안정화 완료
- [ ] 실제 업무 1개월 이상 사용
- [ ] 팀 협업 필요성 발생

---

Created: 2026-01-04
Status: PLANNED
