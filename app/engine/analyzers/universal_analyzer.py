import re
from typing import List, Optional
from app.models import CodeIssue, IssueCategory, IssueSeverity
from app.engine.analyzers.base import BaseAnalyzer

SECRET_PATTERNS = [
    (r'(?i)(?:aws_access_key_id|aws_secret_access_key)\s*[:=]\s*["\']([a-zA-Z0-9/+=]{20,40})["\']', "AWS Secret Key Exposure", IssueSeverity.CRITICAL),
    (r'(?i)(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36}', "GitHub Personal Access Token Exposed", IssueSeverity.CRITICAL),
    (r'(?i)xox[baprs]-[0-9]{10,13}-[a-zA-Z0-9]{24}', "Slack API Token Detected", IssueSeverity.HIGH),
    (r'(?i)(?:sk_live|rk_live)_[0-9a-zA-Z]{24,34}', "Stripe Live Secret Key Exposed", IssueSeverity.CRITICAL),
    (r'-----BEGIN\s+(?:RSA|OPENSSH|DSA|EC)\s+PRIVATE\s+KEY-----', "Unencrypted Private Key in Source Code", IssueSeverity.CRITICAL),
    (r'(?i)(?:api_key|apikey|secret_key|client_secret)\s*[:=]\s*["\']([a-zA-Z0-9_\-]{16,64})["\']', "Hardcoded API Key or Secret", IssueSeverity.HIGH),
    (r'(?i)(?:password|passwd|pwd)\s*[:=]\s*["\']([^"\']{6,64})["\']', "Hardcoded Password in Plaintext", IssueSeverity.HIGH),
    (r'(?i)postgres(?:ql)?://[a-zA-Z0-9_]+:([^@\s]+)@', "Database Credentials Exposed in Connection URI", IssueSeverity.CRITICAL),
]

class UniversalAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__("universal")

    def analyze(self, code: str, filename: Optional[str] = None) -> List[CodeIssue]:
        issues: List[CodeIssue] = []
        lines = code.splitlines()

        for idx, line in enumerate(lines, 1):
            # 1. Secret detection patterns
            for pattern, title, severity in SECRET_PATTERNS:
                if re.search(pattern, line):
                    issues.append(self.create_issue(
                        rule_id="SEC-UNI-SECRET",
                        title=title,
                        description="Sensitive credentials or cryptographic keys found hardcoded in source files. Hardcoded secrets are easily harvested from version control history.",
                        category=IssueCategory.SECURITY,
                        severity=severity,
                        line_number=idx,
                        code=code,
                        suggestion="Extract secrets to environment variables (e.g., 'os.getenv(...)') or a dedicated secrets manager (Vault, AWS Secrets Manager)."
                    ))

            # 2. Insecure HTTP URLs
            if re.search(r'http://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', line):
                # Exclude localhost, 127.0.0.1, or schemas like http://www.w3.org
                if not re.search(r'http://(localhost|127\.0\.0\.1|0\.0\.0\.0|www\.w3\.org|schemas\.)', line):
                    issues.append(self.create_issue(
                        rule_id="SEC-UNI-HTTP",
                        title="Insecure Plaintext HTTP Protocol",
                        description="Communicating over plaintext 'http://' transmits data without encryption, rendering traffic vulnerable to eavesdropping and man-in-the-middle (MITM) attacks.",
                        category=IssueCategory.SECURITY,
                        severity=IssueSeverity.LOW,
                        line_number=idx,
                        code=code,
                        suggestion="Upgrade protocol to TLS-secured 'https://'."
                    ))

            # 3. Excessive indentation / deep nesting (> 4 levels)
            leading_spaces = len(line) - len(line.lstrip(' '))
            if leading_spaces >= 20 and line.strip():  # 5 indent levels of 4 spaces
                issues.append(self.create_issue(
                    rule_id="STYLE-UNI-NESTING",
                    title="Deep Control Nesting (Indentation > 4 Levels)",
                    description="Excessive nesting impairs readability and increases cognitive complexity (arrow anti-pattern).",
                    category=IssueCategory.CODE_STYLE,
                    severity=IssueSeverity.LOW,
                    line_number=idx,
                    code=code,
                    suggestion="Invert conditional checks and use guard clauses / early returns to flatten control flow."
                ))

            # 4. Unresolved TODO or FIXME items
            if re.search(r'\b(TODO|FIXME|XXX|HACK)\b', line):
                issues.append(self.create_issue(
                    rule_id="STYLE-UNI-TODO",
                    title="Unresolved Debt Marker (TODO / FIXME)",
                    description="Source code contains lingering developer task markers, which indicates unfinished features or unaddressed technical debt.",
                    category=IssueCategory.CODE_STYLE,
                    severity=IssueSeverity.INFO,
                    line_number=idx,
                    code=code,
                    suggestion="Review and resolve technical debt before merging into production."
                ))

        return issues
