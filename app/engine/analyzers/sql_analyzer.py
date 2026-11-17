import re
from typing import List, Optional
from app.models import CodeIssue, IssueCategory, IssueSeverity
from app.engine.analyzers.base import BaseAnalyzer

class SqlAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__("sql")

    def analyze(self, code: str, filename: Optional[str] = None) -> List[CodeIssue]:
        issues: List[CodeIssue] = []
        lines = code.splitlines()

        # 1. Unbounded UPDATE / DELETE without WHERE clause
        # Normalize comments
        clean_code = re.sub(r'--.*', '', code)
        clean_code = re.sub(r'/\*.*?\*/', '', clean_code, flags=re.DOTALL)

        statements = [stmt.strip() for stmt in clean_code.split(";") if stmt.strip()]
        for stmt in statements:
            upper = stmt.upper()
            if re.search(r'\bDELETE\s+FROM\b', upper) and not re.search(r'\bWHERE\b', upper):
                issues.append(self.create_issue(
                    rule_id="BUG-SQL-001",
                    title="DELETE Statement Without WHERE Clause",
                    description="Executing a DELETE query without a WHERE filter deletes ALL records in the target table irrevocably.",
                    category=IssueCategory.BUG_LOGIC,
                    severity=IssueSeverity.CRITICAL,
                    code=stmt[:150],
                    suggestion="Add an explicit 'WHERE' clause with targeted primary key or condition filters."
                ))
            elif re.search(r'\bUPDATE\s+[a-zA-Z0-9_]+\s+SET\b', upper) and not re.search(r'\bWHERE\b', upper):
                issues.append(self.create_issue(
                    rule_id="BUG-SQL-002",
                    title="UPDATE Statement Without WHERE Clause",
                    description="Executing an UPDATE query without a WHERE filter modifies EVERY row in the target table.",
                    category=IssueCategory.BUG_LOGIC,
                    severity=IssueSeverity.CRITICAL,
                    code=stmt[:150],
                    suggestion="Specify a 'WHERE' clause to prevent global data corruption."
                ))

        # 2. Line-by-line checks
        for idx, line in enumerate(lines, 1):
            upper_line = line.upper()

            # SELECT *
            if re.search(r'\bSELECT\s+\*\s+FROM\b', upper_line):
                issues.append(self.create_issue(
                    rule_id="PERF-SQL-001",
                    title="Wildcard 'SELECT *' Anti-Pattern",
                    description="Retrieving all columns with 'SELECT *' wastes network bandwidth, degrades database cache utilization, and precludes index-only covering scans.",
                    category=IssueCategory.PERFORMANCE,
                    severity=IssueSeverity.MEDIUM,
                    line_number=idx,
                    code=code,
                    suggestion="Explicitly enumerate only the required column names."
                ))

            # Non-sargable leading wildcard LIKE '%xyz'
            if re.search(r"\bLIKE\s+['\"]%[a-zA-Z0-9_]+", upper_line):
                issues.append(self.create_issue(
                    rule_id="PERF-SQL-002",
                    title="Non-Sargable Leading Wildcard LIKE '%...'",
                    description="Using a leading wildcard ('%keyword') forces the query planner to perform a full table scan rather than an efficient B-tree index seek.",
                    category=IssueCategory.PERFORMANCE,
                    severity=IssueSeverity.MEDIUM,
                    line_number=idx,
                    code=code,
                    suggestion="Use trailing wildcards ('keyword%') or integrate a dedicated Full-Text Search index."
                ))

        return issues
