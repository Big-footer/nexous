# PROMETHEUS

## Project-based AI Agent Factory & Orchestrator

PROMETHEUS는 프로젝트 단위로 전용 AI Agent를 생성하고 오케스트레이션하는 시스템입니다.

## 핵심 특징

- **멀티 LLM 지원**: GPT, Gemini, Claude 통합
- **프로젝트 기반 Agent 생성**: 프로젝트마다 전용 Agent 인스턴스 생성
- **Agent Factory + Orchestrator**: PROMETHEUS가 Agent 생성 및 조율 담당
- **Tool 기반 실행**: 확장 가능한 Tool 시스템
- **LangChain 기반**: Python 3.11 + LangChain

## 아키텍처 개요

```
PROMETHEUS (Meta Agent / Orchestrator)
    │
    ├── Agent Factory ──→ ProjectAgent 생성
    │
    ├── Router ──→ 작업 분배
    │
    └── Lifecycle Manager ──→ Agent 생명주기 관리

ProjectAgent
    ├── PlannerAgent (계획 수립)
    ├── ExecutorAgent (실행)
    ├── WriterAgent (문서 작성)
    └── QAAgent (검증)
```

## 디렉토리 구조

```
PROMETHEUS/
├── prometheus/           # 메인 패키지
│   ├── controller/       # Meta Agent, Factory, Router, Lifecycle
│   ├── agents/           # Agent 정의
│   ├── tools/            # Tool 정의
│   ├── llm/              # LLM 클라이언트
│   ├── memory/           # 메모리 및 벡터 스토어
│   ├── config/           # 설정 스키마 및 로더
│   └── utils/            # 유틸리티
├── projects/             # 프로젝트 디렉토리
├── templates/            # 템플릿 파일
└── tests/                # 테스트
```

## 설치

```bash
pip install -r requirements.txt
```

## 환경 설정

`.env.example`을 `.env`로 복사하고 API 키를 설정하세요.

```bash
cp .env.example .env
```

## 사용법

TODO: 사용법 문서화 예정

## 라이선스

MIT License
# NEXOUS CI/CD 구축 완료
