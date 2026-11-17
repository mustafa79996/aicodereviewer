import re
from typing import List, Optional
from app.models import CodeIssue, IssueCategory, IssueSeverity
from app.engine.analyzers.base import BaseAnalyzer

class GoAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__("go")

    def analyze(self, code: str, filename: Optional[str] = None) -> List[CodeIssue]:
        issues: List[CodeIssue] = []
        lines = code.splitlines()

        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue

            # 1. Ignored error: _, _ = ... or err assigned but ignored
            if re.search(r'_\s*,\s*_\s*=\s*[a-zA-Z0-9_]+\s*\(', line):
                issues.append(self.create_issue(
                    rule_id="BUG-GO-001",
                    title="Silently Ignored Return Error",
                    description="Ignoring errors with blank identifier '_' masks operational failures and crashes.",
                    category=IssueCategory.BUG_LOGIC,
                    severity=IssueSeverity.HIGH,
                    line_number=idx,
                    code=code,
                    suggestion="Check the error: 'val, err := ...; if err != nil { return err }'."
                ))

            # 2. Goroutine leak risk: go func() without context or channel
            if re.search(r'\bgo\s+func\s*\(\s*\)', line):
                issues.append(self.create_issue(
                    rule_id="PERF-GO-001",
                    title="Anonymous Goroutine Spawned",
                    description="Spawning background goroutines without context cancellation or stop channels can lead to goroutine leaks and memory exhaustion.",
                    category=IssueCategory.PERFORMANCE,
                    severity=IssueSeverity.MEDIUM,
                    line_number=idx,
                    code=code,
                    suggestion="Pass a 'context.Context' to monitor lifecycle and ensure goroutine terminates."
                ))

            # 3. Panic used instead of error return
            if re.search(r'\bpanic\s*\(', line):
                issues.append(self.create_issue(
                    rule_id="STYLE-GO-001",
                    title="Use of 'panic()' in Application Code",
                    description="Idiomatic Go encourages returning errors rather than panicking, except for unrecoverable startup configuration failures.",
                    category=IssueCategory.CODE_STYLE,
                    severity=IssueSeverity.LOW,
                    line_number=idx,
                    code=code,
                    suggestion="Return an 'error' value to let caller handle failure gracefully."
                ))

        return issues
