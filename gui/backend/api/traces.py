"""
Traces API

Trace 조회
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from services.trace_service import TraceService

router = APIRouter(prefix="/api/projects/{project_id}/runs/{run_id}", tags=["traces"])
service = TraceService(traces_dir="traces")


@router.get("/trace")
async def get_trace(project_id: str, run_id: str) -> Dict[str, Any]:
    """trace.json 전체 반환"""
    trace = service.get_trace(project_id, run_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


@router.get("/artifacts")
async def get_artifacts(project_id: str, run_id: str) -> List[Dict[str, Any]]:
    """artifacts 반환"""
    return service.get_artifacts(project_id, run_id)


@router.get("/agents")
async def get_agents(project_id: str, run_id: str) -> List[Dict[str, Any]]:
    """agents 반환"""
    return service.get_agents(project_id, run_id)


@router.get("/summary")
async def get_summary(project_id: str, run_id: str) -> Dict[str, Any]:
    """summary 반환"""
    summary = service.get_summary(project_id, run_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    return summary


@router.get("/errors")
async def get_errors(project_id: str, run_id: str) -> List[Dict[str, Any]]:
    """errors 반환"""
    return service.get_errors(project_id, run_id)
