import uuid
from typing import List, Optional
from app.models import CodeIssue, IssueCategory, IssueSeverity

class BaseAnalyzer:
    def __init__(self, language: str):
        self.language = language

    def analyze(self, code: str, filename: Optional[str] = None) -> List[CodeIssue]:
        raise NotImplementedError("Each analyzer must implement analyze()")

    def get_snippet(self, code: str, line_number: Optional[int], context_lines: int = 1) -> Optional[str]:
        if not line_number or line_number < 1:
            return None
        lines = code.splitlines()
        start = max(0, line_number - 1 - context_lines)
        end = min(len(lines), line_number + context_lines)
        
        snippet_lines = []
        for i in range(start, end):
            prefix = " > " if (i + 1) == line_number else "   "
            snippet_lines.append(f"{i + 1:4d} |{prefix}{lines[i]}")
        return "\n".join(snippet_lines)

    def create_issue(
        self,
        rule_id: str,
        title: str,
        description: str,
        category: IssueCategory,
        severity: IssueSeverity,
        line_number: Optional[int] = None,
        column_number: Optional[int] = None,
        line_end: Optional[int] = None,
        code: Optional[str] = None,
        suggestion: Optional[str] = None,
        fix_replacement: Optional[str] = None
    ) -> CodeIssue:
        snippet = self.get_snippet(code, line_number) if (code and line_number) else None
        return CodeIssue(
            id=str(uuid.uuid4())[:8],
            rule_id=rule_id,
            title=title,
            description=description,
            category=category,
            severity=severity,
            line_number=line_number,
            column_number=column_number,
            line_end=line_end,
            code_snippet=snippet,
            suggestion=suggestion,
            fix_replacement=fix_replacement
        )
