import asyncio
import pytest
from app.engine.analyzers.python_analyzer import PythonAnalyzer
from app.engine.orchestrator import ReviewOrchestrator
from app.models import ReviewRequest

def test_user_snippets_catch_bugs_and_penalize_score():
    orchestrator = ReviewOrchestrator()

    # 1. Test "names = ... for i in range(1, 4): print(names[i])"
    code1 = """
names = ["Alice", "Bob", "Charlie"]

for i in range(1, 4):
    print(names[i])
"""
    req1 = ReviewRequest(code=code1, language="python", run_ai_deep_review=False)
    res1 = asyncio.run(orchestrator.execute_review(req1))
    
    # Must catch out-of-bounds error and off-by-one!
    rule_ids1 = [i.rule_id for i in res1.issues]
    assert "BUG-PY-LOOP-INDEX-ERROR" in rule_ids1
    assert "BUG-PY-OFF-BY-ONE-START" in rule_ids1
    # Quality score MUST NOT be 100%!
    assert res1.quality_score.overall_score < 70
    assert res1.quality_score.grade in ("C", "D", "F")
    assert res1.quality_score.reliability_score <= 50

    # 2. Test bare undefined identifier "hi"
    code2 = "hi"
    req2 = ReviewRequest(code=code2, language="python", run_ai_deep_review=False)
    res2 = asyncio.run(orchestrator.execute_review(req2))

    rule_ids2 = [i.rule_id for i in res2.issues]
    assert "BUG-PY-UNDEF-IDENT" in rule_ids2
    # Quality score MUST NOT be 100%!
    assert res2.quality_score.overall_score < 50
    assert res2.quality_score.grade in ("D", "F")
    assert res2.quality_score.reliability_score <= 20

def test_zerodiv_and_type_mismatch():
    orchestrator = ReviewOrchestrator()

    code = "x = 10 / 0\ny = 'text' + 5"
    req = ReviewRequest(code=code, language="python", run_ai_deep_review=False)
    res = asyncio.run(orchestrator.execute_review(req))

    rule_ids = [i.rule_id for i in res.issues]
    assert "BUG-PY-ZERODIV" in rule_ids
    assert "BUG-PY-TYPE-CONCAT" in rule_ids
    assert res.quality_score.overall_score < 50
