"""
QAAgent - 품질 검증 Agent

이 파일의 책임:
- 결과물 품질 검토
- 요청 대비 검증
- 개선점 제안
- 품질 보고서 생성
"""

from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field
import json
import time

from prometheus.agents.base import (
    BaseAgent,
    AgentConfig,
    AgentInput,
    AgentOutput,
    AgentState,
)
from prometheus.llm.base import Message, MessageRole


class QualityLevel(str, Enum):
    """품질 수준"""
    
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    NEEDS_IMPROVEMENT = "needs_improvement"
    POOR = "poor"


class QualityDimension(str, Enum):
    """품질 평가 차원"""
    
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    CLARITY = "clarity"
    RELEVANCE = "relevance"
    CONSISTENCY = "consistency"
    FORMAT = "format"


class QualityScore(BaseModel):
    """품질 점수"""
    
    dimension: QualityDimension
    score: float = Field(ge=0.0, le=1.0)
    feedback: str = ""
    suggestions: List[str] = Field(default_factory=list)


class QualityIssue(BaseModel):
    """품질 이슈"""
    
    severity: str = "medium"  # low, medium, high, critical
    category: str
    description: str
    location: Optional[str] = None
    suggestion: Optional[str] = None


class QualityReport(BaseModel):
    """품질 보고서"""
    
    overall_level: QualityLevel = QualityLevel.GOOD
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    dimension_scores: List[QualityScore] = Field(default_factory=list)
    issues: List[QualityIssue] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    passed: bool = True
    summary: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def model_post_init(self, __context: Any) -> None:
        """초기화 후 처리 - 전체 점수 계산"""
        if self.dimension_scores and self.overall_score == 0.0:
            self.overall_score = sum(s.score for s in self.dimension_scores) / len(self.dimension_scores)
            self.overall_level = self._score_to_level(self.overall_score)
    
    def _score_to_level(self, score: float) -> QualityLevel:
        """점수를 품질 수준으로 변환"""
        if score >= 0.9:
            return QualityLevel.EXCELLENT
        elif score >= 0.75:
            return QualityLevel.GOOD
        elif score >= 0.6:
            return QualityLevel.ACCEPTABLE
        elif score >= 0.4:
            return QualityLevel.NEEDS_IMPROVEMENT
        else:
            return QualityLevel.POOR
    
    def get_critical_issues(self) -> List[QualityIssue]:
        """심각한 이슈 목록"""
        return [i for i in self.issues if i.severity in ["critical", "high"]]
    
    def to_markdown(self) -> str:
        """Markdown 형식으로 변환"""
        lines = [
            "# Quality Report\n",
            f"**Overall Level**: {self.overall_level.value}",
            f"**Overall Score**: {self.overall_score:.2f}",
            f"**Status**: {'✅ Passed' if self.passed else '❌ Failed'}\n",
            "## Summary",
            self.summary or "No summary provided.",
            "",
        ]
        
        if self.dimension_scores:
            lines.append("## Dimension Scores")
            for score in self.dimension_scores:
                lines.append(f"- **{score.dimension.value}**: {score.score:.2f} - {score.feedback}")
            lines.append("")
        
        if self.strengths:
            lines.append("## Strengths")
            for s in self.strengths:
                lines.append(f"- {s}")
            lines.append("")
        
        if self.improvements:
            lines.append("## Improvements Needed")
            for i in self.improvements:
                lines.append(f"- {i}")
            lines.append("")
        
        if self.issues:
            lines.append("## Issues")
            for issue in self.issues:
                lines.append(f"- [{issue.severity.upper()}] {issue.category}: {issue.description}")
            lines.append("")
        
        return "\n".join(lines)


class QAConfig(AgentConfig):
    """QA 설정"""
    
    name: str = "QAAgent"
    pass_threshold: float = 0.7
    dimensions: List[QualityDimension] = Field(default_factory=lambda: [
        QualityDimension.ACCURACY,
        QualityDimension.COMPLETENESS,
        QualityDimension.CLARITY,
        QualityDimension.RELEVANCE,
    ])
    strict_mode: bool = False


class QAAgent(BaseAgent):
    """
    품질 검증 Agent
    
    결과물의 품질을 검토하고 개선점을 제안합니다.
    원래 요청과의 일치도를 검증합니다.
    """
    
    agent_type: str = "qa"
    
    REVIEW_PROMPT = """You are a quality assurance expert. Review the following content against the original request.

Original Request:
{original_request}

Content to Review:
{content}

Evaluate the content on these dimensions:
{dimensions}

Provide your review as a JSON object with this structure:
{{
    "overall_score": 0.85,
    "dimension_scores": [
        {{
            "dimension": "accuracy",
            "score": 0.9,
            "feedback": "Accurate and correct",
            "suggestions": ["Consider adding more details"]
        }}
    ],
    "issues": [
        {{
            "severity": "medium",
            "category": "completeness",
            "description": "Missing section on X",
            "suggestion": "Add a section covering X"
        }}
    ],
    "strengths": ["Well organized", "Clear language"],
    "improvements": ["Add more examples", "Include references"],
    "summary": "Overall good quality with minor improvements needed"
}}

Provide your quality review:"""

    VALIDATION_PROMPT = """You are a validation expert. Check if the content meets the requirements specified in the original request.

Original Request:
{original_request}

Content to Validate:
{content}

Validation Criteria:
{criteria}

Respond with a JSON object:
{{
    "passed": true,
    "score": 0.85,
    "matched_requirements": ["req1", "req2"],
    "missing_requirements": ["req3"],
    "feedback": "Content meets most requirements"
}}

Validate now:"""

    def __init__(
        self,
        config: Optional[QAConfig] = None,
        **kwargs: Any,
    ) -> None:
        """
        QAAgent 초기화
        
        Args:
            config: QA 설정
            **kwargs: 추가 인자
        """
        super().__init__(config=config or QAConfig(), **kwargs)
    
    def _default_system_prompt(self) -> str:
        """기본 시스템 프롬프트"""
        return """You are an expert quality assurance analyst. Your role is to:
1. Thoroughly review content for quality issues
2. Evaluate against specified criteria
3. Provide constructive, actionable feedback
4. Identify both strengths and areas for improvement
5. Be fair, objective, and detailed in your assessments

Always provide your reviews in the requested JSON format."""
    
    async def run(
        self,
        input: AgentInput,
    ) -> AgentOutput:
        """
        품질 검토 실행
        
        Args:
            input: Agent 입력
            
        Returns:
            Agent 출력 (QualityReport 포함)
        """
        start_time = time.time()
        self._set_state(AgentState.RUNNING)
        
        try:
            # 원래 요청 추출
            original_request = input.context.get("original_request", "")
            content = input.task
            
            # 리뷰 수행
            report = await self.review(
                content=content,
                original_request=original_request,
            )
            
            execution_time = time.time() - start_time
            self._set_state(AgentState.COMPLETED)
            
            return AgentOutput(
                result=report,
                success=report.passed,
                messages=self._messages.copy(),
                execution_time=execution_time,
                metadata={
                    "overall_score": report.overall_score,
                    "passed": report.passed,
                    "issues_count": len(report.issues),
                },
            )
            
        except Exception as e:
            self._set_state(AgentState.FAILED)
            return AgentOutput.error_output(
                error=str(e),
                messages=self._messages.copy(),
            )
    
    async def review(
        self,
        content: str,
        original_request: str = "",
        dimensions: Optional[List[QualityDimension]] = None,
    ) -> QualityReport:
        """
        품질 리뷰
        
        Args:
            content: 검토할 내용
            original_request: 원래 요청
            dimensions: 평가 차원
            
        Returns:
            품질 보고서
        """
        dims = dimensions or self.config.dimensions
        dims_str = ", ".join(d.value for d in dims)
        
        prompt = self.REVIEW_PROMPT.format(
            original_request=original_request or "Not provided",
            content=content,
            dimensions=dims_str,
        )
        
        messages = [
            Message.system(self.get_system_prompt()),
            Message.user(prompt),
        ]
        
        response = await self._call_llm(messages, temperature=0.3)
        
        self._add_message(Message.user(prompt))
        self._add_message(Message.assistant(response.content))
        
        # 응답 파싱
        report = self._parse_review_response(response.content)
        
        # 통과 여부 결정
        report.passed = report.overall_score >= self.config.pass_threshold
        if self.config.strict_mode and report.get_critical_issues():
            report.passed = False
        
        return report
    
    async def validate_against_request(
        self,
        content: str,
        original_request: str,
        criteria: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        요청 대비 검증
        
        Args:
            content: 검증할 내용
            original_request: 원래 요청
            criteria: 검증 기준
            
        Returns:
            검증 결과
        """
        criteria_str = "\n".join(f"- {c}" for c in (criteria or [])) or "Match the original request"
        
        prompt = self.VALIDATION_PROMPT.format(
            original_request=original_request,
            content=content,
            criteria=criteria_str,
        )
        
        messages = [
            Message.system(self.get_system_prompt()),
            Message.user(prompt),
        ]
        
        response = await self._call_llm(messages, temperature=0.2)
        
        try:
            json_str = self._extract_json(response.content)
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {
                "passed": False,
                "score": 0.0,
                "feedback": "Failed to parse validation response",
            }
    
    async def suggest_improvements(
        self,
        content: str,
        focus_areas: Optional[List[str]] = None,
    ) -> List[str]:
        """
        개선점 제안
        
        Args:
            content: 검토할 내용
            focus_areas: 집중 영역
            
        Returns:
            개선점 목록
        """
        focus_str = ", ".join(focus_areas) if focus_areas else "general quality"
        
        prompt = f"""Review the following content and suggest specific improvements.
Focus on: {focus_str}

Content:
{content}

Provide 3-5 specific, actionable improvements as a JSON array:
["improvement 1", "improvement 2", ...]"""
        
        messages = [
            Message.system("You are an expert at providing constructive improvement suggestions."),
            Message.user(prompt),
        ]
        
        response = await self._call_llm(messages, temperature=0.4)
        
        try:
            json_str = self._extract_json(response.content)
            return json.loads(json_str)
        except json.JSONDecodeError:
            return [response.content]
    
    async def compare_versions(
        self,
        original: str,
        revised: str,
    ) -> Dict[str, Any]:
        """
        버전 비교
        
        Args:
            original: 원본 내용
            revised: 수정된 내용
            
        Returns:
            비교 결과
        """
        prompt = f"""Compare the original and revised versions.
Identify what changed and whether the revisions improved the content.

Original:
{original}

Revised:
{revised}

Respond with a JSON object:
{{
    "improved": true,
    "changes": ["change 1", "change 2"],
    "improvement_score": 0.8,
    "summary": "Brief comparison summary"
}}"""
        
        messages = [
            Message.system("You are an expert at analyzing content changes."),
            Message.user(prompt),
        ]
        
        response = await self._call_llm(messages, temperature=0.3)
        
        try:
            json_str = self._extract_json(response.content)
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {
                "improved": False,
                "changes": [],
                "summary": response.content,
            }
    
    def _parse_review_response(self, response: str) -> QualityReport:
        """
        리뷰 응답 파싱
        
        Args:
            response: LLM 응답
            
        Returns:
            품질 보고서
        """
        try:
            json_str = self._extract_json(response)
            data = json.loads(json_str)
            
            # dimension_scores 파싱
            dimension_scores = []
            for ds in data.get("dimension_scores", []):
                dimension_scores.append(QualityScore(
                    dimension=QualityDimension(ds.get("dimension", "accuracy")),
                    score=ds.get("score", 0.5),
                    feedback=ds.get("feedback", ""),
                    suggestions=ds.get("suggestions", []),
                ))
            
            # issues 파싱
            issues = []
            for issue in data.get("issues", []):
                issues.append(QualityIssue(
                    severity=issue.get("severity", "medium"),
                    category=issue.get("category", "general"),
                    description=issue.get("description", ""),
                    location=issue.get("location"),
                    suggestion=issue.get("suggestion"),
                ))
            
            return QualityReport(
                overall_score=data.get("overall_score", 0.5),
                dimension_scores=dimension_scores,
                issues=issues,
                strengths=data.get("strengths", []),
                improvements=data.get("improvements", []),
                summary=data.get("summary", ""),
            )
            
        except (json.JSONDecodeError, KeyError):
            # 파싱 실패 시 기본 보고서
            return QualityReport(
                overall_score=0.5,
                summary=response[:500] if response else "Review parsing failed",
            )
    
    def _extract_json(self, text: str) -> str:
        """텍스트에서 JSON 추출"""
        import re
        
        # ```json ... ``` 패턴
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            return json_match.group(1).strip()
        
        # { ... } 패턴
        brace_match = re.search(r'(\{[\s\S]*\})', text)
        if brace_match:
            return brace_match.group(1)
        
        # [ ... ] 패턴
        bracket_match = re.search(r'(\[[\s\S]*\])', text)
        if bracket_match:
            return bracket_match.group(1)
        
        return text
