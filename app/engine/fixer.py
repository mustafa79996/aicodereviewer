import difflib
import re
from typing import List
from app.models import CodeIssue

def generate_heuristic_fix(code: str, language: str, issues: List[CodeIssue]) -> str:
    """Generates an automatically corrected and cleaned version of code based on detected issues."""
    fixed = code
    lang = language.lower()

    if lang in ("python", "py"):
        # 1. Fix == None and != None
        fixed = re.sub(r'==\s*None\b', 'is None', fixed)
        fixed = re.sub(r'!=\s*None\b', 'is not None', fixed)

        # 2. Fix bare except:
        fixed = re.sub(r'except\s*:', 'except Exception:', fixed)

        # 3. Fix except: pass
        fixed = re.sub(
            r'except\s+Exception:\s*\n\s*pass',
            'except Exception as err:\n        # Handle or log exception safely\n        print(f"Error encountered: {err}")',
            fixed
        )

        # 4. Fix eval -> ast.literal_eval if safe
        if "eval(" in fixed and "ast.literal_eval" not in fixed:
            if "import ast" not in fixed:
                fixed = "import ast\n" + fixed
            fixed = re.sub(r'\beval\s*\(', 'ast.literal_eval(', fixed)

        # 5. Fix mutable default arguments in def foo(a=[]): -> def foo(a=None):
        fixed = re.sub(r'(\bdef\s+[a-zA-Z0-9_]+\s*\([^)]*?)([a-zA-Z0-9_]+)\s*=\s*\[\]([^)]*\):)', r'\1\2=None\3', fixed)
        fixed = re.sub(r'(\bdef\s+[a-zA-Z0-9_]+\s*\([^)]*?)([a-zA-Z0-9_]+)\s*=\s*\{\}([^)]*\):)', r'\1\2=None\3', fixed)

        # 6. Fix tautological comparisons x == x
        fixed = re.sub(r'([a-zA-Z0-9_]+)\s*==\s*\1\b', 'True', fixed)

    elif lang in ("javascript", "typescript", "js", "ts"):
        # 1. Fix loose equality
        fixed = re.sub(r'([^!=])==([^=])', r'\1===\2', fixed)
        fixed = re.sub(r'!=([^=])', r'!==\1', fixed)

        # 2. Fix var -> let / const
        fixed = re.sub(r'\bvar\s+([a-zA-Z0-9_$]+)', r'let \1', fixed)

        # 3. Fix empty catch
        fixed = re.sub(r'catch\s*\(([a-zA-Z0-9_$]+)\)\s*\{\s*\}', r'catch (\1) {\n    console.error("Encountered error:", \1);\n}', fixed)

        # 4. Fix innerHTML -> textContent when safe
        fixed = re.sub(r'\.innerHTML\s*=\s*', '.textContent = ', fixed)

    elif lang in ("java",):
        # 1. Fix var.equals("literal") -> "literal".equals(var)
        fixed = re.sub(r'([a-zA-Z0-9_]+)\.equals\(\s*"([^"]+)"\s*\)', r'"\2".equals(\1)', fixed)

        # 2. Fix empty catch
        fixed = re.sub(r'catch\s*\(([a-zA-Z0-9_]+)\s+([a-zA-Z0-9_]+)\)\s*\{\s*\}', r'catch (\1 \2) {\n        System.err.println("Exception: " + \2.getMessage());\n    }', fixed)

    elif lang in ("c", "cpp"):
        # 1. Fix gets -> fgets
        fixed = re.sub(r'\bgets\s*\(\s*([a-zA-Z0-9_]+)\s*\)', r'fgets(\1, sizeof(\1), stdin)', fixed)

        # 2. Fix printf(var) -> printf("%s", var)
        fixed = re.sub(r'\bprintf\s*\(\s*([a-zA-Z0-9_]+)\s*\)', r'printf("%s", \1)', fixed)

    elif lang in ("sql",):
        # Fix SELECT * with advisory comment
        fixed = re.sub(r'\bSELECT\s+\*\s+FROM\b', 'SELECT /* TODO: Replace * with specific columns */ * FROM', fixed, flags=re.IGNORECASE)

    return fixed

def compute_unified_diff(original: str, corrected: str, filename: str = "code") -> str:
    """Computes a unified diff between original code and corrected code."""
    orig_lines = original.splitlines(keepends=True)
    corr_lines = corrected.splitlines(keepends=True)
    
    # Ensure all lines end with newline for clean diff headers
    orig_lines = [l if l.endswith('\n') else l + '\n' for l in orig_lines]
    corr_lines = [l if l.endswith('\n') else l + '\n' for l in corr_lines]
    
    diff = difflib.unified_diff(
        orig_lines,
        corr_lines,
        fromfile=f"a/{filename} (original)",
        tofile=f"b/{filename} (corrected)",
        lineterm="\n"
    )
    return "".join(diff)
