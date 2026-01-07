"""
Projects API

프로젝트 CRUD
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from services.project_service import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])
service = ProjectService(projects_dir="projects")


class CreateProjectRequest(BaseModel):
    id: str
    name: Optional[str] = None
    description: Optional[str] = None


class UpdateProjectRequest(BaseModel):
    yaml_content: str


class ValidateRequest(BaseModel):
    yaml_content: str


@router.get("")
async def list_projects() -> List[Dict[str, Any]]:
    """프로젝트 목록 조회"""
    return service.list_projects()


@router.get("/{project_id}")
async def get_project(project_id: str) -> Dict[str, Any]:
    """프로젝트 조회"""
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("")
async def create_project(request: CreateProjectRequest) -> Dict[str, Any]:
    """프로젝트 생성"""
    try:
        return service.create_project(request.id, request.name, request.description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{project_id}")
async def update_project(project_id: str, request: UpdateProjectRequest) -> Dict[str, Any]:
    """프로젝트 업데이트"""
    try:
        return service.update_project(project_id, request.yaml_content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{project_id}")
async def delete_project(project_id: str) -> Dict[str, Any]:
    """프로젝트 삭제"""
    try:
        return service.delete_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/validate")
async def validate_yaml(request: ValidateRequest) -> Dict[str, Any]:
    """YAML 검증"""
    return service.validate_yaml(request.yaml_content)
