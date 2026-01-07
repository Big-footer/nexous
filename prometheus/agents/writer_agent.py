"""
WriterAgent - 문서 작성 Agent

이 파일의 책임:
- 문서 생성 및 작성
- 템플릿 적용
- 다양한 형식 지원 (Markdown, HTML 등)
- 다국어 지원
"""

from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field
import time

from prometheus.agents.base import (
    BaseAgent,
    AgentConfig,
    AgentInput,
    AgentOutput,
    AgentState,
)
from prometheus.llm.base import Message, MessageRole


class DocumentFormat(str, Enum):
    """문서 형식"""
    
    MARKDOWN = "markdown"
    HTML = "html"
    PLAIN_TEXT = "plain_text"
    JSON = "json"
    YAML = "yaml"


class DocumentSection(BaseModel):
    """문서 섹션"""
    
    title: str
    content: str
    level: int = 1
    order: int = 0


class GeneratedDocument(BaseModel):
    """생성된 문서"""
    
    title: str
    content: str
    format: DocumentFormat = DocumentFormat.MARKDOWN
    sections: List[DocumentSection] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    word_count: int = 0
    language: str = "en"
    
    def model_post_init(self, __context: Any) -> None:
        """초기화 후 처리"""
        self.word_count = len(self.content.split())
    
    def to_markdown(self) -> str:
        """Markdown 형식으로 변환"""
        if self.format == DocumentFormat.MARKDOWN:
            return self.content
        
        # 섹션 기반 생성
        lines = [f"# {self.title}\n"]
        for section in sorted(self.sections, key=lambda s: s.order):
            prefix = "#" * (section.level + 1)
            lines.append(f"{prefix} {section.title}\n")
            lines.append(f"{section.content}\n")
        
        return "\n".join(lines)
    
    def to_html(self) -> str:
        """HTML 형식으로 변환"""
        if self.format == DocumentFormat.HTML:
            return self.content
        
        # 간단한 변환
        html_content = self.content.replace("\n", "<br>\n")
        return f"""<!DOCTYPE html>
<html>
<head><title>{self.title}</title></head>
<body>
<h1>{self.title}</h1>
{html_content}
</body>
</html>"""


class WriterConfig(AgentConfig):
    """Writer 설정"""
    
    name: str = "WriterAgent"
    default_format: DocumentFormat = DocumentFormat.MARKDOWN
    default_language: str = "ko"
    max_length: Optional[int] = None
    include_toc: bool = False


class WriterAgent(BaseAgent):
    """
    문서 작성 Agent
    
    실행 결과를 바탕으로 문서를 생성하고 작성합니다.
    다양한 형식과 템플릿을 지원합니다.
    """
    
    agent_type: str = "writer"
    
    WRITING_PROMPT = """You are a professional document writer. Create a well-structured document based on the provided information.

Document Requirements:
- Title: {title}
- Format: {format}
- Language: {language}
- Style: {style}

Source Information:
{source_content}

Additional Instructions:
{instructions}

Write the document now. Make it clear, professional, and well-organized."""

    TEMPLATE_PROMPT = """You are a professional document writer. Fill in the following template with the provided information.

Template:
{template}

Information to use:
{data}

Instructions:
- Replace all {{placeholder}} markers with appropriate content
- Maintain the template structure
- Ensure consistency and professionalism

Generate the completed document:"""

    def __init__(
        self,
        config: Optional[WriterConfig] = None,
        **kwargs: Any,
    ) -> None:
        """
        WriterAgent 초기화
        
        Args:
            config: Writer 설정
            **kwargs: 추가 인자
        """
        super().__init__(config=config or WriterConfig(), **kwargs)
        self._templates: Dict[str, str] = {}
    
    def _default_system_prompt(self) -> str:
        """기본 시스템 프롬프트"""
        return """You are an expert document writer and editor. Your role is to:
1. Create clear, well-structured documents
2. Adapt writing style to the target audience
3. Ensure accuracy and completeness
4. Format documents appropriately
5. Support multiple languages

Always produce professional, readable content."""
    
    async def run(
        self,
        input: AgentInput,
    ) -> AgentOutput:
        """
        문서 작성 실행
        
        Args:
            input: Agent 입력
            
        Returns:
            Agent 출력 (GeneratedDocument 포함)
        """
        start_time = time.time()
        self._set_state(AgentState.RUNNING)
        
        try:
            # 옵션 추출
            title = input.context.get("title", "Generated Document")
            format_type = input.context.get("format", self.config.default_format)
            language = input.context.get("language", self.config.default_language)
            template_name = input.context.get("template")
            
            # 템플릿 사용 여부
            if template_name and template_name in self._templates:
                document = await self.apply_template(
                    template_name=template_name,
                    data={"content": input.task, **input.context},
                )
            else:
                document = await self.generate_document(
                    title=title,
                    source_content=input.task,
                    format_type=format_type if isinstance(format_type, DocumentFormat) else DocumentFormat(format_type),
                    language=language,
                    instructions=input.context.get("instructions", ""),
                )
            
            execution_time = time.time() - start_time
            self._set_state(AgentState.COMPLETED)
            
            return AgentOutput.success_output(
                result=document,
                messages=self._messages.copy(),
                execution_time=execution_time,
                metadata={
                    "word_count": document.word_count,
                    "format": document.format.value,
                },
            )
            
        except Exception as e:
            self._set_state(AgentState.FAILED)
            return AgentOutput.error_output(
                error=str(e),
                messages=self._messages.copy(),
            )
    
    async def generate_document(
        self,
        title: str,
        source_content: str,
        format_type: DocumentFormat = DocumentFormat.MARKDOWN,
        language: str = "ko",
        style: str = "professional",
        instructions: str = "",
    ) -> GeneratedDocument:
        """
        문서 생성
        
        Args:
            title: 문서 제목
            source_content: 소스 내용
            format_type: 문서 형식
            language: 언어
            style: 문서 스타일
            instructions: 추가 지침
            
        Returns:
            생성된 문서
        """
        prompt = self.WRITING_PROMPT.format(
            title=title,
            format=format_type.value,
            language=language,
            style=style,
            source_content=source_content,
            instructions=instructions or "None",
        )
        
        messages = [
            Message.system(self.get_system_prompt()),
            Message.user(prompt),
        ]
        
        response = await self._call_llm(messages)
        
        self._add_message(Message.user(prompt))
        self._add_message(Message.assistant(response.content))
        
        return GeneratedDocument(
            title=title,
            content=response.content,
            format=format_type,
            language=language,
            metadata={
                "style": style,
                "source_length": len(source_content),
            },
        )
    
    async def apply_template(
        self,
        template_name: str,
        data: Dict[str, Any],
    ) -> GeneratedDocument:
        """
        템플릿 적용
        
        Args:
            template_name: 템플릿 이름
            data: 채울 데이터
            
        Returns:
            생성된 문서
        """
        template = self._templates.get(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")
        
        # 간단한 변수 치환 먼저 시도
        filled_template = template
        for key, value in data.items():
            placeholder = "{{" + key + "}}"
            filled_template = filled_template.replace(placeholder, str(value))
        
        # 아직 플레이스홀더가 남아있으면 LLM 사용
        if "{{" in filled_template:
            prompt = self.TEMPLATE_PROMPT.format(
                template=template,
                data=str(data),
            )
            
            messages = [
                Message.system(self.get_system_prompt()),
                Message.user(prompt),
            ]
            
            response = await self._call_llm(messages)
            filled_template = response.content
            
            self._add_message(Message.user(prompt))
            self._add_message(Message.assistant(response.content))
        
        return GeneratedDocument(
            title=data.get("title", template_name),
            content=filled_template,
            format=DocumentFormat.MARKDOWN,
            metadata={"template": template_name},
        )
    
    async def translate(
        self,
        content: str,
        source_lang: str,
        target_lang: str,
    ) -> str:
        """
        번역
        
        Args:
            content: 번역할 내용
            source_lang: 원본 언어
            target_lang: 대상 언어
            
        Returns:
            번역된 내용
        """
        prompt = f"""Translate the following text from {source_lang} to {target_lang}.
Maintain the original formatting and structure.

Text to translate:
{content}

Translation:"""
        
        messages = [
            Message.system("You are a professional translator. Provide accurate, natural translations."),
            Message.user(prompt),
        ]
        
        response = await self._call_llm(messages)
        return response.content
    
    async def summarize(
        self,
        content: str,
        max_length: Optional[int] = None,
        style: str = "concise",
    ) -> str:
        """
        요약
        
        Args:
            content: 요약할 내용
            max_length: 최대 길이 (단어 수)
            style: 요약 스타일
            
        Returns:
            요약된 내용
        """
        length_instruction = f"Keep it under {max_length} words." if max_length else ""
        
        prompt = f"""Summarize the following content in a {style} manner.
{length_instruction}

Content:
{content}

Summary:"""
        
        messages = [
            Message.system("You are an expert at creating clear, accurate summaries."),
            Message.user(prompt),
        ]
        
        response = await self._call_llm(messages)
        return response.content
    
    async def improve_writing(
        self,
        content: str,
        focus: str = "clarity",
    ) -> str:
        """
        글 개선
        
        Args:
            content: 개선할 내용
            focus: 개선 초점 (clarity, grammar, style, etc.)
            
        Returns:
            개선된 내용
        """
        prompt = f"""Improve the following text with focus on {focus}.
Maintain the original meaning and intent.

Original text:
{content}

Improved text:"""
        
        messages = [
            Message.system("You are an expert editor who improves writing while preserving meaning."),
            Message.user(prompt),
        ]
        
        response = await self._call_llm(messages)
        return response.content
    
    def register_template(
        self,
        name: str,
        template: str,
    ) -> None:
        """
        템플릿 등록
        
        Args:
            name: 템플릿 이름
            template: 템플릿 내용
        """
        self._templates[name] = template
    
    def get_template(
        self,
        name: str,
    ) -> Optional[str]:
        """
        템플릿 조회
        
        Args:
            name: 템플릿 이름
            
        Returns:
            템플릿 내용 또는 None
        """
        return self._templates.get(name)
    
    def list_templates(self) -> List[str]:
        """
        등록된 템플릿 목록
        
        Returns:
            템플릿 이름 목록
        """
        return list(self._templates.keys())
    
    def remove_template(
        self,
        name: str,
    ) -> bool:
        """
        템플릿 제거
        
        Args:
            name: 템플릿 이름
            
        Returns:
            제거 성공 여부
        """
        if name in self._templates:
            del self._templates[name]
            return True
        return False
