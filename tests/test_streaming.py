"""
스트리밍 지원 테스트
"""

import pytest
from prometheus.llm.streaming import (
    StreamEventType,
    StreamEvent,
    StreamingHandler,
    stream_to_string,
    create_console_handler,
)


class TestStreamEvent:
    """StreamEvent 테스트"""
    
    def test_event_creation(self):
        """이벤트 생성"""
        event = StreamEvent(
            type=StreamEventType.TOKEN,
            content="Hello",
            agent="planner",
        )
        assert event.type == StreamEventType.TOKEN
        assert event.content == "Hello"
        assert event.agent == "planner"
    
    def test_event_to_dict(self):
        """이벤트 딕셔너리 변환"""
        event = StreamEvent(
            type=StreamEventType.AGENT_START,
            agent="executor",
            metadata={"step": 1},
        )
        d = event.to_dict()
        
        assert d["type"] == "agent_start"
        assert d["agent"] == "executor"
        assert d["metadata"]["step"] == 1


class TestStreamingHandler:
    """StreamingHandler 테스트"""
    
    def test_handler_creation(self):
        """핸들러 생성"""
        handler = StreamingHandler()
        assert handler.buffer == ""
    
    def test_handle_string_token(self):
        """문자열 토큰 처리"""
        tokens = []
        handler = StreamingHandler(on_token=lambda t: tokens.append(t))
        
        handler.handle("Hello")
        handler.handle(" World")
        
        assert tokens == ["Hello", " World"]
        assert handler.buffer == "Hello World"
    
    def test_handle_stream_event(self):
        """StreamEvent 처리"""
        tokens = []
        handler = StreamingHandler(on_token=lambda t: tokens.append(t))
        
        event = StreamEvent(type=StreamEventType.TOKEN, content="Test")
        handler.handle(event)
        
        assert tokens == ["Test"]
    
    def test_handle_dict_event(self):
        """딕셔너리 이벤트 처리"""
        tokens = []
        handler = StreamingHandler(on_token=lambda t: tokens.append(t))
        
        handler.handle({"type": "token", "content": "Dict"})
        
        assert tokens == ["Dict"]
    
    def test_agent_callbacks(self):
        """Agent 콜백"""
        started = []
        ended = []
        
        handler = StreamingHandler(
            on_agent_start=lambda a: started.append(a),
            on_agent_end=lambda a, r: ended.append((a, r)),
        )
        
        handler.handle(StreamEvent(type=StreamEventType.AGENT_START, agent="planner"))
        handler.handle(StreamEvent(type=StreamEventType.AGENT_END, agent="planner", content="done"))
        
        assert started == ["planner"]
        assert ended == [("planner", "done")]
    
    def test_tool_callbacks(self):
        """Tool 콜백"""
        calls = []
        results = []
        
        handler = StreamingHandler(
            on_tool_call=lambda n, a: calls.append((n, a)),
            on_tool_result=lambda n, r: results.append((n, r)),
        )
        
        handler.handle(StreamEvent(
            type=StreamEventType.TOOL_CALL,
            content={"name": "python_exec", "args": {"code": "print(1)"}},
        ))
        handler.handle(StreamEvent(
            type=StreamEventType.TOOL_RESULT,
            content={"name": "python_exec", "result": "1"},
        ))
        
        assert calls == [("python_exec", {"code": "print(1)"})]
        assert results == [("python_exec", "1")]
    
    def test_error_callback(self):
        """에러 콜백"""
        errors = []
        handler = StreamingHandler(on_error=lambda e: errors.append(str(e)))
        
        handler.handle(StreamEvent(type=StreamEventType.ERROR, content="Test error"))
        
        assert len(errors) == 1
        assert "Test error" in errors[0]
    
    def test_clear_buffer(self):
        """버퍼 초기화"""
        handler = StreamingHandler()
        handler.handle("Hello World")
        
        content = handler.clear_buffer()
        
        assert content == "Hello World"
        assert handler.buffer == ""


class TestStreamUtilities:
    """스트림 유틸리티 테스트"""
    
    def test_stream_to_string_strings(self):
        """문자열 스트림 변환"""
        stream = iter(["Hello", " ", "World"])
        result = stream_to_string(stream)
        
        assert result == "Hello World"
    
    def test_stream_to_string_dicts(self):
        """딕셔너리 스트림 변환"""
        stream = iter([
            {"content": "Hello"},
            {"content": " "},
            {"content": "World"},
        ])
        result = stream_to_string(stream)
        
        assert result == "Hello World"
    
    def test_create_console_handler(self):
        """콘솔 핸들러 생성"""
        handler = create_console_handler()
        
        assert handler.on_token is not None
        assert handler.on_agent_start is not None
        assert handler.on_agent_end is not None
        assert handler.on_tool_call is not None
        assert handler.on_error is not None
        assert handler.on_end is not None


class TestStreamEventTypes:
    """StreamEventType 테스트"""
    
    def test_all_event_types(self):
        """모든 이벤트 타입"""
        types = [
            StreamEventType.START,
            StreamEventType.TOKEN,
            StreamEventType.TOOL_CALL,
            StreamEventType.TOOL_RESULT,
            StreamEventType.AGENT_START,
            StreamEventType.AGENT_END,
            StreamEventType.ERROR,
            StreamEventType.END,
        ]
        
        assert len(types) == 8
    
    def test_event_type_values(self):
        """이벤트 타입 값"""
        assert StreamEventType.TOKEN.value == "token"
        assert StreamEventType.AGENT_START.value == "agent_start"
