import re
from typing import List, Optional
from app.models import CodeIssue, IssueCategory, IssueSeverity
from app.engine.analyzers.base import BaseAnalyzer

class JavaScriptAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__("javascript")

    def analyze(self, code: str, filename: Optional[str] = None) -> List[CodeIssue]:
        issues: List[CodeIssue] = []
        lines = code.splitlines()

        # 1. Bracket & parenthesis balance check
        stack = []
        match_map = {')': '(', '}': '{', ']': '['}
        for line_idx, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*"):
                continue
            for char_idx, char in enumerate(line, 1):
                if char in "({[":
                    stack.append((char, line_idx, char_idx))
                elif char in ")}]":
                    if not stack or stack[-1][0] != match_map[char]:
                        issues.append(self.create_issue(
                            rule_id="SYNTAX-JS-001",
                            title=f"Unmatched Closing Bracket '{char}'",
                            description=f"Encountered closing bracket '{char}' without a corresponding opening bracket.",
                            category=IssueCategory.SYNTAX,
                            severity=IssueSeverity.CRITICAL,
                            line_number=line_idx,
                            column_number=char_idx,
                            code=code,
                            suggestion=f"Check bracket balance or remove the extraneous '{char}'."
                        ))
                    else:
                        stack.pop()

        if stack:
            open_char, l_num, c_num = stack[-1]
            issues.append(self.create_issue(
                rule_id="SYNTAX-JS-002",
                title=f"Unclosed Bracket '{open_char}'",
                description=f"Opening bracket '{open_char}' opened at line {l_num} was never closed.",
                category=IssueCategory.SYNTAX,
                severity=IssueSeverity.CRITICAL,
                line_number=l_num,
                column_number=c_num,
                code=code,
                suggestion="Add matching closing bracket before the end of the scope or file."
            ))

        # 2. Line by line regex and heuristic analysis
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue

            # Dangerous eval / Function
            if re.search(r"\beval\s*\(", line):
                issues.append(self.create_issue(
                    rule_id="SEC-JS-001",
                    title="Dangerous Execution with 'eval()'",
                    description="Passing dynamic strings to 'eval()' can result in Remote Code Execution (XSS/RCE).",
                    category=IssueCategory.SECURITY,
                    severity=IssueSeverity.CRITICAL,
                    line_number=idx,
                    code=code,
                    suggestion="Parse JSON safely using 'JSON.parse()' or refactor using standard object lookups."
                ))

            # DOM XSS: innerHTML / outerHTML / document.write
            if re.search(r"\.(innerHTML|outerHTML)\s*=", line):
                issues.append(self.create_issue(
                    rule_id="SEC-JS-002",
                    title="Cross-Site Scripting (XSS) via innerHTML",
                    description="Directly assigning untrusted strings to 'innerHTML' or 'outerHTML' allows client-side script injection (DOM XSS).",
                    category=IssueCategory.SECURITY,
                    severity=IssueSeverity.HIGH,
                    line_number=idx,
                    code=code,
                    suggestion="Use 'textContent', 'innerText', or sanitize HTML using DOMPurify before insertion."
                ))
            elif re.search(r"\bdocument\.write\s*\(", line):
                issues.append(self.create_issue(
                    rule_id="SEC-JS-003",
                    title="Insecure 'document.write()' Usage",
                    description="'document.write()' presents significant security risks, blocks page rendering, and is strongly discouraged in modern JavaScript.",
                    category=IssueCategory.SECURITY,
                    severity=IssueSeverity.HIGH,
                    line_number=idx,
                    code=code,
                    suggestion="Manipulate the DOM dynamically using 'document.createElement()' and 'appendChild()'."
                ))

            # Weak equality == vs ===
            if re.search(r"[^!=]==[^=]", line):
                issues.append(self.create_issue(
                    rule_id="STYLE-JS-001",
                    title="Loose Equality Operator '=='",
                    description="The loose equality operator '==' performs implicit type coercion, often producing surprising bugs (e.g., 0 == '0' or false == []).",
                    category=IssueCategory.CODE_STYLE,
                    severity=IssueSeverity.LOW,
                    line_number=idx,
                    code=code,
                    suggestion="Use strict equality '===' to verify both type and value."
                ))

            # Use of var instead of let/const
            if re.search(r"\bvar\s+[a-zA-Z_$]", line):
                issues.append(self.create_issue(
                    rule_id="STYLE-JS-002",
                    title="Legacy 'var' Declaration",
                    description="'var' has function scope and is subject to variable hoisting, which causes confusing bugs. Modern ES6+ recommends block-scoped declarations.",
                    category=IssueCategory.CODE_STYLE,
                    severity=IssueSeverity.LOW,
                    line_number=idx,
                    code=code,
                    suggestion="Replace 'var' with 'const' for read-only variables or 'let' for mutable variables."
                ))

            # Empty catch block: catch (e) {}
            if re.search(r"catch\s*\([^)]*\)\s*\{\s*\}", line):
                issues.append(self.create_issue(
                    rule_id="BUG-JS-001",
                    title="Swallowed Error in Empty 'catch' Block",
                    description="An empty catch block silently ignores errors, hiding network failures, runtime crashes, and unexpected exceptions.",
                    category=IssueCategory.BUG_LOGIC,
                    severity=IssueSeverity.HIGH,
                    line_number=idx,
                    code=code,
                    suggestion="Log the error using 'console.error(err)' or rethrow with contextual information."
                ))

            # Leftover console.log in production code
            if re.search(r"\bconsole\.log\s*\(", line):
                issues.append(self.create_issue(
                    rule_id="STYLE-JS-003",
                    title="Production Debugger 'console.log' Detected",
                    description="Leaving 'console.log' statements in production code may leak sensitive application state, token data, and degrades performance.",
                    category=IssueCategory.CODE_STYLE,
                    severity=IssueSeverity.INFO,
                    line_number=idx,
                    code=code,
                    suggestion="Remove debug logs or replace with an enterprise logging framework."
                ))

            # Prototype pollution vulnerability
            if re.search(r"(__proto__|prototype\.constructor|Object\.prototype)", line):
                issues.append(self.create_issue(
                    rule_id="SEC-JS-004",
                    title="Prototype Pollution Vulnerability Risk",
                    description="Direct access or assignment to '__proto__' or prototype chains can allow attackers to override global object behaviors.",
                    category=IssueCategory.SECURITY,
                    severity=IssueSeverity.HIGH,
                    line_number=idx,
                    code=code,
                    suggestion="Use 'Object.create(null)' for dictionary objects or validate property keys before assignment."
                ))

        return issues
