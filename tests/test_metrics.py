from app.engine.metrics import compute_code_metrics, compute_quality_score
from app.models import CodeIssue, IssueCategory, IssueSeverity

def test_metrics_calculation():
    code = """
def sample_func(a, b):
    # Sample comment line
    if a > b:
        return a
    else:
        for i in range(10):
            if i == b:
                return i
    return b
"""
    metrics = compute_code_metrics(code, "python")
    assert metrics.sloc > 5
    assert metrics.cyclomatic_complexity >= 3
    assert metrics.maintainability_index > 0
    assert metrics.blank_lines >= 0

def test_quality_score_computation():
    code = "def simple(): return 1"
    metrics = compute_code_metrics(code, "python")
    
    # Perfect score with 0 issues
    perfect_score = compute_quality_score([], metrics)
    assert perfect_score.overall_score == 100
    assert perfect_score.grade == "A+"

    # Critical issue degrades score
    issues = [
        CodeIssue(
            id="1",
            rule_id="SEC-01",
            title="Critical SQLi",
            description="desc",
            category=IssueCategory.SECURITY,
            severity=IssueSeverity.CRITICAL
        ),
        CodeIssue(
            id="2",
            rule_id="BUG-01",
            title="High Bug",
            description="desc",
            category=IssueCategory.BUG_LOGIC,
            severity=IssueSeverity.HIGH
        )
    ]
    degraded = compute_quality_score(issues, metrics)
    assert degraded.overall_score < 70
    assert degraded.grade in ("C", "D", "F")
