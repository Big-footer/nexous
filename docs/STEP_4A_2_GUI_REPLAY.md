# NEXOUS STEP 4A-2: GUI Replay(DRY) 타임라인 UI 구현 완료

## 📅 구현 날짜
2026-01-07

---

## 🎯 STEP 4A-2 목표 달성

### 완료된 핵심 질문 대응

1. **"실행은 어떤 순서로 진행되었는가?"** ✅
   - Timeline으로 step_index 순서대로 표시
   - SYSTEM → LLM → TOOL → ERROR 흐름 시각화

2. **"각 단계에서 무엇이 일어났는가?"** ✅
   - Step Detail 패널로 상세 정보 표시
   - LLM: provider, model, tokens
   - TOOL: tool_name, input/output
   - ERROR: error_type, message

3. **"LLM/Tool/Error가 언제 발생했는가?"** ✅
   - 색상 코드로 즉시 구분
   - 🔵 LLM, 🟣 TOOL, 🔴 ERROR, ⚪ SYSTEM

4. **"전체 실행의 구조를 한눈에 파악할 수 있는가?"** ✅
   - Summary: 전체 Step 개수 및 유형별 분포
   - Timeline: 전체 흐름 Scrollable 리스트

---

## 📁 생성된 파일

```
nexous/api/
└── replay_formatter.py (170 lines)
    └── ReplayResultFormatter
        - format_for_api() 핵심 메서드
        - _build_timeline() 타임라인 생성
        - _build_summary() Summary 생성

frontend/src/components/
├── ReplayPanel.tsx (308 lines)
│   ├── ReplayPanel (Main Component)
│   ├── ReplaySummaryComponent
│   ├── ReplayTimeline
│   ├── ReplayTimelineItem
│   └── ReplayStepDetail
└── ReplayPanel.css (422 lines)
    ├── Panel Overlay & Container
    ├── Summary Section
    ├── Replay Content (Timeline + Detail)
    ├── Timeline Section
    ├── Timeline Item
    ├── Step Detail Section
    └── Panel Actions

docs/
└── STEP_4A_2_GUI_REPLAY.md (이 문서)
```

**총 3개 파일, 900 lines**

---

## 🎨 GUI 레이아웃 (명세 준수)

```
┌──────────────────────────────────────────────┐
│ ✅ Replay (DRY) — run_XXXX                   │
├──────────────────────────────────────────────┤
│ ✅ SUMMARY                                   │
│  • Status: COMPLETED (🟢)                    │
│  • Steps: 12 (LLM 6 | TOOL 5 | ERROR 1)      │
├──────────────────────────────────────────────┤
│ ✅ TIMELINE (60%)          │ STEP DETAIL (40%)│
│  [0] ⚪ SYSTEM             │                 │
│      Start Run         —  │  Step 1 | LLM    │
│                            │                 │
│  [1] 🔵 LLM                │  Provider: openai│
│      Planner (gpt-4o) 842ms│  Model: gpt-4o   │
│                            │  Attempt: 1      │
│  [2] 🟣 TOOL               │  Tokens: 461     │
│      python_exec      120ms│  Status: OK      │
│                            │                 │
│  [3] 🔴 ERROR              │                 │
│      timeout           —   │                 │
│  ...                       │                 │
├──────────────────────────────────────────────┤
│ ✅ [ Copy Report ]   [ Close ]               │
└──────────────────────────────────────────────┘
```

---

## 📊 데이터 구조 (명세 준수)

### API Response Format

```json
{
  "ok": true,
  "mode": "dry",
  "summary": {
    "total_steps": 12,
    "llm_steps": 6,
    "tool_steps": 5,
    "error_steps": 1,
    "status": "COMPLETED"
  },
  "timeline": [
    {
      "step_index": 0,
      "type": "SYSTEM",
      "label": "Start Run",
      "duration_ms": 0
    },
    {
      "step_index": 1,
      "type": "LLM",
      "label": "Planner (gpt-4o)",
      "duration_ms": 842,
      "meta": {
        "agent_id": "planner_01",
        "provider": "openai",
        "model": "gpt-4o",
        "attempt": 1,
        "tokens": {
          "input": 256,
          "output": 205,
          "total": 461
        },
        "status": "OK"
      }
    },
    {
      "step_index": 2,
      "type": "TOOL",
      "label": "python_exec",
      "duration_ms": 120,
      "meta": {
        "agent_id": "executor_01",
        "tool_name": "python_exec",
        "status": "OK",
        "input_summary": "import pandas...",
        "output_summary": "Result: 42"
      }
    },
    {
      "step_index": 3,
      "type": "ERROR",
      "label": "planner_01 error",
      "duration_ms": 0,
      "meta": {
        "agent_id": "planner_01",
        "error_type": "TimeoutError",
        "message": "Request timed out after 30s"
      }
    }
  ],
  "report": "텍스트 리포트..."
}
```

---

## 🎨 색상 규칙 (명세 준수)

### Type Colors
```css
LLM: #3b82f6    /* 🔵 Blue */
TOOL: #8b5cf6   /* 🟣 Purple */
ERROR: #ef4444  /* 🔴 Red */
SYSTEM: #9ca3af /* ⚪ Gray */
```

### Status Colors
```css
COMPLETED: #10b981 /* 🟢 Green */
FAILED: #ef4444    /* 🔴 Red */
OK: #10b981        /* 🟢 Green */
```

---

## 🔧 컴포넌트 설계 (명세 준수)

### 1. ReplayPanel (Main)
**역할**: 전체 패널 관리
```typescript
<ReplayPanel
  replayResult={replayResult}
  runId="run_20260107_143617"
  onClose={() => setShowReplay(false)}
/>
```

**상태**:
- `selectedStepIndex`: number | null

**기능**:
- Report 복사
- Close

---

### 2. ReplaySummaryComponent
**역할**: 요약 정보 표시

**표시 항목** (명세 준수):
- ✅ Status (COMPLETED/FAILED)
- ✅ 전체 Step 수
- ✅ Step 유형별 개수 (LLM/TOOL/ERROR)

---

### 3. ReplayTimeline
**역할**: 타임라인 리스트

**정렬** (명세 준수):
- ✅ step_index 오름차순 고정

**표시 항목**:
- Step Index
- Type (색상 Badge)
- Label (Agent/Tool 이름)
- Duration (ms)

---

### 4. ReplayTimelineItem
**역할**: 개별 타임라인 항목

**인터랙션**:
- 클릭 시 선택
- 선택 시 하이라이트
- Hover 효과

---

### 5. ReplayStepDetail
**역할**: Step 상세 정보 표시

**유형별 표시** (명세 준수):

**LLM Step**:
- Provider
- Model
- Attempt
- Tokens
- Status

**TOOL Step**:
- Tool Name
- Status
- Input Summary (200자 제한)
- Output Summary (200자 제한)

**ERROR Step**:
- Error Type
- Message

**SYSTEM Step**:
- System Event

⚠️ **Input/Output 전문은 기본 숨김** (명세 준수)

---

## 🚀 사용 예시

### 1. React 컴포넌트 사용
```typescript
import ReplayPanel from './components/ReplayPanel';

function App() {
  const [showReplay, setShowReplay] = useState(false);
  const [replayResult, setReplayResult] = useState(null);
  
  const handleReplay = async (runId: string) => {
    const response = await fetch('/api/replay', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        trace_path: `traces/my_project/${runId}/trace.json`,
        mode: 'dry'
      })
    });
    
    const result = await response.json();
    setReplayResult(result);
    setShowReplay(true);
  };
  
  return (
    <>
      <button onClick={() => handleReplay('run_001')}>
        Replay (DRY)
      </button>
      
      {showReplay && replayResult && (
        <ReplayPanel
          replayResult={replayResult}
          runId="run_001"
          onClose={() => setShowReplay(false)}
        />
      )}
    </>
  );
}
```

---

### 2. Backend API 연동
```python
from nexous.api.replay_formatter import format_replay_for_gui
from pathlib import Path

@app.post("/api/replay")
async def api_replay(trace_path: str, mode: str = "dry"):
    if mode != "dry":
        return {"ok": False, "error": "Only DRY mode supported in GUI"}
    
    # Trace 존재 확인
    trace_file = Path(trace_path)
    if not trace_file.exists():
        return {"ok": False, "error": "Trace not found"}
    
    # GUI 형식으로 변환
    gui_result = format_replay_for_gui(
        trace_path=str(trace_file),
        mode=mode
    )
    
    return gui_result
```

---

## 🧪 테스트 방법

### 1. Mock Data 테스트
```typescript
const mockReplayResult = {
  ok: true,
  mode: 'dry',
  summary: {
    total_steps: 12,
    llm_steps: 6,
    tool_steps: 5,
    error_steps: 1,
    status: 'COMPLETED'
  },
  timeline: [
    {
      step_index: 0,
      type: 'SYSTEM',
      label: 'Start Run',
      duration_ms: 0
    },
    {
      step_index: 1,
      type: 'LLM',
      label: 'Planner (gpt-4o)',
      duration_ms: 842,
      meta: {
        agent_id: 'planner_01',
        provider: 'openai',
        model: 'gpt-4o',
        attempt: 1,
        tokens: {
          input: 256,
          output: 205,
          total: 461
        },
        status: 'OK'
      }
    },
    {
      step_index: 2,
      type: 'TOOL',
      label: 'python_exec',
      duration_ms: 120,
      meta: {
        tool_name: 'python_exec',
        status: 'OK'
      }
    }
  ],
  report: 'Replay Report...'
};

<ReplayPanel 
  replayResult={mockReplayResult}
  runId="run_test_001"
  onClose={() => console.log('closed')}
/>
```

---

### 2. Timeline 인터랙션 테스트
```typescript
// Step 선택 → Detail 표시
// Step 변경 → Detail 업데이트
// 스크롤 → Timeline 및 Detail 독립 스크롤
```

---

### 3. 액션 테스트
```typescript
// Copy Report → clipboard에 텍스트 복사
// Close → 패널 닫기
```

---

## ✅ STEP 4A-2 완료 조건 검증

| 조건 | 상태 | 구현 위치 |
|------|------|----------|
| DRY replay 결과가 GUI에 표시된다 | ✅ | ReplayPanel |
| 전체 실행 흐름이 타임라인으로 보인다 | ✅ | ReplayTimeline |
| LLM/TOOL/ERROR가 색상/라벨로 구분된다 | ✅ | step-type-badge CSS |
| Step 상세 정보가 정확히 표시된다 | ✅ | ReplayStepDetail |

**STEP 4A-2 완료율: 4/4 (100%) ✅**

---

## 📊 명세 준수 체크리스트

### 1. 역할 정의 ✅
- [x] 4가지 핵심 질문 대응
- [x] DRY Replay 전용 (FULL 비활성)

### 2. 데이터 구조 ✅
- [x] summary 필드 (total_steps, llm_steps, tool_steps, error_steps, status)
- [x] timeline 배열
- [x] report 텍스트

### 3. GUI 레이아웃 ✅
- [x] Summary 영역
- [x] Timeline 영역 (60%)
- [x] Step Detail 영역 (40%)
- [x] Panel Actions

### 4. Summary 표시 규칙 ✅
- [x] Status (COMPLETED/FAILED)
- [x] 전체 Step 수
- [x] Step 유형별 개수
- [x] 색상 규칙 (Blue/Purple/Red/Gray)

### 5. Timeline 표시 규칙 ✅
- [x] Step Index
- [x] Type (색상 Badge)
- [x] Label
- [x] Duration(ms)
- [x] step_index 오름차순 정렬

### 6. Step Detail 패널 ✅
- [x] LLM Step (Provider, Model, Attempt, Tokens)
- [x] TOOL Step (Tool Name, Input/Output 요약)
- [x] ERROR Step (Error Type, Message)
- [x] Input/Output 전문 숨김

### 7. UX 제한 ✅
- [x] Timeline 스크롤 (제한 없음)
- [x] Step Detail 한 번에 하나만
- [x] Read-only

### 8. 컴포넌트 설계 ✅
- [x] ReplayPanel
- [x] ReplaySummary
- [x] ReplayTimeline
- [x] ReplayTimelineItem
- [x] ReplayStepDetail

---

## 🎊 결론

**NEXOUS STEP 4A-2 완전 구현 완료!**

- 🎨 GUI Replay(DRY) Viewer 구현
- 📊 명세 100% 준수
- ✅ 모든 완료 조건 충족
- 🔧 컴포넌트 분리 완료
- 💅 스타일링 완료
- 📱 반응형 지원

**다음 단계**: STEP 4A-3 (Run History 목록)

---

## 🔗 통합 방법

### 1. Frontend 프로젝트에 추가
```bash
cp frontend/src/components/ReplayPanel.* {your-react-project}/src/components/
```

### 2. Backend API 추가
```python
# main.py 또는 api.py에 추가
from nexous.api.replay_formatter import format_replay_for_gui
```

### 3. 사용
```typescript
import ReplayPanel from './components/ReplayPanel';
```

**준비 완료!** 🚀
