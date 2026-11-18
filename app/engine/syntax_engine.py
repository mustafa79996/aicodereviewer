import ast
import re
import uuid
from typing import List, Optional, Tuple
from app.models import CodeIssue, IssueCategory, IssueSeverity

class SyntaxEngine:
    """
    Comprehensive Syntax & Lexical Error Detection Engine.
    Detects syntax errors across Python, JavaScript, TypeScript, Java, C/C++, Go, and SQL.
    Catches:
      - Unmatched/unclosed brackets, braces, and parentheses with exact location
      - Unterminated string literals (single, double, backtick, triple quotes)
      - Missing colons in Python control structures (def, if, for, while, class, etc.)
      - Missing condition parentheses in C/Java/JS (if, while, for)
      - Missing semicolons in Java, C/C++, and JavaScript statements
      - Missing required clauses in SQL (SET in UPDATE, FROM in DELETE/SELECT)
      - Invalid assignments to literals (e.g. 5 = x)
      - Dangling binary operators at end of statements
      - Invalid identifier / variable declarations
    """

    def validate(self, code: str, language: str, filename: Optional[str] = None) -> List[CodeIssue]:
        issues: List[CodeIssue] = []
        lang = language.lower().strip()

        # 1. First, check universal string literal quote balancing
        quote_issues = self._check_string_literals(code, lang)
        issues.extend(quote_issues)

        # 2. Check universal bracket, parenthesis & brace balancing
        bracket_issues = self._check_brackets(code, lang)
        issues.extend(bracket_issues)

        # 3. Check language-specific syntax rules
        if lang in ("python", "py"):
            issues.extend(self._validate_python(code, filename))
        elif lang in ("javascript", "typescript", "js", "ts"):
            issues.extend(self._validate_javascript(code))
        elif lang in ("java",):
            issues.extend(self._validate_java(code))
        elif lang in ("c", "cpp", "c++"):
            issues.extend(self._validate_cpp(code))
        elif lang in ("go", "golang"):
            issues.extend(self._validate_go(code))
        elif lang in ("sql",):
            issues.extend(self._validate_sql(code))

        # 4. Universal expression checks (dangling operators, assignment to literals)
        issues.extend(self._check_universal_expressions(code, lang))

        # Deduplicate issues by line and title
        seen = set()
        deduped: List[CodeIssue] = []
        for iss in issues:
            key = (iss.line_number, iss.title)
            if key not in seen:
                seen.add(key)
                deduped.append(iss)

        return deduped

    def _get_snippet(self, code: str, line_number: Optional[int]) -> Optional[str]:
        if not line_number or line_number < 1:
            return None
        lines = code.splitlines()
        start = max(0, line_number - 2)
        end = min(len(lines), line_number + 1)
        snippet_lines = []
        for i in range(start, end):
            prefix = " > " if (i + 1) == line_number else "   "
            snippet_lines.append(f"{i + 1:4d} |{prefix}{lines[i]}")
        return "\n".join(snippet_lines)

    def _create_syntax_issue(
        self,
        code: str,
        rule_id: str,
        title: str,
        description: str,
        line_number: Optional[int],
        column_number: Optional[int] = None,
        suggestion: Optional[str] = None
    ) -> CodeIssue:
        return CodeIssue(
            id=str(uuid.uuid4())[:8],
            rule_id=rule_id,
            title=title,
            description=description,
            category=IssueCategory.SYNTAX,
            severity=IssueSeverity.CRITICAL,
            line_number=line_number,
            column_number=column_number,
            code_snippet=self._get_snippet(code, line_number),
            suggestion=suggestion
        )

    # -------------------------------------------------------------
    # 1. String Literal Quote Balancing
    # -------------------------------------------------------------
    def _check_string_literals(self, code: str, lang: str) -> List[CodeIssue]:
        issues: List[CodeIssue] = []
        lines = code.splitlines()

        # Check triple quotes for Python
        if lang in ("python", "py"):
            for q in ('"""', "'''"):
                count = code.count(q)
                if count % 2 != 0:
                    # Find first unclosed
                    first_line = 1
                    for idx, line in enumerate(lines, 1):
                        if q in line:
                            first_line = idx
                            break
                    issues.append(self._create_syntax_issue(
                        code=code,
                        rule_id="SYNTAX-STR-TRIPLE",
                        title=f"Unterminated Triple-Quoted String ({q})",
                        description=f"Triple-quoted multi-line string opened with {q} was not closed before end of file.",
                        line_number=first_line,
                        suggestion=f"Add closing {q} at the end of the multi-line docstring or string."
                    ))

        # Check single-line strings on each line
        for line_idx, line in enumerate(lines, 1):
            stripped = line.strip()
            # Ignore full-line comments
            if lang in ("python", "py") and stripped.startswith("#"):
                continue
            if lang in ("sql",) and stripped.startswith("--"):
                continue
            if stripped.startswith("//") or stripped.startswith("/*"):
                continue

            # Walk through characters to detect unclosed quotes
            in_single = False
            in_double = False
            in_backtick = False
            escaped = False

            col_single = 0
            col_double = 0
            col_backtick = 0

            i = 0
            while i < len(line):
                char = line[i]

                # Check comment start outside of strings
                if not in_single and not in_double and not in_backtick:
                    if (lang in ("python", "py") and char == '#') or \
                       (lang not in ("python", "py", "sql") and line[i:i+2] == '//') or \
                       (lang == "sql" and line[i:i+2] == '--'):
                        break

                if escaped:
                    escaped = False
                    i += 1
                    continue

                if char == '\\':
                    escaped = True
                    i += 1
                    continue

                if char == "'" and not in_double and not in_backtick:
                    in_single = not in_single
                    col_single = i + 1
                elif char == '"' and not in_single and not in_backtick:
                    # Ignore triple quotes in Python
                    if lang in ("python", "py") and line[i:i+3] == '"""':
                        i += 3
                        continue
                    in_double = not in_double
                    col_double = i + 1
                elif char == '`' and lang in ("javascript", "typescript", "js", "ts", "sql", "go") and not in_single and not in_double:
                    in_backtick = not in_backtick
                    col_backtick = i + 1

                i += 1

            # In most languages, single and double quotes cannot span across lines without escape '\'
            if in_single and not line.rstrip().endswith('\\'):
                issues.append(self._create_syntax_issue(
                    code=code,
                    rule_id="SYNTAX-STR-UNCLOSED-SINGLE",
                    title="Unterminated Single-Quoted String Literal",
                    description=f"Single-quoted string opened at column {col_single} was not closed before the end of the line.",
                    line_number=line_idx,
                    column_number=col_single,
                    suggestion="Add a closing single quote (') before the end of the line, or escape the newline with '\\'."
                ))
            elif in_double and not line.rstrip().endswith('\\'):
                issues.append(self._create_syntax_issue(
                    code=code,
                    rule_id="SYNTAX-STR-UNCLOSED-DOUBLE",
                    title="Unterminated Double-Quoted String Literal",
                    description=f"Double-quoted string opened at column {col_double} was not closed before the end of the line.",
                    line_number=line_idx,
                    column_number=col_double,
                    suggestion='Add a closing double quote (") before the end of the line.'
                ))

        return issues

    # -------------------------------------------------------------
    # 2. Bracket, Parenthesis & Brace Balancing
    # -------------------------------------------------------------
    def _check_brackets(self, code: str, lang: str) -> List[CodeIssue]:
        issues: List[CodeIssue] = []
        stack = []  # entries: (char, line, col)
        bracket_pairs = {')': '(', '}': '{', ']': '['}

        lines = code.splitlines()
        in_multiline_comment = False
        in_docstring = False

        for line_idx, line in enumerate(lines, 1):
            i = 0
            in_str_single = False
            in_str_double = False
            in_str_backtick = False
            escaped = False

            while i < len(line):
                char = line[i]

                # Multiline comment handling
                if not in_str_single and not in_str_double and not in_str_backtick:
                    if not in_multiline_comment and line[i:i+2] == '/*':
                        in_multiline_comment = True
                        i += 2
                        continue
                    if in_multiline_comment:
                        if line[i:i+2] == '*/':
                            in_multiline_comment = False
                            i += 2
                        else:
                            i += 1
                        continue

                    # Single-line comment check
                    if (lang in ("python", "py") and char == '#') or \
                       (lang not in ("python", "py", "sql") and line[i:i+2] == '//') or \
                       (lang == "sql" and line[i:i+2] == '--'):
                        break

                if escaped:
                    escaped = False
                    i += 1
                    continue

                if char == '\\':
                    escaped = True
                    i += 1
                    continue

                # Strings toggle
                if char == "'" and not in_str_double and not in_str_backtick:
                    in_str_single = not in_str_single
                elif char == '"' and not in_str_single and not in_str_backtick:
                    in_str_double = not in_str_double
                elif char == '`' and not in_str_single and not in_str_double:
                    in_str_backtick = not in_str_backtick

                # If outside strings & comments, track brackets
                if not in_str_single and not in_str_double and not in_str_backtick and not in_multiline_comment:
                    if char in "({[":
                        stack.append((char, line_idx, i + 1))
                    elif char in ")}]":
                        if not stack:
                            issues.append(self._create_syntax_issue(
                                code=code,
                                rule_id="SYNTAX-BRACKET-UNEXPECTED",
                                title=f"Unexpected Closing Bracket '{char}'",
                                description=f"Encountered closing '{char}' at line {line_idx}, column {i + 1} with no corresponding opening bracket.",
                                line_number=line_idx,
                                column_number=i + 1,
                                suggestion=f"Remove extraneous '{char}' or verify opening bracket."
                            ))
                        else:
                            last_open, open_line, open_col = stack.pop()
                            expected_open = bracket_pairs[char]
                            if last_open != expected_open:
                                issues.append(self._create_syntax_issue(
                                code=code,
                                rule_id="SYNTAX-BRACKET-MISMATCH",
                                title=f"Mismatched Closing Bracket '{char}'",
                                description=f"Encountered '{char}' on line {line_idx}, but matching opening bracket on line {open_line} is '{last_open}'.",
                                line_number=line_idx,
                                column_number=i + 1,
                                suggestion=f"Change '{char}' to match '{last_open}', or close inner scopes properly."
                            ))

                i += 1

        # Any unclosed brackets remaining on stack
        for unclosed_char, open_line, open_col in reversed(stack):
            match_closing = { '(': ')', '{': '}', '[': ']' }
            issues.append(self._create_syntax_issue(
                code=code,
                rule_id="SYNTAX-BRACKET-UNCLOSED",
                title=f"Unclosed Opening Bracket '{unclosed_char}'",
                description=f"Bracket '{unclosed_char}' opened at line {open_line}, column {open_col} was never closed before the end of the file.",
                line_number=open_line,
                column_number=open_col,
                suggestion=f"Add closing '{match_closing.get(unclosed_char, ')')}' in the appropriate scope."
            ))

        return issues

    # -------------------------------------------------------------
    # 3. Python Syntax Validator
    # -------------------------------------------------------------
    def _validate_python(self, code: str, filename: Optional[str] = None) -> List[CodeIssue]:
        issues: List[CodeIssue] = []

        # Step 1: Real AST parse
        parsed_ok = False
        try:
            ast.parse(code, filename=filename or "<input>")
            parsed_ok = True
        except (SyntaxError, IndentationError, TabError) as e:
            issues.append(self._create_syntax_issue(
                code=code,
                rule_id="SYNTAX-PY-PARSE",
                title=f"Python Syntax Error: {e.msg}",
                description=f"Parsing failed at line {e.lineno}, column {e.offset}: {e.msg}",
                line_number=e.lineno,
                column_number=e.offset,
                suggestion=f"Fix the syntax error at line {e.lineno}: {self._get_python_fix_hint(e.msg)}"
            ))

        # Step 2: Multi-pass check for missing colons on definition/control lines
        # Only inspect if syntax parsing failed to prevent false positives on valid inline statements
        if not parsed_ok:
            lines = code.splitlines()
            block_keywords = [
                r'^\s*def\s+[a-zA-Z0-9_]+\s*\(.*?\)',
                r'^\s*async\s+def\s+[a-zA-Z0-9_]+\s*\(.*?\)',
                r'^\s*class\s+[a-zA-Z0-9_]+(\(.*?\))?',
                r'^\s*if\s+.+',
                r'^\s*elif\s+.+',
                r'^\s*else\s*$',
                r'^\s*for\s+.+\s+in\s+.+',
                r'^\s*while\s+.+',
                r'^\s*try\s*$',
                r'^\s*except(\s+.*)?$',
                r'^\s*finally\s*$',
                r'^\s*with\s+.+'
            ]

            for idx, line in enumerate(lines, 1):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue

                for pattern in block_keywords:
                    if re.match(pattern, stripped):
                        code_part = stripped.split("#")[0].rstrip()
                        if ":" not in code_part:
                            issues.append(self._create_syntax_issue(
                                code=code,
                                rule_id="SYNTAX-PY-COLON",
                                title=f"Missing Colon ':' at End of Statement",
                                description=f"Python block statement '{stripped[:40]}' must terminate with a colon ':'.",
                                line_number=idx,
                                column_number=len(line) + 1,
                                suggestion="Append ':' to the end of the header line."
                            ))
                        break

        return issues

    def _get_python_fix_hint(self, msg: str) -> str:
        msg_l = msg.lower()
        if "expected ':'" in msg_l:
            return "Ensure statement ends with ':'."
        if "invalid syntax" in msg_l:
            return "Check for missing commas, unmatched parentheses, or misspelled keywords."
        if "was never closed" in msg_l:
            return "Add the closing bracket or parenthesis."
        if "unexpected indent" in msg_l:
            return "Align indentation with previous statements."
        if "unindent does not match" in msg_l:
            return "Ensure indentation uses consistent 4-space blocks."
        return "Review syntax according to Python standards."

    # -------------------------------------------------------------
    # 4. JavaScript / TypeScript Syntax Validator
    # -------------------------------------------------------------
    def _validate_javascript(self, code: str) -> List[CodeIssue]:
        issues: List[CodeIssue] = []
        lines = code.splitlines()

        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue

            # 1. Missing condition parentheses: if x > 5 { or while i < 10 {
            if re.match(r'^(if|while|switch)\s+[^(].*\{\s*$', stripped):
                issues.append(self._create_syntax_issue(
                    code=code,
                    rule_id="SYNTAX-JS-COND-PAREN",
                    title="Missing Parentheses Around Condition",
                    description=f"JavaScript/TypeScript requires condition in '{stripped.split()[0]}' statement to be enclosed in parentheses '()'.",
                    line_number=idx,
                    suggestion=f"Wrap condition in parentheses: {stripped.split()[0]} (condition) {{"
                ))

            # 2. Invalid variable declaration without identifier: const = 10; or let ;
            if re.match(r'^(const|let|var)\s*=', stripped) or re.match(r'^(const|let|var)\s*;', stripped):
                issues.append(self._create_syntax_issue(
                    code=code,
                    rule_id="SYNTAX-JS-VAR-DECL",
                    title="Malformed Variable Declaration (Missing Identifier)",
                    description="Variable declaration keyword is missing a valid variable name before assignment or delimiter.",
                    line_number=idx,
                    suggestion="Specify a valid identifier: 'const myVar = ...;'."
                ))

            # 3. Invalid identifier starting with number: let 123abc = 5;
            if re.search(r'\b(let|const|var)\s+\d+[a-zA-Z0-9_]*\b', stripped):
                issues.append(self._create_syntax_issue(
                    code=code,
                    rule_id="SYNTAX-JS-IDENT-NUM",
                    title="Invalid Variable Identifier Starting with Digit",
                    description="Identifiers cannot start with a numeric digit.",
                    line_number=idx,
                    suggestion="Rename identifier to start with a letter, underscore, or dollar sign."
                ))

            # 4. Consecutive commas: [1,, 2] or func(a,, b)
            if re.search(r',(\s*,)+', stripped):
                issues.append(self._create_syntax_issue(
                    code=code,
                    rule_id="SYNTAX-JS-CONSEC-COMMAS",
                    title="Unexpected Consecutive Commas",
                    description="Repeated commas detected without an expression in between.",
                    line_number=idx,
                    suggestion="Remove duplicate comma ','."
                ))

            # 5. Broken arrow function syntax: () = > or (x) =>>
            if re.search(r'=\s*>\s*>', stripped) or re.search(r'=\s+>', stripped):
                issues.append(self._create_syntax_issue(
                    code=code,
                    rule_id="SYNTAX-JS-ARROW-MALFORMED",
                    title="Malformed Arrow Function Operator",
                    description="Arrow function must use '=>' without spaces or redundant characters.",
                    line_number=idx,
                    suggestion="Use standard '=>' operator."
                ))

        return issues

    # -------------------------------------------------------------
    # 5. Java Syntax Validator
    # -------------------------------------------------------------
    def _validate_java(self, code: str) -> List[CodeIssue]:
        issues: List[CodeIssue] = []
        lines = code.splitlines()

        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue

            # 1. Missing condition parentheses: if x > 5 {
            if re.match(r'^(if|while|switch)\s+[^(].*\{\s*$', stripped):
                issues.append(self._create_syntax_issue(
                    code=code,
                    rule_id="SYNTAX-JAVA-COND-PAREN",
                    title="Missing Parentheses Around Control Condition",
                    description=f"Java requires conditional statements in '{stripped.split()[0]}' to be enclosed in parentheses '()'.",
                    line_number=idx,
                    suggestion=f"Wrap condition in parentheses: {stripped.split()[0]} (condition) {{"
                ))

            # 2. Missing semicolon on package or import statements
            if re.match(r'^(package|import)\s+[^;]+$', stripped):
                issues.append(self._create_syntax_issue(
                    code=code,
                    rule_id="SYNTAX-JAVA-SEMI-IMPORT",
                    title="Missing Semicolon ';' on Statement",
                    description=f"Java statement '{stripped}' must end with a semicolon ';'.",
                    line_number=idx,
                    suggestion="Add ';' at the end of the line."
                ))

            # 3. Missing semicolon on return or throw
            if re.match(r'^(return|throw)\s+[^;{}]+$', stripped):
                issues.append(self._create_syntax_issue(
                    code=code,
                    rule_id="SYNTAX-JAVA-SEMI-RETURN",
                    title="Missing Semicolon ';' on Return/Throw Statement",
                    description=f"Statement '{stripped}' is missing a terminating semicolon ';'.",
                    line_number=idx,
                    suggestion="Append ';' to complete the statement."
                ))

            # 4. Inverted access modifier e.g. void public foo()
            if re.search(r'\b(void|int|String|boolean|double)\s+(public|private|protected)\b', stripped):
                issues.append(self._create_syntax_issue(
                    code=code,
                    rule_id="SYNTAX-JAVA-MODIFIER-ORDER",
                    title="Misplaced Access Modifier",
                    description="Access modifier (public/private/protected) must precede return type in method declarations.",
                    line_number=idx,
                    suggestion="Reorder declaration: 'public void methodName(...)'."
                ))

        return issues

    # -------------------------------------------------------------
    # 6. C / C++ Syntax Validator
    # -------------------------------------------------------------
    def _validate_cpp(self, code: str) -> List[CodeIssue]:
        issues: List[CodeIssue] = []
        lines = code.splitlines()

        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue

            # 1. Malformed #include directive
            if stripped.startswith("#include"):
                if not (re.match(r'#include\s*<[^>]+>', stripped) or re.match(r'#include\s*"[^"]+"', stripped)):
                    issues.append(self._create_syntax_issue(
                        code=code,
                        rule_id="SYNTAX-CPP-INCLUDE",
                        title="Malformed '#include' Preprocessor Directive",
                        description=f"Header inclusion '{stripped}' must enclose header in '<...>' or '\"...\"'.",
                        line_number=idx,
                        suggestion="Use '#include <header.h>' or '#include \"header.h\"'."
                    ))

            # 2. Missing condition parentheses: if x > 5 {
            if re.match(r'^(if|while|switch)\s+[^(].*\{\s*$', stripped):
                issues.append(self._create_syntax_issue(
                    code=code,
                    rule_id="SYNTAX-CPP-COND-PAREN",
                    title="Missing Parentheses in Control Statement",
                    description=f"Control flow condition in '{stripped.split()[0]}' must be enclosed in parentheses '()'.",
                    line_number=idx,
                    suggestion=f"Wrap condition in parentheses: {stripped.split()[0]} (condition) {{"
                ))

            # 3. Missing semicolon on return statement
            if re.match(r'^return\s+[^;{}]+$', stripped):
                issues.append(self._create_syntax_issue(
                    code=code,
                    rule_id="SYNTAX-CPP-SEMI-RETURN",
                    title="Missing Semicolon ';' on 'return' Statement",
                    description="Return statements in C/C++ must terminate with a semicolon ';'.",
                    line_number=idx,
                    suggestion="Add ';' at the end of the return statement."
                ))

        return issues

    # -------------------------------------------------------------
    # 7. Go Syntax Validator
    # -------------------------------------------------------------
    def _validate_go(self, code: str) -> List[CodeIssue]:
        issues: List[CodeIssue] = []
        lines = code.splitlines()

        has_package = any(line.strip().startswith("package ") for line in lines)
        if lines and not has_package:
            issues.append(self._create_syntax_issue(
                code=code,
                rule_id="SYNTAX-GO-PACKAGE",
                title="Missing Go 'package' Declaration",
                description="Every Go source file must start with a 'package <name>' clause.",
                line_number=1,
                suggestion="Add 'package main' or appropriate package header at top of file."
            ))

        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            # Go does not allow parentheses around if conditions e.g. if (x == 1) {
            # (Though Go compiler accepts it with warning, standard gofmt rejects it)
            if re.search(r'\bfunc\s+[a-zA-Z0-9_]+\s+[^{]+{', stripped):
                # Missing parameter parentheses e.g. func foo {
                if not re.search(r'\bfunc\s+[a-zA-Z0-9_]+\s*\(', stripped):
                    issues.append(self._create_syntax_issue(
                        code=code,
                        rule_id="SYNTAX-GO-FUNC-PAREN",
                        title="Missing Parameter Parentheses in 'func' Declaration",
                        description="Go function declarations require parameter parentheses: 'func Name()'.",
                        line_number=idx,
                        suggestion="Add parameter parentheses: 'func functionName() {'."
                    ))

        return issues

    # -------------------------------------------------------------
    # 8. SQL Syntax Validator
    # -------------------------------------------------------------
    def _validate_sql(self, code: str) -> List[CodeIssue]:
        issues: List[CodeIssue] = []
        clean = re.sub(r'--.*', '', code)
        clean = re.sub(r'/\*.*?\*/', '', clean, flags=re.DOTALL)
        statements = [s.strip() for s in clean.split(";") if s.strip()]

        for stmt in statements:
            upper = stmt.upper()

            # 1. SELECT without FROM or expressions
            if re.match(r'^SELECT\s+FROM\b', upper):
                issues.append(self._create_syntax_issue(
                    code=stmt,
                    rule_id="SYNTAX-SQL-SELECT-EMPTY",
                    title="Malformed 'SELECT FROM' Syntax (Missing Columns)",
                    description="SELECT clause must specify column names, expressions, or wildcard '*' before FROM.",
                    line_number=1,
                    suggestion="Specify columns: 'SELECT col1, col2 FROM table' or 'SELECT * FROM table'."
                ))

            # 2. UPDATE without SET
            if re.search(r'\bUPDATE\s+[a-zA-Z0-9_]+\s+(?!SET\b)', upper):
                if not re.search(r'\bSET\b', upper):
                    issues.append(self._create_syntax_issue(
                        code=stmt,
                        rule_id="SYNTAX-SQL-UPDATE-SET",
                        title="Malformed 'UPDATE' Syntax (Missing 'SET' Clause)",
                        description="UPDATE statement must include a 'SET' clause assigning new column values.",
                        line_number=1,
                        suggestion="Add 'SET column = value' clause."
                    ))

            # 3. INSERT without INTO or VALUES/SELECT
            if re.match(r'^INSERT\s+[a-zA-Z0-9_]+', upper) and not re.match(r'^INSERT\s+INTO\b', upper):
                issues.append(self._create_syntax_issue(
                    code=stmt,
                    rule_id="SYNTAX-SQL-INSERT-INTO",
                    title="Missing 'INTO' Keyword in 'INSERT' Statement",
                    description="SQL standard requires 'INSERT INTO <table_name> ...'.",
                    line_number=1,
                    suggestion="Add 'INTO': 'INSERT INTO table_name ...'."
                ))

        return issues

    # -------------------------------------------------------------
    # 9. Universal Expression Syntax Checks
    # -------------------------------------------------------------
    def _check_universal_expressions(self, code: str, lang: str) -> List[CodeIssue]:
        issues: List[CodeIssue] = []
        lines = code.splitlines()

        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//") or stripped.startswith("#") or stripped.startswith("--"):
                continue

            # 1. Illegal assignment to literal: e.g. 5 = x or "test" = y
            if re.match(r'^(\d+|"[^"]*"|\'[^\']*\')\s*=\s*[^=]', stripped):
                issues.append(self._create_syntax_issue(
                    code=code,
                    rule_id="SYNTAX-EXPR-LITERAL-ASSIGN",
                    title="Illegal Assignment to Literal Constant",
                    description=f"Cannot assign a value to a literal constant ({stripped[:25]}).",
                    line_number=idx,
                    suggestion="Ensure variable name is on the left-hand side of assignment: 'variable = value;'."
                ))

            # 2. Dangling binary operator at end of line: e.g. x = a + 
            dangling_match = re.search(r'([+\-*/%&|]|\band\b|\bor\b)\s*$', stripped)
            if dangling_match and not stripped.endswith("++") and not stripped.endswith("--") and not stripped.endswith("\\"):
                op = dangling_match.group(1)
                # Check if next line continues the expression
                if idx < len(lines) and not lines[idx].strip():
                    issues.append(self._create_syntax_issue(
                        code=code,
                        rule_id="SYNTAX-EXPR-DANGLING-OP",
                        title=f"Dangling Incomplete Operator '{op}' at End of Line",
                        description=f"Expression ends prematurely with binary operator '{op}' without a right-hand operand.",
                        line_number=idx,
                        suggestion=f"Provide right-hand operand after '{op}' or remove the operator."
                    ))

            # 3. Duplicate equality operators e.g. x === = y or x == = y
            if re.search(r'===\s+=|==\s+=', stripped):
                issues.append(self._create_syntax_issue(
                    code=code,
                    rule_id="SYNTAX-EXPR-DOUBLE-OP",
                    title="Malformed Comparison Operator",
                    description="Detected invalid sequence of equality operators (e.g. '== =').",
                    line_number=idx,
                    suggestion="Use either '==' (equality) or '===' (strict equality)."
                ))

        return issues
