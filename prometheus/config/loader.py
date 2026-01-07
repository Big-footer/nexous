"""
ConfigLoader - 설정 로더

이 파일의 책임:
- 프로젝트 설정 파일 로드
- 환경 변수 처리
- 설정 병합 (기본값 + 프로젝트 설정)
- 설정 검증
- 다양한 설정 소스 지원 (YAML, JSON, ENV)
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
from pydantic import BaseModel
import os
import json
import yaml
from dotenv import load_dotenv

from prometheus.config.project_schema import ProjectConfig, LLMProviderConfig, MemoryConfig


class LoaderConfig(BaseModel):
    """로더 설정"""
    
    projects_dir: str = "./projects"
    env_file: str = ".env"
    default_config_file: str = "default_config.yaml"


class ConfigLoadError(Exception):
    """설정 로드 오류"""
    pass


class ConfigValidationError(Exception):
    """설정 검증 오류"""
    pass


class ConfigLoader:
    """
    설정 로더
    
    프로젝트 설정 파일을 로드하고 환경 변수와 병합합니다.
    다양한 설정 소스를 지원합니다.
    """
    
    def __init__(
        self,
        config: Optional[LoaderConfig] = None,
        auto_load_env: bool = True,
    ) -> None:
        """
        ConfigLoader 초기화
        
        Args:
            config: 로더 설정
            auto_load_env: 자동으로 .env 파일 로드 여부
        """
        self.config = config or LoaderConfig()
        self._env_vars: Dict[str, str] = {}
        self._default_config: Optional[ProjectConfig] = None
        self._loaded_projects: Dict[str, ProjectConfig] = {}
        
        if auto_load_env:
            self.load_env()
    
    def load_project(
        self,
        project_path: str,
        use_cache: bool = True,
    ) -> ProjectConfig:
        """
        프로젝트 설정 로드
        
        Args:
            project_path: 프로젝트 디렉토리 경로 또는 프로젝트 이름
            use_cache: 캐시 사용 여부
            
        Returns:
            프로젝트 설정
            
        Raises:
            ConfigLoadError: 로드 실패 시
        """
        # 프로젝트 경로 결정
        path = Path(project_path)
        if not path.is_absolute():
            # 프로젝트 이름인 경우 projects_dir에서 찾기
            if not path.exists():
                path = Path(self.config.projects_dir) / project_path
        
        # 캐시 확인
        cache_key = str(path.resolve())
        if use_cache and cache_key in self._loaded_projects:
            return self._loaded_projects[cache_key]
        
        # project.yaml 파일 찾기
        config_file = path / "project.yaml"
        if not config_file.exists():
            config_file = path / "project.yml"
        if not config_file.exists():
            raise ConfigLoadError(f"Project config file not found in {path}")
        
        try:
            # YAML 로드
            yaml_data = self.load_yaml(str(config_file))
            
            # 환경 변수 치환
            yaml_data = self._substitute_env_vars(yaml_data)
            
            # ProjectConfig 생성
            project_config = ProjectConfig.from_dict(yaml_data)
            
            # 검증
            if not project_config.validate_all():
                raise ConfigValidationError(f"Project config validation failed: {path}")
            
            # 캐시 저장
            self._loaded_projects[cache_key] = project_config
            
            return project_config
            
        except yaml.YAMLError as e:
            raise ConfigLoadError(f"Failed to parse YAML: {e}")
        except Exception as e:
            raise ConfigLoadError(f"Failed to load project config: {e}")
    
    def load_yaml(
        self,
        file_path: str,
    ) -> Dict[str, Any]:
        """
        YAML 파일 로드
        
        Args:
            file_path: 파일 경로
            
        Returns:
            파싱된 딕셔너리
            
        Raises:
            ConfigLoadError: 파일을 찾을 수 없거나 파싱 실패 시
        """
        path = Path(file_path)
        if not path.exists():
            raise ConfigLoadError(f"YAML file not found: {file_path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data if data else {}
        except yaml.YAMLError as e:
            raise ConfigLoadError(f"Failed to parse YAML file {file_path}: {e}")
        except IOError as e:
            raise ConfigLoadError(f"Failed to read file {file_path}: {e}")
    
    def load_json(
        self,
        file_path: str,
    ) -> Dict[str, Any]:
        """
        JSON 파일 로드
        
        Args:
            file_path: 파일 경로
            
        Returns:
            파싱된 딕셔너리
            
        Raises:
            ConfigLoadError: 파일을 찾을 수 없거나 파싱 실패 시
        """
        path = Path(file_path)
        if not path.exists():
            raise ConfigLoadError(f"JSON file not found: {file_path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigLoadError(f"Failed to parse JSON file {file_path}: {e}")
        except IOError as e:
            raise ConfigLoadError(f"Failed to read file {file_path}: {e}")
    
    def load_env(
        self,
        env_file: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        환경 변수 로드
        
        Args:
            env_file: .env 파일 경로 (None이면 기본 경로 사용)
            
        Returns:
            로드된 환경 변수 딕셔너리
        """
        env_path = env_file or self.config.env_file
        
        # .env 파일 로드 (존재하는 경우)
        if Path(env_path).exists():
            load_dotenv(env_path)
        
        # 현재 환경 변수 캐시
        self._env_vars = dict(os.environ)
        
        return self._env_vars
    
    def get_env(
        self,
        key: str,
        default: Optional[str] = None,
    ) -> Optional[str]:
        """
        환경 변수 조회
        
        Args:
            key: 변수 키
            default: 기본값
            
        Returns:
            변수 값 또는 기본값
        """
        return os.environ.get(key, default)
    
    def get_api_key(
        self,
        provider: str,
    ) -> Optional[str]:
        """
        LLM 프로바이더 API 키 조회
        
        Args:
            provider: 프로바이더 이름 (openai, anthropic, gemini)
            
        Returns:
            API 키 또는 None
        """
        key_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GOOGLE_API_KEY",
        }
        env_key = key_map.get(provider.lower())
        if env_key:
            return self.get_env(env_key)
        return None
    
    def merge_configs(
        self,
        base: Dict[str, Any],
        override: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        설정 병합 (깊은 병합)
        
        Args:
            base: 기본 설정
            override: 오버라이드 설정
            
        Returns:
            병합된 설정
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # 딕셔너리는 재귀적으로 병합
                result[key] = self.merge_configs(result[key], value)
            else:
                # 그 외는 오버라이드
                result[key] = value
        
        return result
    
    def validate_config(
        self,
        config: Dict[str, Any],
    ) -> bool:
        """
        설정 유효성 검증
        
        Args:
            config: 검증할 설정
            
        Returns:
            유효성 여부
        """
        try:
            ProjectConfig.from_dict(config)
            return True
        except Exception:
            return False
    
    def list_projects(self) -> List[str]:
        """
        프로젝트 목록 조회
        
        Returns:
            프로젝트 이름 목록
        """
        projects_path = Path(self.config.projects_dir)
        if not projects_path.exists():
            return []
        
        projects = []
        for item in projects_path.iterdir():
            if item.is_dir():
                # project.yaml 또는 project.yml 존재 확인
                if (item / "project.yaml").exists() or (item / "project.yml").exists():
                    projects.append(item.name)
        
        return sorted(projects)
    
    def project_exists(
        self,
        project_name: str,
    ) -> bool:
        """
        프로젝트 존재 여부 확인
        
        Args:
            project_name: 프로젝트 이름
            
        Returns:
            존재 여부
        """
        return project_name in self.list_projects()
    
    def get_project_path(
        self,
        project_name: str,
    ) -> Path:
        """
        프로젝트 경로 조회
        
        Args:
            project_name: 프로젝트 이름
            
        Returns:
            프로젝트 경로
        """
        return Path(self.config.projects_dir) / project_name
    
    def create_project(
        self,
        project_name: str,
        config: Optional[ProjectConfig] = None,
        request: Optional[str] = None,
    ) -> Path:
        """
        새 프로젝트 생성
        
        Args:
            project_name: 프로젝트 이름
            config: 프로젝트 설정 (None이면 기본 설정 사용)
            request: request.txt 내용
            
        Returns:
            생성된 프로젝트 경로
            
        Raises:
            ConfigLoadError: 이미 존재하는 경우
        """
        project_path = self.get_project_path(project_name)
        
        if project_path.exists():
            raise ConfigLoadError(f"Project '{project_name}' already exists")
        
        # 디렉토리 생성
        project_path.mkdir(parents=True, exist_ok=True)
        
        # 기본 설정 생성
        if config is None:
            config = self._create_default_project_config(project_name)
        
        # project.yaml 저장
        config_file = project_path / "project.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config.to_yaml())
        
        # request.txt 저장
        if request:
            request_file = project_path / "request.txt"
            with open(request_file, 'w', encoding='utf-8') as f:
                f.write(request)
        
        return project_path
    
    def _substitute_env_vars(
        self,
        config: Any,
    ) -> Any:
        """
        설정 내 환경 변수 치환
        ${VAR_NAME} 또는 $VAR_NAME 형식 지원
        
        Args:
            config: 설정 딕셔너리 또는 값
            
        Returns:
            치환된 설정
        """
        import re
        
        if isinstance(config, dict):
            return {k: self._substitute_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        elif isinstance(config, str):
            # ${VAR_NAME} 패턴
            pattern = r'\$\{([^}]+)\}'
            
            def replace(match: re.Match) -> str:
                var_name = match.group(1)
                return os.environ.get(var_name, match.group(0))
            
            result = re.sub(pattern, replace, config)
            
            # $VAR_NAME 패턴 (단어 경계)
            pattern2 = r'\$([A-Z_][A-Z0-9_]*)'
            result = re.sub(pattern2, replace, result)
            
            return result
        else:
            return config
    
    def _create_default_project_config(
        self,
        project_name: str,
    ) -> ProjectConfig:
        """
        기본 프로젝트 설정 생성
        
        Args:
            project_name: 프로젝트 이름
            
        Returns:
            기본 ProjectConfig
        """
        from prometheus.config.project_schema import (
            ProjectMetadata,
            AgentConfig,
            AgentType,
            ToolConfig,
        )
        from datetime import datetime
        
        return ProjectConfig(
            metadata=ProjectMetadata(
                name=project_name,
                description=f"Project: {project_name}",
                version="1.0.0",
                created_at=datetime.now().isoformat(),
            ),
            default_llm=LLMProviderConfig(),
            agents=[
                AgentConfig(agent_type=AgentType.PLANNER),
                AgentConfig(agent_type=AgentType.EXECUTOR),
                AgentConfig(agent_type=AgentType.WRITER),
                AgentConfig(agent_type=AgentType.QA),
            ],
            tools=[
                ToolConfig(name="python_exec", enabled=True),
            ],
            memory=MemoryConfig(),
            settings={
                "enable_tracing": True,
                "log_level": "INFO",
            },
        )
    
    def _load_default_config(self) -> Optional[ProjectConfig]:
        """
        기본 설정 로드
        
        Returns:
            기본 프로젝트 설정 또는 None
        """
        default_path = Path(self.config.default_config_file)
        if default_path.exists():
            try:
                yaml_data = self.load_yaml(str(default_path))
                return ProjectConfig.from_dict(yaml_data)
            except Exception:
                return None
        return None
    
    def clear_cache(self) -> None:
        """캐시 초기화"""
        self._loaded_projects.clear()
    
    def reload_project(
        self,
        project_name: str,
    ) -> ProjectConfig:
        """
        프로젝트 설정 다시 로드
        
        Args:
            project_name: 프로젝트 이름
            
        Returns:
            다시 로드된 설정
        """
        return self.load_project(project_name, use_cache=False)


# 전역 ConfigLoader 인스턴스
_default_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """
    기본 ConfigLoader 인스턴스 획득
    
    Returns:
        ConfigLoader 인스턴스
    """
    global _default_loader
    if _default_loader is None:
        _default_loader = ConfigLoader()
    return _default_loader


def load_project_config(project_name: str) -> ProjectConfig:
    """
    프로젝트 설정 로드 (편의 함수)
    
    Args:
        project_name: 프로젝트 이름
        
    Returns:
        프로젝트 설정
    """
    return get_config_loader().load_project(project_name)
