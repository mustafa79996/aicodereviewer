from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class IssueSeverity(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFO = "Info"

class IssueCategory(str, Enum):
    SECURITY = "Security"
    BUG_LOGIC = "Bug & Logic"
    SYNTAX = "Syntax Error"
    PERFORMANCE = "Performance"
    CODE_STYLE = "Code Style & Standards"

class CodeIssue(BaseModel):
    id: str
    rule_id: str
    title: str
    description: str
    category: IssueCategory
    severity: IssueSeverity
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    line_end: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None
    fix_replacement: Optional[str] = None

class CodeMetrics(BaseModel):
    sloc: int = 0
    logical_loc: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    comment_ratio: float = 0.0
    cyclomatic_complexity: int = 1
    cognitive_complexity: int = 0
    maintainability_index: float = 100.0
    halstead_volume: float = 0.0
    halstead_difficulty: float = 0.0
    estimated_bugs: float = 0.0

class QualityScore(BaseModel):
    overall_score: int = 100
    grade: str = "A+"
    security_score: int = 100
    reliability_score: int = 100
    maintainability_score: int = 100
    performance_score: int = 100

class ReviewRequest(BaseModel):
    code: str
    language: str = "python"
    filename: Optional[str] = "unnamed_code"
    ai_provider: Optional[str] = "built-in"  # built-in, gemini, openai, ollama, groq, claude
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    ollama_url: Optional[str] = "http://localhost:11434"
    run_ai_deep_review: bool = True

class ReviewResponse(BaseModel):
    id: str
    timestamp: str
    language: str
    filename: Optional[str]
    issues: List[CodeIssue]
    issue_counts_by_severity: Dict[str, int]
    issue_counts_by_category: Dict[str, int]
    metrics: CodeMetrics
    quality_score: QualityScore
    original_code: str
    corrected_code: str
    unified_diff: str
    ai_insights: Optional[str] = None
    execution_time_ms: float = 0.0
