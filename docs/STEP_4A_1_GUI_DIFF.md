# NEXOUS STEP 4A-1: GUI Diff Viewer 구현 완료

## 📅 구현 날짜
2026-01-07

---

## 🎯 STEP 4A-1 목표 달성

### 완료된 핵심 질문 대응

1. **"무엇이 달라졌는가?"** ✅
   - Change List로 모든 변경사항 표시
   - Type별 분류 (LLM/TOOL/ERROR/METADATA)

2. **"언제 처음 달라졌는가?"** ✅
   - First Divergence 명확히 표시
   - Step Index로 정확한 위치 파악

3. **"왜 달라졌는가?"** ✅
   - Reason 필드로 원인 표시
   - Policy 정보 포함

4. **"이 차이가 허용 가능한가?"** ✅
   - Status (IDENTICAL/CHANGED/FAILED)
   - 색상 코드로 시각적 판단 지원

---

## 📁 생성된 파일

```
nexous/api/
└── diff_formatter.py (207 lines)
    └── DiffResultFormatter 클래스
        - format_for_api()
        - _extract_changes()
        - _determine_status()

frontend/src/components/
├── DiffModal.tsx (331 lines)
│   ├── DiffModal (Main)
│   ├── DiffSummaryComponent
│   ├── DiffFilter
│   ├── DiffChangeList
│   └── DiffChangeItem
└── DiffModal.css (465 lines)
    ├── Modal Overlay & Container
    ├── Summary Section
    ├── Tabs
    ├── Filter Section
    ├── Change List (Scrollable)
    ├── Report Tab
    └── Modal Actions
```

---

## 🎨 GUI 레이아웃 (명세 준수)

```
┌──────────────────────────────────────────────┐
│ Diff: run_A  ↔  run_B                 ✅     │
├──────────────────────────────────────────────┤
│ SUMMARY                               ✅     │
│  • Status: CHANGED                           │
│  • First Divergence: Step 5 (LLM)            │
│  • Reason: output_hash_changed               │
│                                              │
│  Counts:  LLM 2 | TOOL 1 | ERROR 0            │
├──────────────────────────────────────────────┤
│ FILTER                                ✅     │
│  [ All ] [ LLM ] [ TOOL ] [ ERROR ]           │
├──────────────────────────────────────────────┤
│ CHANGES (Scrollable)                  ✅     │
│  Step 5 | LLM | output changed               │
│   - baseline: abc                            │
│   - target:   def                            │
│                                              │
│  Step 8 | TOOL | params changed              │
│                                              │
├──────────────────────────────────────────────┤
│ [ Copy JSON ]   [ Export ]   [ Close ] ✅    │
└──────────────────────────────────────────────┘
```

---

## 📊 데이터 구조 (명세 준수)

### API Response Format

```json
{
  "ok": true,
  "summary": {
    "baseline_run": "run_A",
    "target_run": "run_B",
    "status": "CHANGED",
    "first_divergence": {
      "step_index": 5,
      "step_type": "LLM",
      "reason": "output_hash_changed"
    },
    "counts": {
      "llm": 2,
      "tool": 1,
      "errors": 0
    }
  },
  "changes": [
    {
      "step_index": 5,
      "type": "LLM",
      "field": "output",
      "baseline_value": "abc",
      "target_value": "def",
      "policy": {
        "model": "gpt-4o",
        "temperature": 0.2
      }
    }
  ],
  "report": "텍스트 리포트..."
}
```

---

## 🎨 색상 규칙 (명세 준수)

### Status Colors
- **IDENTICAL**: 🟢 Green (#10b981)
- **CHANGED**: 🟡 Orange (#f59e0b)
- **FAILED**: 🔴 Red (#ef4444)

### Type Colors
- **LLM**: 🔵 Blue (#3b82f6)
- **TOOL**: 🟣 Purple (#8b5cf6)
- **ERROR**: 🔴 Red (#ef4444)
- **METADATA**: ⚫ Gray (#6b7280)

---

## 🔧 컴포넌트 설계 (명세 준수)

### 1. DiffModal (Main)
**역할**: 전체 모달 관리
```typescript
<DiffModal
  diffResult={diffResult}
  onClose={() => setShowDiff(false)}
/>
```

**상태**:
- `activeFilter`: FilterType
- `activeTab`: 'CHANGES' | 'REPORT'

**기능**:
- JSON 복사
- Export (다운로드)
- Close

---

### 2. DiffSummaryComponent
**역할**: 요약 정보 표시

**표시 항목** (명세 준수):
- ✅ Status (IDENTICAL/CHANGED/FAILED)
- ✅ First Divergence
  - step_index
  - step_type
  - reason
- ✅ 변경 개수 요약 (LLM/TOOL/ERROR)

---

### 3. DiffFilter
**역할**: 필터 버튼

**옵션**:
- ALL (default)
- LLM
- TOOL
- ERROR

**동작** (명세 준수):
- ✅ 즉시 반영 (서버 재호출 없음)
- ✅ 프론트엔드 상태로 처리

---

### 4. DiffChangeList
**역할**: 변경 항목 리스트

**제한** (명세 준수):
- ✅ 최대 200개 표시
- ✅ 초과 시 경고 메시지
- ✅ Scrollable

---

### 5. DiffChangeItem
**역할**: 개별 변경 항목

**표시** (명세 준수):
```
[Step 5] LLM
Field: output
Baseline: abc123
Target:   def456
Policy: model=gpt-4o, temperature=0.2
```

---

## 📋 UX 제한 규칙 (명세 준수)

1. ✅ **기본 최대 표시**: 200개 Change Item
2. ✅ **초과 시**: "Too many changes, please filter" 안내
3. ✅ **Diff 결과**: Read-only

---

## 🚀 사용 예시

### 1. 기본 사용
```typescript
import { DiffModal } from './components/DiffModal';

function App() {
  const [showDiff, setShowDiff] = useState(false);
  const [diffResult, setDiffResult] = useState(null);
  
  const handleDiff = async () => {
    const response = await fetch('/api/diff', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        baseline: 'flood_analysis_ulsan',
        target: 'traces/flood_analysis_ulsan/run_002/trace.json'
      })
    });
    
    const result = await response.json();
    setDiffResult(result);
    setShowDiff(true);
  };
  
  return (
    <div>
      <button onClick={handleDiff}>Compare with Baseline</button>
      
      {showDiff && diffResult && (
        <DiffModal
          diffResult={diffResult}
          onClose={() => setShowDiff(false)}
        />
      )}
    </div>
  );
}
```

---

### 2. Backend 연동
```python
from nexous.api.diff_formatter import format_diff_for_gui
from nexous.trace import diff_traces

@app.post("/api/diff")
async def api_diff(request: DiffRequest):
    # Diff 실행
    diff_result = diff_traces(
        request.baseline_trace,
        request.target_trace,
        only=request.filter,
        show=request.show
    )
    
    # GUI 형식으로 변환
    gui_result = format_diff_for_gui(
        baseline_run=request.baseline_run_id,
        target_run=request.target_run_id,
        diff_result=diff_result,
        report_text=generate_report_text(diff_result)
    )
    
    return gui_result
```

---

## 🧪 테스트 방법

### 1. Mock Data 테스트
```typescript
const mockDiffResult = {
  ok: true,
  summary: {
    baseline_run: 'baseline_002_docker',
    target_run: 'run_003',
    status: 'CHANGED',
    first_divergence: {
      step_index: 5,
      step_type: 'LLM',
      reason: 'token_count_changed'
    },
    counts: {
      llm: 2,
      tool: 1,
      errors: 0
    }
  },
  changes: [
    {
      step_index: 5,
      type: 'LLM',
      field: 'tokens',
      baseline_value: '461',
      target_value: '301',
      policy: {
        model: 'gpt-4o',
        temperature: 0.3
      }
    },
    {
      step_index: 5,
      type: 'LLM',
      field: 'latency',
      baseline_value: '5747ms',
      target_value: '4063ms',
      policy: null
    }
  ],
  report: 'Diff Report:\n...'
};

<DiffModal 
  diffResult={mockDiffResult}
  onClose={() => console.log('closed')}
/>
```

---

### 2. 필터 테스트
```typescript
// ALL 필터 → 모든 changes 표시
// LLM 필터 → type === 'LLM'만 표시
// TOOL 필터 → type === 'TOOL'만 표시
// ERROR 필터 → type === 'ERROR'만 표시
```

---

### 3. 액션 테스트
```typescript
// Copy JSON → clipboard에 JSON 복사
// Export → JSON 파일 다운로드
// Close → 모달 닫기
```

---

## ✅ STEP 4A-1 완료 조건 검증

| 조건 | 상태 | 구현 위치 |
|------|------|----------|
| Summary가 정확히 표시된다 | ✅ | DiffSummaryComponent |
| First Divergence가 한 눈에 보인다 | ✅ | first-divergence div |
| Filter가 즉시 반영된다 | ✅ | DiffFilter (프론트엔드 상태) |
| Change Item이 스펙대로 표시된다 | ✅ | DiffChangeItem |
| JSON/Report 복사가 가능하다 | ✅ | handleCopyJSON/handleCopyReport |

**STEP 4A-1 완료율: 5/5 (100%) ✅**

---

## 📊 명세 준수 체크리스트

### 1. 데이터 구조 ✅
- [x] summary 필드 (baseline_run, target_run, status, first_divergence, counts)
- [x] changes 배열
- [x] report 텍스트

### 2. GUI 레이아웃 ✅
- [x] Summary 영역
- [x] Filter 영역
- [x] Changes 영역 (Scrollable)
- [x] Modal Actions

### 3. Summary 표시 규칙 ✅
- [x] Status (IDENTICAL/CHANGED/FAILED)
- [x] First Divergence (step_index, step_type, reason)
- [x] 변경 개수 요약
- [x] 색상 규칙 (Green/Orange/Red)

### 4. Filter 동작 ✅
- [x] 기본값 ALL
- [x] 즉시 반영 (서버 재호출 없음)
- [x] Type별 필터링

### 5. Change Item 표시 ✅
- [x] Step Index
- [x] Type (LLM/TOOL/ERROR)
- [x] Changed Field
- [x] Baseline vs Target 값
- [x] Policy 정보

### 6. Report 탭 ✅
- [x] 텍스트 리포트 표시
- [x] 복사 버튼

### 7. UX 제한 ✅
- [x] 최대 200개 표시
- [x] 초과 시 안내
- [x] Read-only

### 8. 컴포넌트 설계 ✅
- [x] DiffModal
- [x] DiffSummary
- [x] DiffFilter
- [x] DiffChangeList
- [x] DiffChangeItem

---

## 🎊 결론

**NEXOUS STEP 4A-1 완전 구현 완료!**

- 🎨 GUI Diff Viewer 구현
- 📊 명세 100% 준수
- ✅ 모든 완료 조건 충족
- 🔧 컴포넌트 분리 완료
- 💅 스타일링 완료
- 📱 반응형 지원

**다음 단계**: STEP 4A-2 (Baseline/Replay 버튼 연동)

---

## 🔗 통합 방법

### 1. Frontend 프로젝트에 추가
```bash
cp frontend/src/components/DiffModal.* {your-react-project}/src/components/
```

### 2. Backend API 추가
```python
# main.py 또는 api.py에 추가
from nexous.api.diff_formatter import format_diff_for_gui
```

### 3. 사용
```typescript
import DiffModal from './components/DiffModal';
```

**준비 완료!** 🚀
