"""
NEXOUS Test - LEVEL 2 출력 JSON Schema 검증

Agent 출력이 정의된 JSON Schema를 만족하는지 검증
"""

import os
import json
import pytest

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


class TestOutputSchemaValidation:
    """출력 JSON Schema 검증"""
    
    def test_output_schema_exists(self, project_root):
        """output_schema.json 파일 존재"""
        schema_path = project_root / "schemas" / "output_schema.json"
        assert schema_path.exists()
    
    def test_output_schema_valid_json(self, project_root):
        """output_schema.json이 유효한 JSON"""
        schema_path = project_root / "schemas" / "output_schema.json"
        with open(schema_path) as f:
            schema = json.load(f)
        
        assert "$schema" in schema or "type" in schema
    
    def test_executor_output_schema(self, executor_output_schema):
        """Executor 출력 스키마 정의"""
        assert executor_output_schema["type"] == "object"
        assert "execution_status" in executor_output_schema["required"]
    
    @pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
    def test_valid_executor_output(self, executor_output_schema):
        """유효한 Executor 출력"""
        valid_output = {
            "execution_status": "success",
            "output_files": ["result.csv"],
            "logs": ["Step 1 completed", "Step 2 completed"],
        }
        
        # 검증 통과
        jsonschema.validate(instance=valid_output, schema=executor_output_schema)
    
    @pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
    def test_invalid_executor_output_missing_required(self, executor_output_schema):
        """필수 필드 누락 시 검증 실패"""
        invalid_output = {
            "output_files": ["result.csv"],
            # execution_status 누락
        }
        
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid_output, schema=executor_output_schema)
    
    @pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
    def test_invalid_executor_status_enum(self, executor_output_schema):
        """잘못된 status enum 값"""
        invalid_output = {
            "execution_status": "invalid_status",  # success/partial/failed만 허용
        }
        
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid_output, schema=executor_output_schema)


class TestAgentOutputValidation:
    """Agent 출력 검증"""
    
    def test_agent_validates_json_output(self):
        """Agent가 JSON 출력 검증"""
        from nexous.core import GenericAgent
        
        agent = GenericAgent(
            agent_id="test_agent",
            role="tester",
            purpose="테스트",
            llm_config={"policy": {"primary": "openai/gpt-4o", "retry": 1}},
            tools=[],
            output_policy={
                "format": "json",
                "required_fields": ["result"],
            },
        )
        
        # output_policy가 설정되어 있는지 확인
        assert agent.output_policy is not None
        assert agent.output_policy["format"] == "json"
    
    def test_agent_missing_required_fields_warning(self, mock_openai_client, caplog):
        """필수 필드 누락 시 경고"""
        from nexous.core import GenericAgent
        from nexous.llm import LLMRegistry, LLMResponse
        from unittest.mock import patch
        
        # JSON이 아닌 응답 (required_fields 검증 실패)
        mock_openai_client.generate.return_value = LLMResponse(
            content="This is not JSON",  # JSON이 아님
            provider="openai",
            model="gpt-4o",
            tokens_input=10,
            tokens_output=20,
            latency_ms=100,
        )
        
        with patch.object(LLMRegistry, 'get', return_value=mock_openai_client):
            agent = GenericAgent(
                agent_id="test_agent",
                role="tester",
                purpose="테스트",
                llm_config={"policy": {"primary": "openai/gpt-4o", "retry": 1}},
                tools=[],
                output_policy={
                    "format": "json",
                    "required_fields": ["result"],
                },
            )
            
            result = agent.execute({"inputs": {"task": "Test"}})
            
            # 실행은 성공하지만 validated_output은 None
            assert result["status"] == "success"
            assert result["validated_output"] is None


class TestOutputSchemaTypes:
    """각 Role별 출력 스키마"""
    
    @pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
    def test_planner_output_schema(self, output_schema):
        """Planner 출력 스키마"""
        planner_output = {
            "plan": "데이터 분석 계획",
            "steps": [
                {"step_id": "1", "description": "데이터 로드"},
                {"step_id": "2", "description": "전처리"},
            ],
        }
        
        planner_schema = output_schema.get("definitions", {}).get("planner_output", {
            "type": "object",
            "required": ["plan", "steps"],
        })
        
        if planner_schema:
            jsonschema.validate(instance=planner_output, schema=planner_schema)
    
    @pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
    def test_analyst_output_schema(self, output_schema):
        """Analyst 출력 스키마"""
        analyst_output = {
            "analysis": "분석 결과 요약",
            "findings": ["발견 1", "발견 2"],
            "recommendations": ["권고 1"],
        }
        
        analyst_schema = output_schema.get("definitions", {}).get("analyst_output", {
            "type": "object",
            "required": ["analysis"],
        })
        
        if analyst_schema:
            jsonschema.validate(instance=analyst_output, schema=analyst_schema)
    
    @pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
    def test_writer_output_schema(self, output_schema):
        """Writer 출력 스키마"""
        writer_output = {
            "content": "# 보고서\n\n내용...",
            "format": "markdown",
        }
        
        writer_schema = output_schema.get("definitions", {}).get("writer_output", {
            "type": "object",
            "required": ["content"],
        })
        
        if writer_schema:
            jsonschema.validate(instance=writer_output, schema=writer_schema)


class TestJSONExtraction:
    """JSON 추출 테스트"""
    
    def test_extract_json_from_markdown_block(self):
        """마크다운 코드 블록에서 JSON 추출"""
        from nexous.core import GenericAgent
        
        content = '''
        Here is the result:
        
        ```json
        {"result": "success", "value": 42}
        ```
        
        That's all.
        '''
        
        agent = GenericAgent(
            agent_id="test",
            role="tester",
            purpose="테스트",
            llm_config={"policy": {"primary": "openai/gpt-4o"}},
            tools=[],
            output_policy={"format": "json"},
        )
        
        validated = agent._validate_output(content)
        
        assert validated is not None
        assert validated["result"] == "success"
        assert validated["value"] == 42
    
    def test_extract_raw_json(self):
        """순수 JSON 추출"""
        from nexous.core import GenericAgent
        
        content = '{"status": "ok", "count": 10}'
        
        agent = GenericAgent(
            agent_id="test",
            role="tester",
            purpose="테스트",
            llm_config={"policy": {"primary": "openai/gpt-4o"}},
            tools=[],
            output_policy={"format": "json"},
        )
        
        validated = agent._validate_output(content)
        
        assert validated is not None
        assert validated["status"] == "ok"
        assert validated["count"] == 10
    
    def test_invalid_json_returns_none(self):
        """잘못된 JSON은 None 반환"""
        from nexous.core import GenericAgent
        
        content = "This is not JSON at all"
        
        agent = GenericAgent(
            agent_id="test",
            role="tester",
            purpose="테스트",
            llm_config={"policy": {"primary": "openai/gpt-4o"}},
            tools=[],
            output_policy={"format": "json"},
        )
        
        validated = agent._validate_output(content)
        
        assert validated is None
