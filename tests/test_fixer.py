from app.engine.fixer import generate_heuristic_fix, compute_unified_diff

def test_python_heuristic_fix():
    buggy_code = """
def calc(x=[]):
    if x == None:
        pass
    try:
        y = 1
    except:
        pass
"""
    fixed = generate_heuristic_fix(buggy_code, "python", [])
    assert "x=None" in fixed
    assert "is None" in fixed
    assert "except Exception:" in fixed or "except Exception as err:" in fixed

def test_unified_diff():
    orig = "a = 1\nb = 2\n"
    corr = "a = 1\nb = 3\n"
    diff = compute_unified_diff(orig, corr, "test.py")
    assert "-b = 2" in diff
    assert "+b = 3" in diff
