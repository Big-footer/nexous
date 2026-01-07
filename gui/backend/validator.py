"""
NEXOUS Project YAML Validator

JSON Schema + 로직 레벨 검증을 결합한 YAML 검증 모듈

검증 순서:
1. YAML 파싱
2. JSON Schema 검증 (구조, 타입, 패턴)
3. 로직 레벨 검증 (중복, 참조, 의존성)
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import yaml

try:
    from jsonschema import Draft7Validator, ValidationError as JsonSchemaError
    from jsonschema import FormatChecker
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    print("[WARNING] jsonschema not installed. Run: pip install jsonschema")


class ErrorSeverity(str, Enum):
    """에러 심각도"""
    ERROR = "error"      # 실행 불가
    WARNING = "warning"  # 실행 가능하나 권장하지 않음
    INFO = "info"        # 참고 사항


@dataclass
class ValidationIssue:
    """검증 이슈"""
    severity: ErrorSeverity
    field: str
    message: str
    path: Optional[str] = None
    line: Optional[int] = None


@dataclass
class ValidationResult:
    """검증 결과"""
    valid: bool
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    infos: List[ValidationIssue] = field(default_factory=list)
    
    # 파싱된 데이터
    agents: List[str] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    
    def add_error(self, field: str, message: str, path: str = None):
        self.errors.append(ValidationIssue(
            severity=ErrorSeverity.ERROR,
            field=field,
            message=message,
            path=path
        ))
        self.valid = False
    
    def add_warning(self, field: str, message: str, path: str = None):
        self.warnings.append(ValidationIssue(
            severity=ErrorSeverity.WARNING,
            field=field,
            message=message,
            path=path
        ))
    
    def add_info(self, field: str, message: str, path: str = None):
        self.infos.append(ValidationIssue(
            severity=ErrorSeverity.INFO,
            field=field,
            message=message,
            path=path
        ))
    
    def to_dict(self) -> Dict[str, Any]:
        """API 응답용 딕셔너리 변환"""
        return {
            "valid": self.valid,
            "errors": [
                {"field": e.field, "message": e.message, "path": e.path}
                for e in self.errors
            ],
            "warnings": [e.message for e in self.warnings],
            "agents": self.agents,
            "artifacts": self.artifacts,
        }


class ProjectYAMLValidator:
    """
    NEXOUS Project YAML 검증기
    
    사용법:
        validator = ProjectYAMLValidator()
        result = validator.validate(yaml_content)
        
        if result.valid:
            print("검증 성공!")
        else:
            for err in result.errors:
                print(f"[ERROR] {err.field}: {err.message}")
    """
    
    def __init__(self, schema_path: Optional[Path] = None):
        """
        Args:
            schema_path: JSON Schema 파일 경로 (기본: schemas/project_schema.json)
        """
        if schema_path is None:
            schema_path = Path(__file__).parent / "schemas" / "project_schema.json"
        
        self.schema_path = schema_path
        self.schema = self._load_schema()
        self._json_validator = None
        
        if HAS_JSONSCHEMA and self.schema:
            self._json_validator = Draft7Validator(
                self.schema,
                format_checker=FormatChecker()
            )
    
    def _load_schema(self) -> Optional[Dict]:
        """JSON Schema 로드"""
        try:
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"[WARNING] Schema file not found: {self.schema_path}")
            return None
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in schema: {e}")
            return None
    
    def validate(self, yaml_content: str) -> ValidationResult:
        """
        YAML 내용 검증 (전체 파이프라인)
        
        Args:
            yaml_content: YAML 문자열
            
        Returns:
            ValidationResult 객체
        """
        result = ValidationResult(valid=True)
        
        # 1. YAML 파싱
        data = self._parse_yaml(yaml_content, result)
        if data is None:
            return result
        
        # 2. JSON Schema 검증
        self._validate_schema(data, result)
        
        # 3. 로직 레벨 검증
        self._validate_logic(data, result)
        
        # 4. 메타데이터 추출
        self._extract_metadata(data, result)
        
        return result
    
    def _parse_yaml(self, content: str, result: ValidationResult) -> Optional[Dict]:
        """YAML 파싱"""
        try:
            data = yaml.safe_load(content)
            if not data:
                result.add_error("yaml", "빈 YAML 파일입니다")
                return None
            if not isinstance(data, dict):
                result.add_error("yaml", "YAML 최상위는 객체(object)여야 합니다")
                return None
            return data
        except yaml.YAMLError as e:
            result.add_error("yaml", f"YAML 파싱 오류: {e}")
            return None
    
    def _validate_schema(self, data: Dict, result: ValidationResult):
        """JSON Schema 검증"""
        if not self._json_validator:
            result.add_warning("schema", "JSON Schema 검증기가 비활성화되어 있습니다")
            return
        
        errors = list(self._json_validator.iter_errors(data))
        
        for error in errors:
            # 경로 추출
            path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
            
            # 사람이 읽기 쉬운 메시지 생성
            message = self._humanize_schema_error(error)
            
            result.add_error(path, message)
    
    def _humanize_schema_error(self, error: Any) -> str:
        """JSON Schema 에러를 사람이 읽기 쉬운 메시지로 변환"""
        if error.validator == "required":
            missing = error.validator_value
            return f"필수 필드가 없습니다: {missing}"
        elif error.validator == "type":
            expected = error.validator_value
            return f"타입이 잘못되었습니다. '{expected}' 타입이어야 합니다"
        elif error.validator == "pattern":
            return f"형식이 잘못되었습니다. 패턴: {error.validator_value}"
        elif error.validator == "enum":
            allowed = error.validator_value
            return f"허용되지 않는 값입니다. 허용값: {allowed}"
        elif error.validator == "minItems":
            return f"최소 {error.validator_value}개 이상의 항목이 필요합니다"
        elif error.validator == "minLength":
            return f"최소 {error.validator_value}자 이상이어야 합니다"
        elif error.validator == "minimum":
            return f"최소값은 {error.validator_value} 이상이어야 합니다"
        elif error.validator == "additionalProperties":
            return f"허용되지 않는 속성이 포함되어 있습니다"
        else:
            return error.message
    
    def _validate_logic(self, data: Dict, result: ValidationResult):
        """로직 레벨 검증 (중복, 참조, 의존성)"""
        
        # Agent ID 수집
        agents = data.get("agents", [])
        agent_ids = set()
        
        # 1. Agent ID 중복 검사
        for i, agent in enumerate(agents):
            agent_id = agent.get("id")
            if not agent_id:
                continue
            
            if agent_id in agent_ids:
                result.add_error(
                    f"agents[{i}].id",
                    f"Agent ID가 중복되었습니다: '{agent_id}'"
                )
            agent_ids.add(agent_id)
        
        # 2. Dependencies 참조 검증
        for i, agent in enumerate(agents):
            agent_id = agent.get("id", f"agents[{i}]")
            deps = agent.get("dependencies", [])
            
            for dep in deps:
                if dep not in agent_ids:
                    result.add_error(
                        f"agents[{i}].dependencies",
                        f"존재하지 않는 Agent를 참조합니다: '{dep}' (agent: {agent_id})"
                    )
                # 자기 참조 검사
                if dep == agent_id:
                    result.add_error(
                        f"agents[{i}].dependencies",
                        f"Agent가 자기 자신을 참조할 수 없습니다: '{agent_id}'"
                    )
        
        # 3. previous_results 참조 검증
        for i, agent in enumerate(agents):
            agent_id = agent.get("id", f"agents[{i}]")
            prev_results = agent.get("input", {}).get("previous_results", [])
            
            for prev in prev_results:
                if prev not in agent_ids:
                    result.add_error(
                        f"agents[{i}].input.previous_results",
                        f"존재하지 않는 Agent를 참조합니다: '{prev}'"
                    )
        
        # 4. Artifacts source 참조 검증
        artifacts = data.get("artifacts", [])
        for i, artifact in enumerate(artifacts):
            source = artifact.get("source")
            if source and source not in agent_ids:
                result.add_error(
                    f"artifacts[{i}].source",
                    f"존재하지 않는 Agent를 source로 참조합니다: '{source}'"
                )
        
        # 5. 순환 의존성 검사
        self._check_circular_dependencies(agents, agent_ids, result)
        
        # 6. 경고: 의존성 없는 중간 Agent
        self._check_orphan_agents(agents, agent_ids, result)
    
    def _check_circular_dependencies(
        self, 
        agents: List[Dict], 
        agent_ids: set, 
        result: ValidationResult
    ):
        """순환 의존성 검사 (DFS)"""
        # 인접 리스트 구성
        graph = {agent.get("id"): agent.get("dependencies", []) for agent in agents}
        
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str, path: List[str]) -> Optional[List[str]]:
            if node not in graph:
                return None
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    cycle = has_cycle(neighbor, path + [neighbor])
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # 순환 발견
                    return path + [neighbor]
            
            rec_stack.remove(node)
            return None
        
        for agent_id in agent_ids:
            if agent_id not in visited:
                cycle = has_cycle(agent_id, [agent_id])
                if cycle:
                    result.add_error(
                        "agents.dependencies",
                        f"순환 의존성이 발견되었습니다: {' → '.join(cycle)}"
                    )
                    break  # 첫 번째 순환만 보고
    
    def _check_orphan_agents(
        self, 
        agents: List[Dict], 
        agent_ids: set, 
        result: ValidationResult
    ):
        """고아 Agent 검사 (의존성 체인에서 제외된 Agent)"""
        if len(agents) <= 1:
            return
        
        # 참조된 Agent 수집
        referenced = set()
        for agent in agents:
            deps = agent.get("dependencies", [])
            prev_results = agent.get("input", {}).get("previous_results", [])
            referenced.update(deps)
            referenced.update(prev_results)
        
        # 첫 번째 Agent는 의존성이 없어도 됨
        first_agent = agents[0].get("id")
        
        # 의존성도 없고 참조도 안 된 Agent
        for agent in agents[1:]:
            agent_id = agent.get("id")
            deps = agent.get("dependencies", [])
            
            if not deps and agent_id not in referenced:
                result.add_warning(
                    f"agents.{agent_id}",
                    f"Agent '{agent_id}'는 의존성이 없고 다른 Agent에게 참조되지 않습니다"
                )
    
    def _extract_metadata(self, data: Dict, result: ValidationResult):
        """메타데이터 추출 (agents, artifacts 목록)"""
        agents = data.get("agents", [])
        result.agents = [a.get("id") for a in agents if a.get("id")]
        
        artifacts = data.get("artifacts", [])
        result.artifacts = [a.get("id") for a in artifacts if a.get("id")]


# ============================================
# 편의 함수
# ============================================

_validator = None

def get_validator() -> ProjectYAMLValidator:
    """싱글톤 검증기 반환"""
    global _validator
    if _validator is None:
        _validator = ProjectYAMLValidator()
    return _validator


def validate_project_yaml(yaml_content: str) -> ValidationResult:
    """
    Project YAML 검증 (간편 함수)
    
    Args:
        yaml_content: YAML 문자열
        
    Returns:
        ValidationResult 객체
    """
    return get_validator().validate(yaml_content)


# ============================================
# CLI 테스트
# ============================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python validator.py <yaml_file>")
        sys.exit(1)
    
    yaml_file = Path(sys.argv[1])
    if not yaml_file.exists():
        print(f"File not found: {yaml_file}")
        sys.exit(1)
    
    with open(yaml_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    result = validate_project_yaml(content)
    
    print("\n" + "=" * 60)
    print(f"  NEXOUS YAML Validation: {'✓ PASS' if result.valid else '✗ FAIL'}")
    print("=" * 60)
    
    if result.errors:
        print("\n[ERRORS]")
        for err in result.errors:
            print(f"  ✗ {err.field}: {err.message}")
    
    if result.warnings:
        print("\n[WARNINGS]")
        for warn in result.warnings:
            print(f"  ⚠ {warn.field}: {warn.message}")
    
    print(f"\nAgents: {result.agents}")
    print(f"Artifacts: {result.artifacts}")
