"""
NEXOUS Core - Preset Loader

presets/ 폴더에서 Preset YAML을 로드하고 관리한다.

LEVEL 2:
- llm.policy 형식 지원
- 기존 llm.provider/model 형식 호환
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Any, Optional

import yaml

from .exceptions import NEXOUSError

logger = logging.getLogger(__name__)


class PresetNotFoundError(NEXOUSError):
    """Preset을 찾을 수 없음"""
    def __init__(self, preset_id: str):
        self.preset_id = preset_id
        super().__init__(f"Preset not found: '{preset_id}'")


class PresetLoadError(NEXOUSError):
    """Preset 로드 오류"""
    pass


class PresetLoader:
    """
    Preset 로더
    
    presets/ 폴더에서 YAML 파일들을 로드하고 캐싱한다.
    
    LEVEL 2:
    - llm.policy 형식 지원 (primary/retry/fallback)
    - 기존 llm.provider/model 형식 호환
    """
    
    def __init__(self, preset_dir: str = None):
        if preset_dir:
            self.preset_dir = Path(preset_dir)
        else:
            self.preset_dir = Path(__file__).parent.parent / "presets"
        
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._loaded = False
    
    def load_all(self) -> Dict[str, Dict[str, Any]]:
        """모든 Preset 로드"""
        if not self.preset_dir.exists():
            logger.warning(f"[PresetLoader] Preset directory not found: {self.preset_dir}")
            return {}
        
        self._cache.clear()
        
        for yaml_file in self.preset_dir.glob("*.yaml"):
            try:
                preset = self._load_file(yaml_file)
                preset_id = preset.get("id")
                
                if not preset_id:
                    logger.warning(f"[PresetLoader] Missing 'id' in {yaml_file.name}, using filename")
                    preset_id = yaml_file.stem
                    preset["id"] = preset_id
                
                self._cache[preset_id] = preset
                logger.debug(f"[PresetLoader] Loaded preset: {preset_id}")
                
            except Exception as e:
                logger.error(f"[PresetLoader] Failed to load {yaml_file.name}: {e}")
                raise PresetLoadError(f"Failed to load preset {yaml_file.name}: {e}")
        
        self._loaded = True
        logger.info(f"[PresetLoader] Loaded {len(self._cache)} presets: {list(self._cache.keys())}")
        
        return self._cache
    
    def get(self, preset_id: str) -> Dict[str, Any]:
        """Preset 조회"""
        if not self._loaded:
            self.load_all()
        
        preset = self._cache.get(preset_id)
        
        if preset is None:
            raise PresetNotFoundError(preset_id)
        
        return preset
    
    def list_presets(self) -> list:
        """로드된 Preset ID 목록"""
        if not self._loaded:
            self.load_all()
        return list(self._cache.keys())
    
    def _load_file(self, path: Path) -> Dict[str, Any]:
        """YAML 파일 로드"""
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data:
            raise PresetLoadError(f"Empty preset file: {path}")
        
        self._validate_preset(data, path.name)
        
        return data
    
    def _validate_preset(self, preset: Dict, filename: str) -> None:
        """
        Preset 필수 필드 검증
        
        LEVEL 2:
        - llm.policy.primary 또는 llm.provider 중 하나 필요
        """
        required = ["role", "llm", "system_prompt"]
        
        for field in required:
            if field not in preset:
                raise PresetLoadError(f"Missing required field '{field}' in {filename}")
        
        # LLM 설정 검증 (LEVEL 2: policy 또는 기존 형식)
        llm = preset.get("llm", {})
        
        # 새 형식: llm.policy.primary
        if "policy" in llm:
            policy = llm["policy"]
            if "primary" not in policy:
                raise PresetLoadError(f"Missing 'llm.policy.primary' in {filename}")
        # 기존 형식: llm.provider + llm.model
        elif "provider" not in llm and "model" not in llm:
            raise PresetLoadError(
                f"Missing LLM config in {filename}. "
                f"Use 'llm.policy.primary' or 'llm.provider/model'"
            )
