import re
from typing import List, Optional
from app.models import CodeIssue, IssueCategory, IssueSeverity
from app.engine.analyzers.base import BaseAnalyzer

UNSAFE_C_FUNCS = {
    "gets": ("CRITICAL", "gets() performs no bounds checking and is fundamentally vulnerable to buffer overflow. Removed from C11/C++14."),
    "strcpy": ("HIGH", "strcpy() does not check destination buffer size, leading to buffer overflows."),
    "strcat": ("HIGH", "strcat() can easily overflow destination buffer if source string exceeds remaining space."),
    "sprintf": ("HIGH", "sprintf() does not enforce buffer boundaries; can lead to arbitrary memory corruption."),
    "vsprintf": ("HIGH", "vsprintf() lacks destination buffer length check.")
}

class CppAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__("cpp")

    def analyze(self, code: str, filename: Optional[str] = None) -> List[CodeIssue]:
        issues: List[CodeIssue] = []
        lines = code.splitlines()

        malloc_count = 0
        free_count = 0
        new_count = 0
        delete_count = 0

        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*"):
                continue

            # 1. Unsafe C legacy functions
            for func, (sev, desc) in UNSAFE_C_FUNCS.items():
                if re.search(rf"\b{func}\s*\(", line):
                    severity = IssueSeverity.CRITICAL if sev == "CRITICAL" else IssueSeverity.HIGH
                    safe_alt = "fgets" if func == "gets" else f"{func}n_s" if func in ("strcpy", "strcat") else "snprintf"
                    issues.append(self.create_issue(
                        rule_id=f"SEC-CPP-{func.upper()}",
                        title=f"Unsafe C Function '{func}()'",
                        description=desc,
                        category=IssueCategory.SECURITY,
                        severity=severity,
                        line_number=idx,
                        code=code,
                        suggestion=f"Replace '{func}()' with safer alternatives like '{safe_alt}()' or C++ 'std::string'."
                    ))

            # 2. Format string vulnerability: printf(user_input) without "%s"
            if re.search(r'\b(printf|fprintf)\s*\(\s*[a-zA-Z0-9_]+\s*\)', line):
                issues.append(self.create_issue(
                    rule_id="SEC-CPP-FMT",
                    title="Potential Format String Vulnerability in 'printf'",
                    description="Passing a non-literal variable directly as the format string allows attackers to read or write arbitrary process memory via '%x' and '%n' specifiers.",
                    category=IssueCategory.SECURITY,
                    severity=IssueSeverity.CRITICAL,
                    line_number=idx,
                    code=code,
                    suggestion='Use a format specifier: printf("%s", variable);'
                ))

            # Count allocations and deallocations for memory leak heuristic
            if re.search(r'\b(malloc|calloc)\s*\(', line):
                malloc_count += 1
            if re.search(r'\bfree\s*\(', line):
                free_count += 1
            if re.search(r'\bnew\s+[a-zA-Z0-9_]+', line):
                new_count += 1
            if re.search(r'\bdelete(\[\])?\s+', line):
                delete_count += 1

            # 3. Raw pointer allocation in modern C++
            if re.search(r'[a-zA-Z0-9_]+\s*\*\s*[a-zA-Z0-9_]+\s*=\s*new\s+', line):
                issues.append(self.create_issue(
                    rule_id="PERF-CPP-SMARTPTR",
                    title="Raw Pointer Allocation ('new') in Modern C++",
                    description="Manual memory management with raw pointers is error-prone and risks memory leaks or dangling pointers.",
                    category=IssueCategory.PERFORMANCE,
                    severity=IssueSeverity.LOW,
                    line_number=idx,
                    code=code,
                    suggestion="Use RAII smart pointers: 'std::unique_ptr' or 'std::make_unique<T>()'."
                ))

        # Memory leak heuristic checks
        if malloc_count > free_count:
            issues.append(self.create_issue(
                rule_id="PERF-CPP-LEAK-MALLOC",
                title=f"Potential Memory Leak: {malloc_count} malloc() vs {free_count} free()",
                description="The number of malloc/calloc allocations exceeds the number of free() deallocations, indicating potential memory leaks.",
                category=IssueCategory.PERFORMANCE,
                severity=IssueSeverity.HIGH,
                line_number=None,
                code=code,
                suggestion="Ensure every allocated block is freed along all control paths, or adopt smart pointers / RAII wrappers."
            ))

        if new_count > delete_count:
            issues.append(self.create_issue(
                rule_id="PERF-CPP-LEAK-NEW",
                title=f"Potential Memory Leak: {new_count} new vs {delete_count} delete",
                description="Dynamic 'new' statements exceed 'delete' statements in this source file.",
                category=IssueCategory.PERFORMANCE,
                severity=IssueSeverity.HIGH,
                line_number=None,
                code=code,
                suggestion="Verify that every dynamically allocated object is destroyed with 'delete' or 'delete[]'."
            ))

        return issues
