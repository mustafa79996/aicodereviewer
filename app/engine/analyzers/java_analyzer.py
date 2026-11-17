import re
from typing import List, Optional
from app.models import CodeIssue, IssueCategory, IssueSeverity
from app.engine.analyzers.base import BaseAnalyzer

class JavaAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__("java")

    def analyze(self, code: str, filename: Optional[str] = None) -> List[CodeIssue]:
        issues: List[CodeIssue] = []
        lines = code.splitlines()

        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue

            # 1. String comparison with ==
            if re.search(r'"[^"]*"\s*==\s*[a-zA-Z0-9_]+|[a-zA-Z0-9_]+\s*==\s*"[^"]*"', line):
                issues.append(self.create_issue(
                    rule_id="BUG-JAVA-001",
                    title="String Comparison Using '==' Operator",
                    description="In Java, the '==' operator compares object reference addresses in memory, not the character contents. This leads to subtle logic failures.",
                    category=IssueCategory.BUG_LOGIC,
                    severity=IssueSeverity.HIGH,
                    line_number=idx,
                    code=code,
                    suggestion="Use 'str1.equals(str2)' or 'Objects.equals(str1, str2)' for content equality."
                ))

            # 2. Potential NullPointerException in equals: var.equals("constant")
            match_equals = re.search(r'([a-zA-Z0-9_]+)\.equals\(\s*"([^"]+)"\s*\)', line)
            if match_equals:
                var_name = match_equals.group(1)
                const_val = match_equals.group(2)
                issues.append(self.create_issue(
                    rule_id="BUG-JAVA-002",
                    title=f"Potential NullPointerException in '{var_name}.equals()'",
                    description=f"Calling '.equals()' on variable '{var_name}' will throw a NullPointerException if '{var_name}' is null.",
                    category=IssueCategory.BUG_LOGIC,
                    severity=IssueSeverity.MEDIUM,
                    line_number=idx,
                    code=code,
                    suggestion=f'Invert the check: \'"{const_val}".equals({var_name})\' or use \'Objects.equals({var_name}, "{const_val}")\'.'
                ))

            # 3. SQL Injection via string concatenation
            if re.search(r'\.(executeQuery|executeUpdate|execute)\s*\(\s*".*"\s*\+', line):
                issues.append(self.create_issue(
                    rule_id="SEC-JAVA-001",
                    title="SQL Injection via String Concatenation",
                    description="Constructing SQL queries via string concatenation allows SQL Injection attacks, giving attackers full access to the database.",
                    category=IssueCategory.SECURITY,
                    severity=IssueSeverity.CRITICAL,
                    line_number=idx,
                    code=code,
                    suggestion="Use 'PreparedStatement' with parameterized query placeholders '?'."
                ))

            # 4. Command Injection via Runtime.getRuntime().exec()
            if re.search(r'Runtime\.getRuntime\(\)\.exec\s*\(', line):
                issues.append(self.create_issue(
                    rule_id="SEC-JAVA-002",
                    title="Command Injection via 'Runtime.exec()'",
                    description="Executing system commands directly with user-influenced arguments leads to Command Injection.",
                    category=IssueCategory.SECURITY,
                    severity=IssueSeverity.HIGH,
                    line_number=idx,
                    code=code,
                    suggestion="Use 'ProcessBuilder' with a predefined argument array and strictly sanitize any external arguments."
                ))

            # 5. Resource leak: new FileInputStream / Statement without try-with-resources
            if re.search(r'new\s+(FileInputStream|FileOutputStream|FileReader|FileWriter|BufferedReader)\s*\(', line):
                # Check if preceded by try (
                if not re.search(r'try\s*\(', line):
                    issues.append(self.create_issue(
                        rule_id="PERF-JAVA-001",
                        title="Potential Unclosed Stream Resource Leak",
                        description="Stream initialized without explicit try-with-resources statement may leak OS file descriptors on exceptions.",
                        category=IssueCategory.PERFORMANCE,
                        severity=IssueSeverity.MEDIUM,
                        line_number=idx,
                        code=code,
                        suggestion="Wrap streams inside 'try (FileInputStream fis = new FileInputStream(...)) { ... }' for automatic cleanup."
                    ))

            # 6. Insecure crypto: DES / MD5 / SHA-1
            if re.search(r'GetInstance\s*\(\s*"(DES|MD5|SHA-1|DESede)"\s*\)', line, re.IGNORECASE):
                issues.append(self.create_issue(
                    rule_id="SEC-JAVA-003",
                    title="Cryptographically Weak Algorithm Used",
                    description="Algorithms like DES, MD5, and SHA-1 have known collision or brute-force vulnerabilities.",
                    category=IssueCategory.SECURITY,
                    severity=IssueSeverity.HIGH,
                    line_number=idx,
                    code=code,
                    suggestion="Upgrade to AES-GCM for encryption ('AES/GCM/NoPadding') and SHA-256 / SHA-512 for hashing."
                ))

            # 7. Empty catch block
            if re.search(r'catch\s*\([^)]+\)\s*\{\s*\}', line):
                issues.append(self.create_issue(
                    rule_id="BUG-JAVA-003",
                    title="Empty Catch Block Swallowing Exceptions",
                    description="Empty catch blocks swallow exceptions silently, masking serious errors and leaving system in undefined states.",
                    category=IssueCategory.BUG_LOGIC,
                    severity=IssueSeverity.HIGH,
                    line_number=idx,
                    code=code,
                    suggestion="Log the exception with a logger (e.g. 'logger.error(\"Context\", e);') or rethrow a runtime exception."
                ))

            # 8. System.out.println left in code
            if re.search(r'System\.(out|err)\.println\s*\(', line):
                issues.append(self.create_issue(
                    rule_id="STYLE-JAVA-001",
                    title="Console Print 'System.out.println' in Production Code",
                    description="Standard out/err print statements lack logging levels, timestamps, and thread identifiers, and can bottleneck I/O performance.",
                    category=IssueCategory.CODE_STYLE,
                    severity=IssueSeverity.INFO,
                    line_number=idx,
                    code=code,
                    suggestion="Replace with a structured logging framework such as SLF4J / Logback."
                ))

        return issues
