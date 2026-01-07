"""
NEXOUS GUI Backend

FastAPI 서버
"""

import sys
from pathlib import Path

# NEXOUS 루트 경로 추가
NEXOUS_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(NEXOUS_ROOT))

# Backend 경로 추가
BACKEND_ROOT = Path(__file__).parent
sys.path.insert(0, str(BACKEND_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.projects import router as projects_router
from api.runs import router as runs_router
from api.traces import router as traces_router

app = FastAPI(
    title="NEXOUS API",
    description="NEXOUS Multi-Agent Orchestration System",
    version="0.1.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(projects_router)
app.include_router(runs_router)
app.include_router(traces_router)


@app.get("/")
async def root():
    return {"message": "NEXOUS API", "version": "0.1.0"}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def startup():
    # 작업 디렉토리를 NEXOUS 루트로 설정
    import os
    os.chdir(NEXOUS_ROOT)
    print(f"[NEXOUS] Working directory: {os.getcwd()}")


if __name__ == "__main__":
    import uvicorn
    import os
    
    os.chdir(NEXOUS_ROOT)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
