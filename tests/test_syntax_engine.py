import pytest
from app.engine.syntax_engine import SyntaxEngine

@pytest.fixture
def syntax_engine():
    return SyntaxEngine()

def test_python_missing_colon(syntax_engine):
    code = """
def calculate(a, b)
    if a > b
        return a
    return b
"""
    issues = syntax_engine.validate(code, "python")
    rule_ids = [i.rule_id for i in issues]
    assert "SYNTAX-PY-COLON" in rule_ids
    # Should catch missing colon on line 2 (def) and line 3 (if)
    colon_issues = [i for i in issues if i.rule_id == "SYNTAX-PY-COLON"]
    assert len(colon_issues) >= 2

def test_unclosed_string_literals(syntax_engine):
    code = 'msg = "unclosed double quote string\nval = 10\n'
    issues = syntax_engine.validate(code, "python")
    rule_ids = [i.rule_id for i in issues]
    assert "SYNTAX-STR-UNCLOSED-DOUBLE" in rule_ids

def test_bracket_mismatch_and_unclosed(syntax_engine):
    code = "items = [1, 2, (3, 4];"
    issues = syntax_engine.validate(code, "javascript")
    rule_ids = [i.rule_id for i in issues]
    assert "SYNTAX-BRACKET-MISMATCH" in rule_ids

def test_javascript_missing_condition_parens(syntax_engine):
    code = """
function test(x) {
    if x > 10 {
        return true;
    }
}
"""
    issues = syntax_engine.validate(code, "javascript")
    rule_ids = [i.rule_id for i in issues]
    assert "SYNTAX-JS-COND-PAREN" in rule_ids

def test_java_missing_semicolon(syntax_engine):
    code = """
package com.example.app
import java.util.List

public class App {
    public int run() {
        return 42
    }
}
"""
    issues = syntax_engine.validate(code, "java")
    rule_ids = [i.rule_id for i in issues]
    assert "SYNTAX-JAVA-SEMI-IMPORT" in rule_ids or "SYNTAX-JAVA-SEMI-RETURN" in rule_ids

def test_cpp_malformed_include(syntax_engine):
    code = """
#include <stdio.h
int main() {
    return 0
}
"""
    issues = syntax_engine.validate(code, "cpp")
    rule_ids = [i.rule_id for i in issues]
    assert "SYNTAX-CPP-INCLUDE" in rule_ids or "SYNTAX-CPP-SEMI-RETURN" in rule_ids

def test_sql_malformed_queries(syntax_engine):
    code = """
SELECT FROM users;
UPDATE accounts active = 1;
"""
    issues = syntax_engine.validate(code, "sql")
    rule_ids = [i.rule_id for i in issues]
    assert "SYNTAX-SQL-SELECT-EMPTY" in rule_ids
    assert "SYNTAX-SQL-UPDATE-SET" in rule_ids

def test_illegal_assignment_to_literal(syntax_engine):
    code = "10 = x\n"
    issues = syntax_engine.validate(code, "python")
    rule_ids = [i.rule_id for i in issues]
    assert "SYNTAX-EXPR-LITERAL-ASSIGN" in rule_ids
