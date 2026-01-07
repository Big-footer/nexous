"""
NEXUS Artifact Manager

프로젝트 실행 결과물(artifact)을 관리합니다.
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum
import hashlib


class ArtifactType(str, Enum):
    """Artifact 유형"""
    DOCUMENT = "document"       # 문서 (docx, pdf, md)
    CODE = "code"               # 코드 (py, js, etc)
    DATA = "data"               # 데이터 (csv, json, xlsx)
    IMAGE = "image"             # 이미지 (png, jpg, svg)
    REPORT = "report"           # 보고서
    MODEL = "model"             # 모델 파일
    CONFIG = "config"           # 설정 파일
    LOG = "log"                 # 로그
    OTHER = "other"


class ArtifactMetadata(BaseModel):
    """Artifact 메타데이터"""
    id: str = Field(description="고유 ID")
    name: str = Field(description="파일명")
    type: ArtifactType = Field(description="유형")
    path: str = Field(description="저장 경로")
    size: int = Field(default=0, description="파일 크기 (bytes)")
    checksum: Optional[str] = Field(default=None, description="MD5 체크섬")
    
    # 생성 정보
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: Optional[str] = Field(default=None, description="생성 Agent")
    
    # 프로젝트 연결
    project_id: Optional[str] = Field(default=None)
    trace_id: Optional[str] = Field(default=None)
    
    # 추가 정보
    description: Optional[str] = Field(default=None)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ArtifactManager:
    """
    Artifact Manager
    
    프로젝트 결과물을 저장, 조회, 관리합니다.
    """
    
    def __init__(self, base_dir: Union[str, Path] = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / ".nexus" / "artifacts"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self._index_file = self.base_dir / "index.json"
        self._index: Dict[str, ArtifactMetadata] = self._load_index()
    
    def _load_index(self) -> Dict[str, ArtifactMetadata]:
        """인덱스 로드"""
        if self._index_file.exists():
            try:
                with open(self._index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return {k: ArtifactMetadata(**v) for k, v in data.items()}
            except:
                pass
        return {}
    
    def _save_index(self):
        """인덱스 저장"""
        data = {k: v.model_dump(mode='json') for k, v in self._index.items()}
        with open(self._index_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    
    def _generate_id(self, name: str) -> str:
        """고유 ID 생성"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        hash_input = f"{name}_{timestamp}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """파일 체크섬 계산"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _infer_type(self, file_path: Path) -> ArtifactType:
        """파일 확장자로 유형 추론"""
        ext = file_path.suffix.lower()
        
        type_map = {
            # Document
            '.md': ArtifactType.DOCUMENT,
            '.txt': ArtifactType.DOCUMENT,
            '.docx': ArtifactType.DOCUMENT,
            '.pdf': ArtifactType.DOCUMENT,
            '.html': ArtifactType.DOCUMENT,
            
            # Code
            '.py': ArtifactType.CODE,
            '.js': ArtifactType.CODE,
            '.ts': ArtifactType.CODE,
            '.java': ArtifactType.CODE,
            '.cpp': ArtifactType.CODE,
            '.inp': ArtifactType.CODE,  # SWMM
            
            # Data
            '.csv': ArtifactType.DATA,
            '.json': ArtifactType.DATA,
            '.xlsx': ArtifactType.DATA,
            '.xml': ArtifactType.DATA,
            '.geojson': ArtifactType.DATA,
            '.shp': ArtifactType.DATA,
            
            # Image
            '.png': ArtifactType.IMAGE,
            '.jpg': ArtifactType.IMAGE,
            '.jpeg': ArtifactType.IMAGE,
            '.svg': ArtifactType.IMAGE,
            '.gif': ArtifactType.IMAGE,
            '.tif': ArtifactType.IMAGE,
            '.tiff': ArtifactType.IMAGE,
            
            # Config
            '.yaml': ArtifactType.CONFIG,
            '.yml': ArtifactType.CONFIG,
            '.toml': ArtifactType.CONFIG,
            '.ini': ArtifactType.CONFIG,
            
            # Log
            '.log': ArtifactType.LOG,
        }
        
        return type_map.get(ext, ArtifactType.OTHER)
    
    def save(
        self,
        content: Union[str, bytes, Path],
        name: str,
        artifact_type: Optional[ArtifactType] = None,
        project_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        created_by: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ArtifactMetadata:
        """
        Artifact 저장
        
        Args:
            content: 파일 내용 (문자열, 바이트, 또는 기존 파일 경로)
            name: 파일명
            artifact_type: 유형 (자동 추론 가능)
            project_id: 프로젝트 ID
            trace_id: Trace ID
            created_by: 생성 Agent
            description: 설명
            tags: 태그
            metadata: 추가 메타데이터
        
        Returns:
            ArtifactMetadata
        """
        artifact_id = self._generate_id(name)
        
        # 저장 디렉토리
        if project_id:
            save_dir = self.base_dir / project_id
        else:
            save_dir = self.base_dir / "default"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # 파일 저장
        save_path = save_dir / name
        
        if isinstance(content, Path):
            # 기존 파일 복사
            shutil.copy2(content, save_path)
        elif isinstance(content, bytes):
            with open(save_path, 'wb') as f:
                f.write(content)
        else:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # 유형 추론
        if artifact_type is None:
            artifact_type = self._infer_type(save_path)
        
        # 메타데이터 생성
        artifact_meta = ArtifactMetadata(
            id=artifact_id,
            name=name,
            type=artifact_type,
            path=str(save_path),
            size=save_path.stat().st_size,
            checksum=self._calculate_checksum(save_path),
            project_id=project_id,
            trace_id=trace_id,
            created_by=created_by,
            description=description,
            tags=tags or [],
            metadata=metadata or {},
        )
        
        # 인덱스 업데이트
        self._index[artifact_id] = artifact_meta
        self._save_index()
        
        return artifact_meta
    
    def get(self, artifact_id: str) -> Optional[ArtifactMetadata]:
        """Artifact 메타데이터 조회"""
        return self._index.get(artifact_id)
    
    def read(self, artifact_id: str) -> Optional[Union[str, bytes]]:
        """Artifact 내용 읽기"""
        meta = self.get(artifact_id)
        if not meta:
            return None
        
        path = Path(meta.path)
        if not path.exists():
            return None
        
        # 바이너리 파일 여부
        binary_types = {ArtifactType.IMAGE, ArtifactType.MODEL}
        
        if meta.type in binary_types:
            with open(path, 'rb') as f:
                return f.read()
        else:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
    
    def delete(self, artifact_id: str) -> bool:
        """Artifact 삭제"""
        meta = self.get(artifact_id)
        if not meta:
            return False
        
        # 파일 삭제
        path = Path(meta.path)
        if path.exists():
            path.unlink()
        
        # 인덱스에서 제거
        del self._index[artifact_id]
        self._save_index()
        
        return True
    
    def list_by_project(self, project_id: str) -> List[ArtifactMetadata]:
        """프로젝트별 Artifact 목록"""
        return [a for a in self._index.values() if a.project_id == project_id]
    
    def list_by_trace(self, trace_id: str) -> List[ArtifactMetadata]:
        """Trace별 Artifact 목록"""
        return [a for a in self._index.values() if a.trace_id == trace_id]
    
    def list_by_type(self, artifact_type: ArtifactType) -> List[ArtifactMetadata]:
        """유형별 Artifact 목록"""
        return [a for a in self._index.values() if a.type == artifact_type]
    
    def list_all(self) -> List[ArtifactMetadata]:
        """모든 Artifact 목록"""
        return list(self._index.values())
    
    def export_project(self, project_id: str, output_dir: Union[str, Path]) -> Path:
        """프로젝트 Artifact 내보내기"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        artifacts = self.list_by_project(project_id)
        
        for artifact in artifacts:
            src = Path(artifact.path)
            dst = output_dir / artifact.name
            if src.exists():
                shutil.copy2(src, dst)
        
        # 메타데이터 저장
        meta_file = output_dir / "artifacts.json"
        with open(meta_file, 'w', encoding='utf-8') as f:
            data = [a.model_dump(mode='json') for a in artifacts]
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        return output_dir


# =============================================================================
# 싱글톤 인스턴스
# =============================================================================

_artifact_manager: Optional[ArtifactManager] = None

def get_artifact_manager() -> ArtifactManager:
    """ArtifactManager 싱글톤 반환"""
    global _artifact_manager
    if _artifact_manager is None:
        _artifact_manager = ArtifactManager()
    return _artifact_manager
