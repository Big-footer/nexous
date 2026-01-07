# NEXOUS GUI

## 프로젝트 실행 콘솔 (챗봇 아님)

NEXOUS GUI는 **Project YAML을 선택/편집/검증/실행**하고 **Run/Trace/Artifacts를 관찰**하는 콘솔입니다.

> ⚠️ **중요**: 이것은 챗봇 UI가 아닙니다. 대화/질문/응답 기능이 없습니다.

---

## 📁 폴더 구조

```
gui/
├── backend/                     # FastAPI 백엔드
│   ├── main.py                  # API 서버 (1100+ lines)
│   └── requirements.txt         # Python 의존성
│
├── frontend/                    # React 프론트엔드
│   ├── src/
│   │   ├── App.tsx              # 메인 앱 (3열 레이아웃)
│   │   ├── api.ts               # API 클라이언트
│   │   ├── types.ts             # TypeScript 타입
│   │   └── components/
│   │       ├── Header.tsx           # 헤더
│   │       ├── ProjectList.tsx      # 프로젝트 목록 (좌측)
│   │       ├── MainPanel.tsx        # 탭 컨테이너 (중앙)
│   │       ├── ProjectEditor.tsx    # YAML 편집기
│   │       ├── RunConsole.tsx       # 실행 콘솔
│   │       ├── TraceViewer.tsx      # Trace 뷰어
│   │       └── RunHistoryPanel.tsx  # Run History (우측)
│   ├── package.json
│   └── vite.config.ts
│
└── README.md

projects/                        # Project YAML 저장
traces/                          # Trace 저장
outputs/                         # Artifacts 저장
```

---

## 🚀 로컬 실행 방법

### 1. 백엔드 실행

```bash
cd gui/backend

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
uvicorn main:app --reload --port 8000
```

### 2. 프론트엔드 실행

```bash
cd gui/frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

### 3. 브라우저에서 접속

```
http://localhost:5173
```

---

## 🖥️ 화면 구성 (3열 레이아웃)

```
┌────────────────────┬────────────────────────────────────┬────────────────────┐
│     Projects       │           Main Panel               │  Trace/Artifacts   │
│     (좌측)         │    [탭] Project | Run | Trace      │      (우측)        │
│                    │                                    │                    │
│ • flood_analysis   │  ┌──────────────────────────────┐  │ Run: run_001       │
│ • traffic_sim      │  │                              │  │ Status: RUNNING    │
│                    │  │      (탭 내용)                │  │ ──────────────── │
│ [+ New] [Delete]   │  │                              │  │ Trace Timeline     │
│                    │  └──────────────────────────────┘  │ Run History        │
└────────────────────┴────────────────────────────────────┴────────────────────┘
```

### 화면 A - Project 목록 (좌측)
- `projects/` 폴더의 YAML 파일 목록 표시
- New Project 버튼으로 템플릿 기반 생성
- 프로젝트 선택/삭제

### 화면 B - Project 편집기 (중앙 - Project 탭)
- Monaco Editor 기반 YAML 편집
- 실시간 스키마 검증
- Agents/Artifacts 미리보기
- Save / Validate / Run 버튼

### 화면 C - Run 콘솔 (중앙 - Run 탭)
- Run 정보 (Project, Run ID, Status)
- 현재 Agent + Stage (INPUT → LLM → TOOL → OUTPUT)
- 실시간 로그 스트리밍 (WebSocket)
- Stop 버튼

### 화면 D - Trace 뷰어 (중앙 - Trace 탭)
- Trace 타임라인 (step별 목록)
- Step 상세 (LLM/Tool 정보)
- Artifacts 탭 (결과물 목록)

### 우측 - Run History
- 현재 Run 상태
- Trace Timeline 미리보기
- 최근 Run 목록

---

## 📡 API 엔드포인트

### Projects
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/projects` | 프로젝트 목록 |
| GET | `/api/projects/{id}` | 프로젝트 상세 |
| POST | `/api/projects` | 프로젝트 생성 |
| PUT | `/api/projects/{id}` | 프로젝트 저장 |
| DELETE | `/api/projects/{id}` | 프로젝트 삭제 |
| POST | `/api/projects/{id}/validate` | YAML 검증 |

### Runs
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/runs` | Run 목록 |
| POST | `/api/runs` | Run 생성/실행 |
| GET | `/api/runs/{id}` | Run 상세 |
| POST | `/api/runs/{id}/stop` | Run 중지 |
| GET | `/api/runs/{id}/trace` | Trace 조회 |
| GET | `/api/runs/{id}/artifacts` | Artifacts 목록 |
| GET | `/api/runs/{id}/logs` | 로그 조회 |

### WebSocket
| Endpoint | 설명 |
|----------|------|
| `WS /api/runs/{id}/stream` | 실시간 로그 스트리밍 |

---

## ✅ YAML 검증 규칙

1. `project.id` 필수
2. `agents[].id` 중복 불가
3. `dependencies` 참조 유효성
4. `artifacts[].source` 참조 유효성

---

## 🔧 기술 스택

### Backend
- FastAPI
- Pydantic v2
- WebSocket (실시간 스트리밍)
- PyYAML

### Frontend
- React 18 + TypeScript
- Vite
- TailwindCSS
- Monaco Editor (YAML 편집)
- Lucide Icons

---

## 📋 사용자 행위 (UX)

사용자가 하는 행위는 항상:
1. **프로젝트 선택** - 좌측 목록에서 클릭
2. **YAML 편집/검증** - 에디터에서 수정 후 Validate
3. **실행(Run) 시작/중지** - Run 버튼 클릭
4. **결과/Trace 탐색** - Trace 뷰어에서 확인

> ❌ "대화", "질문", "응답" 개념 없음
