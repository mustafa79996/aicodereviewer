import ast
import math
import re
from typing import Tuple, List, Dict
from app.models import CodeMetrics, QualityScore, CodeIssue, IssueSeverity

def calculate_python_complexity(code: str) -> Tuple[int, int]:
    """Calculates Cyclomatic Complexity and Cognitive Complexity for Python code."""
    try:
        tree = ast.parse(code)
    except Exception:
        # Fallback to regex counting
        return calculate_generic_complexity(code)

    cyclomatic = 1
    cognitive = 0

    class ComplexityVisitor(ast.NodeVisitor):
        def __init__(self):
            self.cc = 1
            self.cog = 0
            self.depth = 0

        def visit_If(self, node: ast.If):
            self.cc += 1
            self.cog += 1 + self.depth
            self.depth += 1
            self.generic_visit(node)
            self.depth -= 1

        def visit_For(self, node: ast.For):
            self.cc += 1
            self.cog += 1 + self.depth
            self.depth += 1
            self.generic_visit(node)
            self.depth -= 1

        def visit_AsyncFor(self, node: ast.AsyncFor):
            self.cc += 1
            self.cog += 1 + self.depth
            self.depth += 1
            self.generic_visit(node)
            self.depth -= 1

        def visit_While(self, node: ast.While):
            self.cc += 1
            self.cog += 1 + self.depth
            self.depth += 1
            self.generic_visit(node)
            self.depth -= 1

        def visit_ExceptHandler(self, node: ast.ExceptHandler):
            self.cc += 1
            self.cog += 1 + self.depth
            self.depth += 1
            self.generic_visit(node)
            self.depth -= 1

        def visit_BoolOp(self, node: ast.BoolOp):
            # and / or expressions
            self.cc += len(node.values) - 1
            self.cog += len(node.values) - 1
            self.generic_visit(node)

        def visit_Assert(self, node: ast.Assert):
            self.cc += 1
            self.generic_visit(node)

    visitor = ComplexityVisitor()
    visitor.visit(tree)
    return visitor.cc, visitor.cog

def calculate_generic_complexity(code: str) -> Tuple[int, int]:
    """Calculates complexity heuristics for non-Python languages."""
    decision_patterns = [
        r'\bif\b', r'\belse\s+if\b', r'\belif\b', r'\bwhile\b', r'\bfor\b',
        r'\bcase\b', r'\bcatch\b', r'&&', r'\|\|', r'\?'
    ]
    cc = 1
    for pat in decision_patterns:
        cc += len(re.findall(pat, code))
    
    # Rough cognitive complexity based on nesting
    cog = 0
    nesting = 0
    for line in code.splitlines():
        trimmed = line.strip()
        nesting += trimmed.count('{') - trimmed.count('}')
        if any(re.search(pat, trimmed) for pat in decision_patterns):
            cog += 1 + max(0, nesting)
            
    return max(1, cc), max(0, cog)

def calculate_halstead_metrics(code: str) -> Tuple[float, float, float]:
    """Returns (volume, difficulty, estimated_bugs)."""
    operators = [
        '+', '-', '*', '/', '%', '=', '==', '!=', '<', '>', '<=', '>=',
        '&&', '||', '!', '&', '|', '^', '~', '<<', '>>', '+=', '-=',
        '*=', '/=', '->', '.', ',', ';', ':', '(', ')', '[', ']', '{', '}'
    ]
    
    tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*|\d+|[^\s\w]', code)
    if not tokens:
        return 0.0, 0.0, 0.0
        
    op_counts: Dict[str, int] = {}
    operand_counts: Dict[str, int] = {}
    
    for t in tokens:
        if t in operators:
            op_counts[t] = op_counts.get(t, 0) + 1
        elif re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$|^\d+$', t):
            operand_counts[t] = operand_counts.get(t, 0) + 1

    n1 = len(op_counts)
    n2 = len(operand_counts)
    N1 = sum(op_counts.values())
    N2 = sum(operand_counts.values())

    vocabulary = n1 + n2
    length = N1 + N2

    if vocabulary <= 1 or length == 0:
        return 0.0, 0.0, 0.0

    volume = length * math.log2(vocabulary)
    difficulty = ((n1 / 2.0) * (N2 / max(1, n2))) if n2 > 0 else 0.0
    estimated_bugs = volume / 3000.0

    return round(volume, 2), round(difficulty, 2), round(estimated_bugs, 3)

def compute_code_metrics(code: str, language: str) -> CodeMetrics:
    lines = code.splitlines()
    sloc = len(lines)
    blank_lines = sum(1 for line in lines if not line.strip())
    
    # Comment detection
    comment_lines = 0
    for line in lines:
        s = line.strip()
        if language in ("python",):
            if s.startswith("#") or s.startswith('"""') or s.startswith("'''"):
                comment_lines += 1
        elif language in ("sql",):
            if s.startswith("--") or s.startswith("/*"):
                comment_lines += 1
        else:
            if s.startswith("//") or s.startswith("/*") or s.startswith("*"):
                comment_lines += 1

    logical_loc = max(0, sloc - blank_lines - comment_lines)
    comment_ratio = round((comment_lines / max(1, sloc)) * 100, 1)

    if language.lower() == "python":
        cc, cog = calculate_python_complexity(code)
    else:
        cc, cog = calculate_generic_complexity(code)

    volume, diff, bugs = calculate_halstead_metrics(code)

    # Maintainability Index (MI)
    if volume > 0 and sloc > 0:
        mi = 171.0 - 5.2 * math.log(max(1.0, volume)) - 0.23 * cc - 16.2 * math.log(max(1.0, sloc))
        # Scale to 0-100 range
        mi_scaled = max(0.0, min(100.0, (mi * 100.0) / 171.0))
    else:
        mi_scaled = 100.0

    return CodeMetrics(
        sloc=sloc,
        logical_loc=logical_loc,
        blank_lines=blank_lines,
        comment_lines=comment_lines,
        comment_ratio=comment_ratio,
        cyclomatic_complexity=cc,
        cognitive_complexity=cog,
        maintainability_index=round(mi_scaled, 1),
        halstead_volume=volume,
        halstead_difficulty=diff,
        estimated_bugs=bugs
    )

def compute_quality_score(issues: List[CodeIssue], metrics: CodeMetrics) -> QualityScore:
    """Computes an overarching quality score (0-100) and letter grade."""
    score = 100.0
    sec_score = 100.0
    rel_score = 100.0
    maint_score = 100.0
    perf_score = 100.0

    critical_count = 0
    high_count = 0
    syntax_error_count = 0

    for issue in issues:
        deduction = 0
        sev = issue.severity.value if hasattr(issue.severity, 'value') else str(issue.severity)
        cat = issue.category.value if hasattr(issue.category, 'value') else str(issue.category)

        if sev == "Critical":
            deduction = 35
            critical_count += 1
        elif sev == "High":
            deduction = 20
            high_count += 1
        elif sev == "Medium":
            deduction = 8
        elif sev == "Low":
            deduction = 3
        elif sev == "Info":
            deduction = 1

        score -= deduction

        if cat == "Security":
            sec_score -= deduction * 1.5
        elif cat in ("Bug & Logic", "Syntax Error"):
            rel_score -= deduction * 1.5
            maint_score -= deduction * 0.6
            if cat == "Syntax Error":
                syntax_error_count += 1
        elif cat == "Performance":
            perf_score -= deduction * 1.5
        elif cat == "Code Style & Standards":
            maint_score -= deduction * 1.2

    # Complexity penalty
    if metrics.cyclomatic_complexity > 25:
        score -= 10
        maint_score -= 15
    elif metrics.cyclomatic_complexity > 12:
        score -= 4
        maint_score -= 6

    # Critical or Syntax Failure Sanity Checks:
    # A program with fatal syntax or runtime crashes cannot have high health or grade
    if syntax_error_count > 0:
        score = min(score, 25.0)
        rel_score = min(rel_score, 10.0)
        maint_score = min(maint_score, 30.0)
        sec_score = min(sec_score, 50.0)
        perf_score = min(perf_score, 50.0)
    elif critical_count > 0:
        score = min(score, 40.0)
        rel_score = min(rel_score, 20.0)
        maint_score = min(maint_score, 50.0)

    final_score = int(max(0, min(100, round(score))))
    final_sec = int(max(0, min(100, round(sec_score))))
    final_rel = int(max(0, min(100, round(rel_score))))
    final_maint = int(max(0, min(100, round(maint_score))))
    final_perf = int(max(0, min(100, round(perf_score))))

    # Grade determination
    if final_score >= 95:
        grade = "A+"
    elif final_score >= 85:
        grade = "A"
    elif final_score >= 75:
        grade = "B"
    elif final_score >= 65:
        grade = "C"
    elif final_score >= 50:
        grade = "D"
    else:
        grade = "F"

    return QualityScore(
        overall_score=final_score,
        grade=grade,
        security_score=final_sec,
        reliability_score=final_rel,
        maintainability_score=final_maint,
        performance_score=final_perf
    )
