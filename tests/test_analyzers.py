import pytest
from app.engine.analyzers.python_analyzer import PythonAnalyzer
from app.engine.analyzers.javascript_analyzer import JavaScriptAnalyzer
from app.engine.analyzers.java_analyzer import JavaAnalyzer
from app.engine.analyzers.cpp_analyzer import CppAnalyzer
from app.engine.analyzers.go_analyzer import GoAnalyzer
from app.engine.analyzers.sql_analyzer import SqlAnalyzer
from app.engine.analyzers.universal_analyzer import UniversalAnalyzer

def test_python_analyzer_detects_bugs_and_security():
    code = """
import os

def test_func(cache=[]):
    x = eval("1 + 1")
    os.system("echo hello")
    f = open("file.txt", "w")
    if x == None:
        pass
    list = [1, 2, 3]
"""
    analyzer = PythonAnalyzer()
    issues = analyzer.analyze(code)
    rule_ids = [i.rule_id for i in issues]

    assert "SEC-PY-001" in rule_ids  # eval
    assert "SEC-PY-002" in rule_ids  # os.system
    assert "BUG-PY-001" in rule_ids  # mutable default
    assert "PERF-PY-001" in rule_ids # unclosed open
    assert "STYLE-PY-003" in rule_ids # == None
    assert "STYLE-PY-005" in rule_ids # list shadowing

def test_python_syntax_error():
    code = "def broken_code(:\n    return 1"
    analyzer = PythonAnalyzer()
    issues = analyzer.analyze(code)
    assert any(i.category.value == "Syntax Error" for i in issues)

def test_javascript_analyzer():
    code = """
var key = "test";
function render(data) {
    document.getElementById("box").innerHTML = data.input;
    if (data.role == "admin") {
        eval(data.script);
    }
    try {
        JSON.parse(data);
    } catch (e) {}
}
"""
    analyzer = JavaScriptAnalyzer()
    issues = analyzer.analyze(code)
    rule_ids = [i.rule_id for i in issues]

    assert "SEC-JS-001" in rule_ids  # eval
    assert "SEC-JS-002" in rule_ids  # innerHTML
    assert "STYLE-JS-001" in rule_ids # loose ==
    assert "STYLE-JS-002" in rule_ids # var
    assert "BUG-JS-001" in rule_ids  # empty catch

def test_java_analyzer():
    code = """
public class Test {
    public void run(String str, Connection conn) throws Exception {
        if (str == "admin") {}
        if (str.equals("root")) {}
        Statement stmt = conn.createStatement();
        stmt.executeQuery("SELECT * FROM users WHERE name = '" + str + "'");
        try {} catch (Exception e) {}
    }
}
"""
    analyzer = JavaAnalyzer()
    issues = analyzer.analyze(code)
    rule_ids = [i.rule_id for i in issues]

    assert "BUG-JAVA-001" in rule_ids # == comparison
    assert "BUG-JAVA-002" in rule_ids # null pointer in equals
    assert "SEC-JAVA-001" in rule_ids # SQLi concatenation
    assert "BUG-JAVA-003" in rule_ids # empty catch

def test_cpp_analyzer():
    code = """
void test() {
    char buf[10];
    gets(buf);
    strcpy(buf, "hello");
    printf(buf);
    char *p = (char *)malloc(100);
}
"""
    analyzer = CppAnalyzer()
    issues = analyzer.analyze(code)
    rule_ids = [i.rule_id for i in issues]

    assert "SEC-CPP-GETS" in rule_ids
    assert "SEC-CPP-STRCPY" in rule_ids
    assert "SEC-CPP-FMT" in rule_ids
    assert "PERF-CPP-LEAK-MALLOC" in rule_ids

def test_go_analyzer():
    code = """
package main
func run() {
    _, _ = doSomething()
    go func() {
        for {}
    }()
}
"""
    analyzer = GoAnalyzer()
    issues = analyzer.analyze(code)
    rule_ids = [i.rule_id for i in issues]

    assert "BUG-GO-001" in rule_ids
    assert "PERF-GO-001" in rule_ids

def test_sql_analyzer():
    code = """
DELETE FROM customers;
UPDATE accounts SET active = 0;
SELECT * FROM logs;
"""
    analyzer = SqlAnalyzer()
    issues = analyzer.analyze(code)
    rule_ids = [i.rule_id for i in issues]

    assert "BUG-SQL-001" in rule_ids # DELETE without WHERE
    assert "BUG-SQL-002" in rule_ids # UPDATE without WHERE
    assert "PERF-SQL-001" in rule_ids # SELECT *

def test_universal_analyzer_secrets():
    code = """
api_key = "secret_key_sample_token_123456"
PASSWORD = "supersecretpassword123"
URL = "http://api.external-service.com/data"
"""
    analyzer = UniversalAnalyzer()
    issues = analyzer.analyze(code)
    rule_ids = [i.rule_id for i in issues]

    assert "SEC-UNI-SECRET" in rule_ids
    assert "SEC-UNI-HTTP" in rule_ids
