"""
test_config.py - Config 모듈 테스트

이 파일의 책임:
- ProjectConfig 스키마 테스트
- ConfigLoader 기능 테스트
- 환경 변수 치환 테스트
- 유효성 검증 테스트
"""

import pytest
import tempfile
import os
from pathlib import Path

from prometheus.config.project_schema import (
    ProjectConfig,
    ProjectMetadata,
    AgentConfig,
    AgentType,
    ToolConfig,
    LLMProviderConfig,
    LLMProvider,
    MemoryConfig,
)
from prometheus.config.loader import (
    ConfigLoader,
    LoaderConfig,
    ConfigLoadError,
    ConfigValidationError,
)


class TestProjectMetadata:
    """프로젝트 메타데이터 테스트"""
    
    def test_valid_metadata(self) -> None:
        """유효한 메타데이터 생성"""
        metadata = ProjectMetadata(
            name="test_project",
            description="Test project",
            version="1.0.0",
        )
        assert metadata.name == "test_project"
        assert metadata.description == "Test project"
    
    def test_invalid_name_empty(self) -> None:
        """빈 이름 검증"""
        with pytest.raises(ValueError):
            ProjectMetadata(name="")
    
    def test_invalid_name_format(self) -> None:
        """잘못된 이름 형식 검증"""
        with pytest.raises(ValueError):
            ProjectMetadata(name="123_invalid")
    
    def test_valid_name_formats(self) -> None:
        """유효한 이름 형식들"""
        valid_names = ["project", "my_project", "Project1", "test-project"]
        for name in valid_names:
            metadata = ProjectMetadata(name=name)
            assert metadata.name == name


class TestLLMProviderConfig:
    """LLM 프로바이더 설정 테스트"""
    
    def test_default_values(self) -> None:
        """기본값 테스트"""
        config = LLMProviderConfig()
        assert config.provider == LLMProvider.OPENAI
        assert config.temperature == 0.7
    
    def test_temperature_validation(self) -> None:
        """temperature 유효성 검증"""
        # 유효한 값
        config = LLMProviderConfig(temperature=0.5)
        assert config.temperature == 0.5
        
        # 범위 초과
        with pytest.raises(ValueError):
            LLMProviderConfig(temperature=3.0)
    
    def test_different_providers(self) -> None:
        """다양한 프로바이더 설정"""
        for provider in LLMProvider:
            config = LLMProviderConfig(provider=provider)
            assert config.provider == provider


class TestAgentConfig:
    """Agent 설정 테스트"""
    
    def test_auto_name_generation(self) -> None:
        """자동 이름 생성"""
        config = AgentConfig(agent_type=AgentType.PLANNER)
        assert config.name == "PlannerAgent"
    
    def test_custom_name(self) -> None:
        """커스텀 이름 설정"""
        config = AgentConfig(agent_type=AgentType.EXECUTOR, name="MyExecutor")
        assert config.name == "MyExecutor"
    
    def test_with_tools(self) -> None:
        """Tool 설정"""
        config = AgentConfig(
            agent_type=AgentType.EXECUTOR,
            tools=["python_exec", "file_tool"],
        )
        assert len(config.tools) == 2


class TestProjectConfig:
    """프로젝트 설정 테스트"""
    
    def test_minimal_config(self) -> None:
        """최소 설정"""
        config = ProjectConfig(
            metadata=ProjectMetadata(name="minimal_project"),
        )
        assert config.metadata.name == "minimal_project"
        assert len(config.agents) == 0
    
    def test_full_config(self) -> None:
        """전체 설정"""
        config = ProjectConfig(
            metadata=ProjectMetadata(name="full_project"),
            default_llm=LLMProviderConfig(
                provider=LLMProvider.ANTHROPIC,
                model="claude-3-opus",
            ),
            agents=[
                AgentConfig(agent_type=AgentType.PLANNER),
                AgentConfig(agent_type=AgentType.EXECUTOR),
            ],
            tools=[
                ToolConfig(name="python_exec"),
            ],
        )
        assert len(config.agents) == 2
        assert len(config.tools) == 1
    
    def test_duplicate_agent_types(self) -> None:
        """중복 Agent 타입 검증"""
        with pytest.raises(ValueError):
            ProjectConfig(
                metadata=ProjectMetadata(name="test"),
                agents=[
                    AgentConfig(agent_type=AgentType.PLANNER),
                    AgentConfig(agent_type=AgentType.PLANNER),  # 중복
                ],
            )
    
    def test_get_agent_config(self) -> None:
        """Agent 설정 조회"""
        config = ProjectConfig(
            metadata=ProjectMetadata(name="test"),
            agents=[
                AgentConfig(agent_type=AgentType.PLANNER),
                AgentConfig(agent_type=AgentType.EXECUTOR),
            ],
        )
        
        planner = config.get_agent_config(AgentType.PLANNER)
        assert planner is not None
        assert planner.agent_type == AgentType.PLANNER
        
        writer = config.get_agent_config(AgentType.WRITER)
        assert writer is None
    
    def test_get_tool_config(self) -> None:
        """Tool 설정 조회"""
        config = ProjectConfig(
            metadata=ProjectMetadata(name="test"),
            tools=[
                ToolConfig(name="python_exec"),
                ToolConfig(name="file_tool", enabled=False),
            ],
        )
        
        python_tool = config.get_tool_config("python_exec")
        assert python_tool is not None
        assert python_tool.enabled is True
        
        unknown_tool = config.get_tool_config("unknown")
        assert unknown_tool is None
    
    def test_yaml_serialization(self) -> None:
        """YAML 직렬화/역직렬화"""
        original = ProjectConfig(
            metadata=ProjectMetadata(name="yaml_test"),
            agents=[AgentConfig(agent_type=AgentType.PLANNER)],
        )
        
        yaml_str = original.to_yaml()
        restored = ProjectConfig.from_yaml(yaml_str)
        
        assert restored.metadata.name == original.metadata.name
        assert len(restored.agents) == len(original.agents)


class TestConfigLoader:
    """ConfigLoader 테스트"""
    
    @pytest.fixture
    def temp_project_dir(self) -> Path:
        """임시 프로젝트 디렉토리 생성"""
        with tempfile.TemporaryDirectory() as tmpdir:
            projects_dir = Path(tmpdir) / "projects"
            projects_dir.mkdir()
            
            # 샘플 프로젝트 생성
            sample_project = projects_dir / "sample_project"
            sample_project.mkdir()
            
            config_content = """
metadata:
  name: sample_project
  description: Test project

default_llm:
  provider: openai
  model: gpt-4

agents:
  - agent_type: planner
    tools:
      - python_exec

tools:
  - name: python_exec
    enabled: true
"""
            (sample_project / "project.yaml").write_text(config_content)
            
            yield projects_dir
    
    def test_load_project(self, temp_project_dir: Path) -> None:
        """프로젝트 로드 테스트"""
        loader = ConfigLoader(
            config=LoaderConfig(projects_dir=str(temp_project_dir)),
            auto_load_env=False,
        )
        
        config = loader.load_project("sample_project")
        assert config.metadata.name == "sample_project"
    
    def test_list_projects(self, temp_project_dir: Path) -> None:
        """프로젝트 목록 조회"""
        loader = ConfigLoader(
            config=LoaderConfig(projects_dir=str(temp_project_dir)),
            auto_load_env=False,
        )
        
        projects = loader.list_projects()
        assert "sample_project" in projects
    
    def test_project_exists(self, temp_project_dir: Path) -> None:
        """프로젝트 존재 여부 확인"""
        loader = ConfigLoader(
            config=LoaderConfig(projects_dir=str(temp_project_dir)),
            auto_load_env=False,
        )
        
        assert loader.project_exists("sample_project") is True
        assert loader.project_exists("nonexistent") is False
    
    def test_load_nonexistent_project(self, temp_project_dir: Path) -> None:
        """존재하지 않는 프로젝트 로드"""
        loader = ConfigLoader(
            config=LoaderConfig(projects_dir=str(temp_project_dir)),
            auto_load_env=False,
        )
        
        with pytest.raises(ConfigLoadError):
            loader.load_project("nonexistent")
    
    def test_merge_configs(self) -> None:
        """설정 병합 테스트"""
        loader = ConfigLoader(auto_load_env=False)
        
        base = {
            "metadata": {"name": "base", "version": "1.0"},
            "settings": {"a": 1, "b": 2},
        }
        override = {
            "metadata": {"version": "2.0"},
            "settings": {"b": 3, "c": 4},
        }
        
        merged = loader.merge_configs(base, override)
        
        assert merged["metadata"]["name"] == "base"
        assert merged["metadata"]["version"] == "2.0"
        assert merged["settings"]["a"] == 1
        assert merged["settings"]["b"] == 3
        assert merged["settings"]["c"] == 4
    
    def test_env_var_substitution(self) -> None:
        """환경 변수 치환 테스트"""
        loader = ConfigLoader(auto_load_env=False)
        
        os.environ["TEST_VAR"] = "test_value"
        
        config = {
            "api_key": "${TEST_VAR}",
            "nested": {
                "value": "$TEST_VAR",
            },
        }
        
        result = loader._substitute_env_vars(config)
        
        assert result["api_key"] == "test_value"
        assert result["nested"]["value"] == "test_value"
        
        del os.environ["TEST_VAR"]
    
    def test_create_project(self, temp_project_dir: Path) -> None:
        """새 프로젝트 생성"""
        loader = ConfigLoader(
            config=LoaderConfig(projects_dir=str(temp_project_dir)),
            auto_load_env=False,
        )
        
        project_path = loader.create_project(
            "new_project",
            request="Test request",
        )
        
        assert project_path.exists()
        assert (project_path / "project.yaml").exists()
        assert (project_path / "request.txt").exists()
    
    def test_create_existing_project(self, temp_project_dir: Path) -> None:
        """이미 존재하는 프로젝트 생성 시도"""
        loader = ConfigLoader(
            config=LoaderConfig(projects_dir=str(temp_project_dir)),
            auto_load_env=False,
        )
        
        with pytest.raises(ConfigLoadError):
            loader.create_project("sample_project")


class TestValidation:
    """유효성 검증 테스트"""
    
    def test_validate_all_success(self) -> None:
        """전체 검증 성공"""
        config = ProjectConfig(
            metadata=ProjectMetadata(name="valid_project"),
            agents=[
                AgentConfig(
                    agent_type=AgentType.EXECUTOR,
                    tools=["python_exec"],
                ),
            ],
            tools=[
                ToolConfig(name="python_exec"),
            ],
        )
        
        assert config.validate_all() is True
    
    def test_validate_all_missing_tool(self) -> None:
        """참조된 Tool이 없는 경우"""
        config = ProjectConfig(
            metadata=ProjectMetadata(name="invalid_project"),
            agents=[
                AgentConfig(
                    agent_type=AgentType.EXECUTOR,
                    tools=["nonexistent_tool"],  # 존재하지 않는 Tool
                ),
            ],
            tools=[],
        )
        
        assert config.validate_all() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
