"""
NEXOUS Core - Exceptions

실행 예외 정의
"""


class NEXOUSError(Exception):
    """NEXOUS 기본 예외"""
    pass


class YAMLParseError(NEXOUSError):
    """YAML 파싱 오류"""
    pass


class SchemaValidationError(NEXOUSError):
    """JSON Schema 검증 실패"""
    pass


class DependencyCycleError(NEXOUSError):
    """의존성 순환 참조"""
    pass


class AgentNotFoundError(NEXOUSError):
    """Agent를 찾을 수 없음"""
    pass


class AgentExecutionError(NEXOUSError):
    """Agent 실행 중 오류"""
    def __init__(self, agent_id: str, message: str, original_error: Exception = None):
        self.agent_id = agent_id
        self.original_error = original_error
        super().__init__(f"Agent '{agent_id}' failed: {message}")


class RunnerError(NEXOUSError):
    """Runner 실행 오류"""
    pass
