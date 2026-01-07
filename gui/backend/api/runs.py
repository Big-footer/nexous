"""
Runs API

Run 시작/상태 조회
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from services.run_service import RunService

router = APIRouter(prefix="/api/projects/{project_id}/runs", tags=["runs"])
service = RunService(projects_dir="projects", traces_dir="traces")


class StartRunRequest(BaseModel):
    run_id: Optional[str] = None


@router.get("")
async def list_runs(project_id: str) -> List[Dict[str, Any]]:
    """프로젝트의 Run 목록 조회"""
    return service.list_runs(project_id)


@router.post("")
async def start_run(project_id: str, request: StartRunRequest = None) -> Dict[str, Any]:
    """Run 시작"""
    try:
        run_id = request.run_id if request else None
        return service.start_run(project_id, run_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{run_id}")
async def get_run_status(project_id: str, run_id: str) -> Dict[str, Any]:
    """Run 상태 조회"""
    status = service.get_run_status(project_id, run_id)
    if not status:
        raise HTTPException(status_code=404, detail="Run not found")
    return status
