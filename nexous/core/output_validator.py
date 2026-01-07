"""
NEXOUS Core - Output Validator

Agent 출력 스키마 검증
"""

from __future__ import annotations

import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class OutputValidationError(Exception):
    """출력 검증 오류"""
    pass


class OutputValidator:
    """
    Agent 출력 검증기
    
    Preset의 output_policy에 따라 출력을 검증
    """
    
    def __init__(self, output_policy: Dict[str, Any] = None):
        """
        Args:
            output_policy: Preset에서 정의한 출력 정책
                {
                    "format": "json",
                    "strict": true,
                    "required_fields": ["summary", "steps"],
                    "schema": {...}  # JSON Schema (선택)
                }
        """
        self.policy = output_policy or {}
        self.format = self.policy.get("format", "text")
        self.strict = self.policy.get("strict", False)
        self.required_fields = self.policy.get("required_fields", [])
        self.schema = self.policy.get("schema")
    
    def validate(self, output: str) -> Dict[str, Any]:
        """
        출력 검증
        
        Args:
            output: Agent 출력 문자열
            
        Returns:
            {"valid": bool, "parsed": Any, "errors": List[str]}
        """
        errors = []
        parsed = None
        
        # Format 검증
        if self.format == "json":
            try:
                # JSON 블록 추출 시도
                parsed = self._extract_json(output)
                
                # Required fields 검증
                if self.required_fields and isinstance(parsed, dict):
                    missing = [f for f in self.required_fields if f not in parsed]
                    if missing:
                        errors.append(f"Missing required fields: {missing}")
                
                # JSON Schema 검증 (선택)
                if self.schema and parsed:
                    schema_errors = self._validate_schema(parsed)
                    errors.extend(schema_errors)
                    
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON: {e}")
                parsed = None
                
        elif self.format == "markdown":
            parsed = output
            # Markdown 구조 검증 (선택)
            if self.required_fields:
                for field in self.required_fields:
                    if f"# {field}" not in output and f"## {field}" not in output:
                        # 헤더가 없어도 내용이 있으면 OK
                        pass
                        
        else:
            parsed = output
        
        # Strict 모드에서 오류 발생
        if self.strict and errors:
            raise OutputValidationError("; ".join(errors))
        
        return {
            "valid": len(errors) == 0,
            "parsed": parsed,
            "errors": errors
        }
    
    def _extract_json(self, text: str) -> Any:
        """JSON 추출 (코드 블록 지원)"""
        # 먼저 전체 텍스트 시도
        try:
            return json.loads(text)
        except:
            pass
        
        # ```json 블록 추출
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                json_str = text[start:end].strip()
                return json.loads(json_str)
        
        # ``` 블록 추출
        if "```" in text:
            start = text.find("```") + 3
            # 언어 태그 스킵
            if text[start:start+10].strip().isalpha():
                start = text.find("\n", start) + 1
            end = text.find("```", start)
            if end > start:
                json_str = text[start:end].strip()
                return json.loads(json_str)
        
        # { } 추출
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = text[start:end]
            return json.loads(json_str)
        
        raise json.JSONDecodeError("No JSON found", text, 0)
    
    def _validate_schema(self, data: Any) -> List[str]:
        """JSON Schema 검증"""
        errors = []
        
        try:
            import jsonschema
            jsonschema.validate(instance=data, schema=self.schema)
        except ImportError:
            logger.warning("[OutputValidator] jsonschema not installed, skipping schema validation")
        except jsonschema.ValidationError as e:
            errors.append(f"Schema validation failed: {e.message}")
        
        return errors
