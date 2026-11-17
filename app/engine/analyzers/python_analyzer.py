import ast
import builtins
import re
from typing import List, Optional, Dict, Set, Any
from app.models import CodeIssue, IssueCategory, IssueSeverity
from app.engine.analyzers.base import BaseAnalyzer

BUILTIN_SHADOW_NAMES = {"list", "dict", "set", "str", "int", "float", "type", "id", "input", "open", "file", "all", "any", "dir"}
PYTHON_BUILTINS = set(dir(builtins)) | {"__name__", "__file__", "__doc__", "__package__", "__builtins__"}

class SymbolCollector(ast.NodeVisitor):
    """Collects all defined symbols in Python AST (variables, functions, imports, arguments, loop targets)."""
    def __init__(self):
        self.defined: Set[str] = set()

    def visit_Assign(self, node: ast.Assign):
        for target in node.targets:
            self._add_target(target)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        self._add_target(node.target)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign):
        self._add_target(node.target)
        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr):
        self._add_target(node.target)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.defined.add(node.name)
        for arg in node.args.args + node.args.kwonlyargs:
            self.defined.add(arg.arg)
        if node.args.vararg:
            self.defined.add(node.args.vararg.arg)
        if node.args.kwarg:
            self.defined.add(node.args.kwarg.arg)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.defined.add(node.name)
        for arg in node.args.args + node.args.kwonlyargs:
            self.defined.add(arg.arg)
        if node.args.vararg:
            self.defined.add(node.args.vararg.arg)
        if node.args.kwarg:
            self.defined.add(node.args.kwarg.arg)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.defined.add(node.name)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname or alias.name.split('.')[0]
            self.defined.add(name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        for alias in node.names:
            self.defined.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        self._add_target(node.target)
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor):
        self._add_target(node.target)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        if node.name:
            self.defined.add(node.name)
        self.generic_visit(node)

    def visit_With(self, node: ast.With):
        for item in node.items:
            if item.optional_vars:
                self._add_target(item.optional_vars)
        self.generic_visit(node)

    def _add_target(self, target: ast.AST):
        if isinstance(target, ast.Name):
            self.defined.add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._add_target(elt)


class PythonASTVisitor(ast.NodeVisitor):
    def __init__(self, code: str, analyzer: BaseAnalyzer, defined_symbols: Set[str]):
        self.code = code
        self.analyzer = analyzer
        self.issues: List[CodeIssue] = []
        self.lines = code.splitlines()
        self.defined_symbols = defined_symbols
        self.sequence_data: Dict[str, Dict[str, Any]] = {}
        self.reported_undefined_names: Set[str] = set()

    def visit_Expr(self, node: ast.Expr):
        # Detect standalone undefined identifiers like `hi`
        if isinstance(node.value, ast.Name):
            var_name = node.value.id
            if var_name not in self.defined_symbols and var_name not in PYTHON_BUILTINS:
                self.issues.append(self.analyzer.create_issue(
                    rule_id="BUG-PY-UNDEF-IDENT",
                    title=f"Undefined Identifier / NameError '{var_name}'",
                    description=f"Standalone identifier '{var_name}' is referenced but never defined or imported. If executed, Python will crash with 'NameError: name \\'{var_name}\\' is not defined'. If you intended a string literal, wrap in quotes: '\"{var_name}\"'.",
                    category=IssueCategory.BUG_LOGIC,
                    severity=IssueSeverity.CRITICAL,
                    line_number=node.lineno,
                    column_number=node.col_offset,
                    code=self.code,
                    suggestion=f'Define \'{var_name}\', import it, or enclose in quotes if intended as a string: \'"{var_name}"\'.'
                ))
                self.reported_undefined_names.add(var_name)
            else:
                # Bare expression with no side effect
                self.issues.append(self.analyzer.create_issue(
                    rule_id="BUG-PY-BARE-EXPR",
                    title=f"Pointless Statement: Bare Expression '{var_name}'",
                    description=f"Evaluating bare identifier '{var_name}' on line {node.lineno} has no side-effects and is not assigned, printed, or returned.",
                    category=IssueCategory.BUG_LOGIC,
                    severity=IssueSeverity.MEDIUM,
                    line_number=node.lineno,
                    column_number=node.col_offset,
                    code=self.code,
                    suggestion=f"Assign '{var_name}' to a variable, print it, or call a function."
                ))
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        # Catch undefined variable usages when loading
        if isinstance(node.ctx, ast.Load):
            if node.id not in self.defined_symbols and node.id not in PYTHON_BUILTINS:
                if node.id not in self.reported_undefined_names:
                    self.issues.append(self.analyzer.create_issue(
                        rule_id="BUG-PY-UNDEF-VAR",
                        title=f"Undefined Variable '{node.id}' (Runtime NameError)",
                        description=f"Variable '{node.id}' is used before being defined or imported. Running this code will raise 'NameError: name \\'{node.id}\\' is not defined'.",
                        category=IssueCategory.BUG_LOGIC,
                        severity=IssueSeverity.CRITICAL,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        code=self.code,
                        suggestion=f"Define variable '{node.id}' before accessing it, or verify spelling."
                    ))
                    self.reported_undefined_names.add(node.id)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        # Track literal sequence lengths for array bounds checking
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                if isinstance(node.value, (ast.List, ast.Tuple)):
                    elts = node.value.elts
                    first_val = None
                    if elts and isinstance(elts[0], ast.Constant):
                        first_val = elts[0].value
                    self.sequence_data[var_name] = {
                        "length": len(elts),
                        "first_element": first_val,
                        "line": node.lineno
                    }

                # Built-in shadowing in variable assignments
                if var_name in BUILTIN_SHADOW_NAMES:
                    self.issues.append(self.analyzer.create_issue(
                        rule_id="STYLE-PY-005",
                        title=f"Built-in Shadowing: Variable '{var_name}'",
                        description=f"Variable '{var_name}' shadows a built-in Python type or function, which can lead to subtle runtime TypeError bugs.",
                        category=IssueCategory.CODE_STYLE,
                        severity=IssueSeverity.MEDIUM,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        code=self.code,
                        suggestion=f"Rename '{var_name}' to a more descriptive name like '{var_name}_list' or 'item_{var_name}'."
                    ))
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript):
        # Static array out of bounds e.g. names[3] when len(names) == 3
        if isinstance(node.value, ast.Name):
            var_name = node.value.id
            if var_name in self.sequence_data:
                seq_info = self.sequence_data[var_name]
                seq_len = seq_info["length"]
                if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int):
                    idx = node.slice.value
                    if idx >= seq_len or idx < -seq_len:
                        self.issues.append(self.analyzer.create_issue(
                            rule_id="BUG-PY-STATIC-INDEX-ERROR",
                            title=f"Index Out of Bounds on '{var_name}' (IndexError)",
                            description=f"Index {idx} is out of bounds for sequence '{var_name}' of length {seq_len} (valid indices: 0 to {seq_len - 1}). Accessing it will crash with 'IndexError: list index out of range'.",
                            category=IssueCategory.BUG_LOGIC,
                            severity=IssueSeverity.CRITICAL,
                            line_number=node.lineno,
                            column_number=node.col_offset,
                            code=self.code,
                            suggestion=f"Use a valid index between 0 and {seq_len - 1}."
                        ))
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        # Detect index loops: for i in range(start, stop): print(names[i])
        loop_var = node.target.id if isinstance(node.target, ast.Name) else None

        if loop_var and isinstance(node.iter, ast.Call):
            func_name = getattr(node.iter.func, "id", "")
            if func_name == "range":
                range_args = node.iter.args
                start_val = 0
                stop_val = None

                if len(range_args) == 1:
                    if isinstance(range_args[0], ast.Constant) and isinstance(range_args[0].value, int):
                        stop_val = range_args[0].value
                elif len(range_args) >= 2:
                    if isinstance(range_args[0], ast.Constant) and isinstance(range_args[0].value, int):
                        start_val = range_args[0].value
                    if isinstance(range_args[1], ast.Constant) and isinstance(range_args[1].value, int):
                        stop_val = range_args[1].value

                # Search body for sequence subscripts using loop_var
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Subscript):
                        if isinstance(sub.value, ast.Name) and isinstance(sub.slice, ast.Name):
                            seq_name = sub.value.id
                            idx_var = sub.slice.id
                            if idx_var == loop_var and seq_name in self.sequence_data:
                                seq_len = self.sequence_data[seq_name]["length"]
                                first_item = self.sequence_data[seq_name].get("first_element")

                                # Check 1: stop_val exceeds seq_len (Out of bounds crash)
                                if stop_val is not None and stop_val > seq_len:
                                    max_attempted_index = stop_val - 1
                                    self.issues.append(self.analyzer.create_issue(
                                        rule_id="BUG-PY-LOOP-INDEX-ERROR",
                                        title=f"Loop Index Out of Bounds on '{seq_name}' (Runtime IndexError)",
                                        description=f"Loop range({start_val}, {stop_val}) generates index {max_attempted_index}, but '{seq_name}' only has {seq_len} elements (valid indices: 0 to {seq_len - 1}). Accessing '{seq_name}[{loop_var}]' will crash with 'IndexError: list index out of range'.",
                                        category=IssueCategory.BUG_LOGIC,
                                        severity=IssueSeverity.CRITICAL,
                                        line_number=sub.lineno,
                                        column_number=sub.col_offset,
                                        code=self.code,
                                        suggestion=f"Iterate directly over items: 'for item in {seq_name}:' or use 'range(len({seq_name}))'."
                                    ))

                                # Check 2: start_val starts at 1, skipping index 0
                                if start_val == 1 and seq_len > 0:
                                    self.issues.append(self.analyzer.create_issue(
                                        rule_id="BUG-PY-OFF-BY-ONE-START",
                                        title=f"Off-by-One: Loop Range Skips First Element at Index 0",
                                        description=f"Loop begins at index 1 instead of 0, skipping '{seq_name}[0]' ('{first_item or 'first item'}'). In Python, sequences are 0-indexed.",
                                        category=IssueCategory.BUG_LOGIC,
                                        severity=IssueSeverity.HIGH,
                                        line_number=node.lineno,
                                        column_number=node.col_offset,
                                        code=self.code,
                                        suggestion=f"Start loop at index 0: 'range(len({seq_name}))' or iterate directly: 'for item in {seq_name}:'."
                                    ))

        # Check for quadratic string concatenation inside loop
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.AugAssign) and isinstance(stmt.op, ast.Add):
                if isinstance(stmt.target, ast.Name):
                    self.issues.append(self.analyzer.create_issue(
                        rule_id="PERF-PY-002",
                        title=f"Quadratic String/Sequence Accumulation in Loop",
                        description=f"Accumulating to '{stmt.target.id}' using '+=' inside a loop creates temporary copies on each iteration, causing O(N^2) time complexity.",
                        category=IssueCategory.PERFORMANCE,
                        severity=IssueSeverity.MEDIUM,
                        line_number=stmt.lineno,
                        column_number=stmt.col_offset,
                        code=self.code,
                        suggestion="Collect elements into a list and join them afterwards: ''.join(chunks)."
                    ))

        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        # 1. Division by Zero
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                self.issues.append(self.analyzer.create_issue(
                    rule_id="BUG-PY-ZERODIV",
                    title="Division or Modulo by Zero (ZeroDivisionError)",
                    description="Dividing or computing remainder with 0 will immediately raise 'ZeroDivisionError' at runtime.",
                    category=IssueCategory.BUG_LOGIC,
                    severity=IssueSeverity.CRITICAL,
                    line_number=node.lineno,
                    column_number=node.col_offset,
                    code=self.code,
                    suggestion="Add a guard check to ensure divisor is non-zero before performing division."
                ))

        # 2. String + Non-string type error: "text" + 5
        if isinstance(node.op, ast.Add):
            if isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant):
                l_type = type(node.left.value)
                r_type = type(node.right.value)
                if l_type == str and r_type in (int, float, list):
                    self.issues.append(self.analyzer.create_issue(
                        rule_id="BUG-PY-TYPE-CONCAT",
                        title="Incompatible Types in '+' Concatenation (TypeError)",
                        description=f"Cannot concatenate 'str' with '{r_type.__name__}'. In Python, this raises 'TypeError: can only concatenate str to str'.",
                        category=IssueCategory.BUG_LOGIC,
                        severity=IssueSeverity.HIGH,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        code=self.code,
                        suggestion=f"Convert the operand to string: f'{{...}}' or 'str(...) + ...'."
                    ))
                elif l_type in (int, float) and r_type == str:
                    self.issues.append(self.analyzer.create_issue(
                        rule_id="BUG-PY-TYPE-ADD",
                        title="Incompatible Types in '+' Addition (TypeError)",
                        description=f"Cannot add '{l_type.__name__}' and 'str'. Raises 'TypeError: unsupported operand type(s)'.",
                        category=IssueCategory.BUG_LOGIC,
                        severity=IssueSeverity.HIGH,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        code=self.code,
                        suggestion="Convert types explicitly to match either arithmetic addition or string formatting."
                    ))

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            if isinstance(node.func.value, ast.Name):
                func_name = f"{node.func.value.id}.{node.func.attr}"

        # 1. eval / exec detection
        if func_name in ("eval", "exec"):
            self.issues.append(self.analyzer.create_issue(
                rule_id="SEC-PY-001",
                title=f"Dangerous Use of '{func_name}()'",
                description=f"Using '{func_name}()' allows execution of arbitrary code, presenting severe remote code execution (RCE) risks if used with untrusted input.",
                category=IssueCategory.SECURITY,
                severity=IssueSeverity.CRITICAL,
                line_number=node.lineno,
                column_number=node.col_offset,
                code=self.code,
                suggestion="Replace dynamic evaluation with safe alternatives such as 'ast.literal_eval()' for literals or structured parsers."
            ))

        # 2. Command Injection (subprocess with shell=True, os.system)
        if func_name in ("os.system", "os.popen"):
            self.issues.append(self.analyzer.create_issue(
                rule_id="SEC-PY-002",
                title="Command Injection Risk via 'os.system'",
                description="'os.system' spawns a shell process. Unsanitized user inputs could lead to command injection vulnerabilities.",
                category=IssueCategory.SECURITY,
                severity=IssueSeverity.HIGH,
                line_number=node.lineno,
                column_number=node.col_offset,
                code=self.code,
                suggestion="Use 'subprocess.run([cmd, arg1, ...], shell=False)' with an argument list rather than shell execution."
            ))
        elif "subprocess" in func_name:
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    self.issues.append(self.analyzer.create_issue(
                        rule_id="SEC-PY-003",
                        title="Subprocess Executed with 'shell=True'",
                        description="Passing 'shell=True' to subprocess functions executes commands through the system shell, exposing the application to shell injection.",
                        category=IssueCategory.SECURITY,
                        severity=IssueSeverity.HIGH,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        code=self.code,
                        suggestion="Set 'shell=False' and pass arguments as a list of strings."
                    ))

        # 3. Insecure Deserialization (pickle)
        if func_name in ("pickle.loads", "pickle.load", "_pickle.loads", "_pickle.load"):
            self.issues.append(self.analyzer.create_issue(
                rule_id="SEC-PY-004",
                title="Insecure Deserialization via 'pickle'",
                description="Pickle serialization is not secure against erroneous or maliciously constructed data. Untrusted pickle payloads can execute arbitrary code during unpickling.",
                category=IssueCategory.SECURITY,
                severity=IssueSeverity.CRITICAL,
                line_number=node.lineno,
                column_number=node.col_offset,
                code=self.code,
                suggestion="Use safer serialization formats such as JSON ('json.loads'), Protocol Buffers, or cryptographically signed tokens."
            ))

        # 4. Weak Hashing (MD5, SHA1)
        if func_name in ("hashlib.md5", "hashlib.sha1"):
            used_for_sec = True
            for kw in node.keywords:
                if kw.arg == "usedforsecurity" and isinstance(kw.value, ast.Constant) and kw.value.value is False:
                    used_for_sec = False
            if used_for_sec:
                self.issues.append(self.analyzer.create_issue(
                    rule_id="SEC-PY-005",
                    title=f"Weak Cryptographic Hash '{func_name}'",
                    description=f"{func_name} is cryptographically broken and vulnerable to collision attacks. It should not be used for security purposes or password hashing.",
                    category=IssueCategory.SECURITY,
                    severity=IssueSeverity.MEDIUM,
                    line_number=node.lineno,
                    column_number=node.col_offset,
                    code=self.code,
                    suggestion="Upgrade to 'hashlib.sha256()', 'hashlib.sha512()', or specialized password hashers like 'argon2' or 'bcrypt'."
                ))

        # 5. SQL Injection via raw string formatting in execute()
        if func_name.endswith(".execute"):
            if node.args:
                first_arg = node.args[0]
                is_vuln_sql = False
                if isinstance(first_arg, ast.JoinedStr):
                    is_vuln_sql = True
                elif isinstance(first_arg, ast.BinOp) and isinstance(first_arg.op, (ast.Mod, ast.Add)):
                    is_vuln_sql = True
                if is_vuln_sql:
                    self.issues.append(self.analyzer.create_issue(
                        rule_id="SEC-PY-006",
                        title="SQL Injection Vulnerability",
                        description="Direct dynamic string formatting or interpolation detected inside SQL 'execute()' statement. This allows attackers to manipulate SQL queries.",
                        category=IssueCategory.SECURITY,
                        severity=IssueSeverity.CRITICAL,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        code=self.code,
                        suggestion="Use parameterized queries with placeholders (e.g., 'cursor.execute(\"SELECT * FROM users WHERE id = ?\", (user_id,))')."
                    ))

        # 6. open() without context manager
        if func_name == "open" and not getattr(node, "_inside_with", False):
            self.issues.append(self.analyzer.create_issue(
                rule_id="PERF-PY-001",
                title="Unmanaged File Descriptor / Resource Leak",
                description="Opening a file with 'open()' outside of a 'with' statement can cause file descriptor leaks if exceptions occur before explicit close.",
                category=IssueCategory.PERFORMANCE,
                severity=IssueSeverity.MEDIUM,
                line_number=node.lineno,
                column_number=node.col_offset,
                code=self.code,
                suggestion="Use context manager: 'with open(...) as f:' to ensure automatic resource cleanup."
            ))

        self.generic_visit(node)

    def visit_With(self, node: ast.With):
        for item in node.items:
            if isinstance(item.context_expr, ast.Call):
                setattr(item.context_expr, "_inside_with", True)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # 1. Mutable default arguments
        for default in node.args.defaults + node.args.kw_defaults:
            if default and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.issues.append(self.analyzer.create_issue(
                    rule_id="BUG-PY-001",
                    title="Mutable Default Argument",
                    description=f"Function '{node.name}' uses a mutable default argument. Default values are created once at function definition time, leading to state persistence across calls.",
                    category=IssueCategory.BUG_LOGIC,
                    severity=IssueSeverity.HIGH,
                    line_number=default.lineno,
                    column_number=default.col_offset,
                    code=self.code,
                    suggestion="Set default value to 'None' and initialize inside function: 'if arg is None: arg = []'."
                ))

        # 2. Missing docstring for public functions
        if not node.name.startswith("_"):
            docstring = ast.get_docstring(node)
            if not docstring:
                self.issues.append(self.analyzer.create_issue(
                    rule_id="STYLE-PY-001",
                    title=f"Missing Docstring in '{node.name}'",
                    description=f"Public function '{node.name}' lacks a docstring documenting its purpose, parameters, and return values (PEP 257).",
                    category=IssueCategory.CODE_STYLE,
                    severity=IssueSeverity.INFO,
                    line_number=node.lineno,
                    column_number=node.col_offset,
                    code=self.code,
                    suggestion="Add a concise triple-quoted docstring explaining what the function does."
                ))

        # 3. Too many arguments (> 6)
        total_args = len(node.args.args) + len(node.args.kwonlyargs)
        if total_args > 6:
            self.issues.append(self.analyzer.create_issue(
                rule_id="STYLE-PY-002",
                title=f"Too Many Parameters in '{node.name}' ({total_args})",
                description=f"Function '{node.name}' takes {total_args} arguments. Functions with many parameters increase cognitive load and indicate violation of Single Responsibility.",
                category=IssueCategory.CODE_STYLE,
                severity=IssueSeverity.LOW,
                line_number=node.lineno,
                column_number=node.col_offset,
                code=self.code,
                suggestion="Refactor using a configuration dataclass, dictionary, or builder pattern."
            ))

        # 4. Check for unreachable code after return/raise
        terminated = False
        for stmt in node.body:
            if terminated:
                self.issues.append(self.analyzer.create_issue(
                    rule_id="BUG-PY-002",
                    title="Unreachable Code Detected",
                    description="Statements exist after a terminal statement (return/raise), meaning they will never be executed.",
                    category=IssueCategory.BUG_LOGIC,
                    severity=IssueSeverity.MEDIUM,
                    line_number=stmt.lineno,
                    column_number=stmt.col_offset,
                    code=self.code,
                    suggestion="Remove or relocate dead code that follows return or raise statements."
                ))
                break
            if isinstance(stmt, (ast.Return, ast.Raise)):
                terminated = True

        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare):
        # 1. Comparison of literal using 'is'
        for op, comp in zip(node.ops, node.comparators):
            if isinstance(op, (ast.Is, ast.IsNot)):
                if isinstance(comp, ast.Constant) and isinstance(comp.value, (str, int, float)):
                    self.issues.append(self.analyzer.create_issue(
                        rule_id="BUG-PY-003",
                        title="Literal Identity Comparison with 'is'",
                        description="Using 'is' or 'is not' compares object identity in memory rather than value equality. Python does not guarantee identity for string/number literals.",
                        category=IssueCategory.BUG_LOGIC,
                        severity=IssueSeverity.HIGH,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        code=self.code,
                        suggestion="Use '==' or '!=' to compare literal values instead of 'is' or 'is not'."
                    ))
            elif isinstance(op, (ast.Eq, ast.NotEq)):
                # Comparison with None using == instead of 'is'
                if isinstance(comp, ast.Constant) and comp.value is None:
                    self.issues.append(self.analyzer.create_issue(
                        rule_id="STYLE-PY-003",
                        title="Comparison to 'None' using '=='",
                        description="Comparing to 'None' should always be done with 'is' or 'is not' according to PEP 8, rather than equality operators.",
                        category=IssueCategory.CODE_STYLE,
                        severity=IssueSeverity.LOW,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        code=self.code,
                        suggestion="Replace '== None' with 'is None' or '!= None' with 'is not None'."
                    ))

        # 2. Self comparison: x == x
        if isinstance(node.left, ast.Name):
            for op, comp in zip(node.ops, node.comparators):
                if isinstance(comp, ast.Name) and node.left.id == comp.id:
                    self.issues.append(self.analyzer.create_issue(
                        rule_id="BUG-PY-004",
                        title="Tautological Comparison (Self-Comparison)",
                        description=f"Variable '{node.left.id}' is compared against itself. This is always True (or False) and likely represents a typo or logic bug.",
                        category=IssueCategory.BUG_LOGIC,
                        severity=IssueSeverity.HIGH,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        code=self.code,
                        suggestion="Verify the intended comparison variable."
                    ))

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        # 1. Bare except:
        if node.type is None:
            self.issues.append(self.analyzer.create_issue(
                rule_id="BUG-PY-005",
                title="Bare 'except:' Clause",
                description="A bare 'except:' catches all exceptions, including KeyboardInterrupt and SystemExit, making debugging difficult and preventing clean program termination.",
                category=IssueCategory.BUG_LOGIC,
                severity=IssueSeverity.HIGH,
                line_number=node.lineno,
                column_number=node.col_offset,
                code=self.code,
                suggestion="Catch specific exceptions like 'except ValueError:' or at minimum 'except Exception:'."
            ))

        # 2. Empty except block: except: pass
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self.issues.append(self.analyzer.create_issue(
                rule_id="BUG-PY-006",
                title="Silently Swallowed Exception ('except: pass')",
                description="Suppressing errors silently hides bugs, corrupts application state, and complicates troubleshooting.",
                category=IssueCategory.BUG_LOGIC,
                severity=IssueSeverity.HIGH,
                line_number=node.lineno,
                column_number=node.col_offset,
                code=self.code,
                suggestion="Log the error with 'logger.error()' or take remedial corrective action instead of 'pass'."
            ))

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        # Wildcard import: from x import *
        for alias in node.names:
            if alias.name == "*":
                self.issues.append(self.analyzer.create_issue(
                    rule_id="STYLE-PY-004",
                    title="Wildcard Import ('from module import *')",
                    description="Wildcard imports pollute the namespace, mask undefined variables, and make code provenance ambiguous (PEP 8 anti-pattern).",
                    category=IssueCategory.CODE_STYLE,
                    severity=IssueSeverity.LOW,
                    line_number=node.lineno,
                    column_number=node.col_offset,
                    code=self.code,
                    suggestion=f"Explicitly import needed symbols: 'from {node.module or ''} import name1, name2'."
                ))
        self.generic_visit(node)

    def visit_While(self, node: ast.While):
        # Infinite loop: while True: with no break/return/sys.exit
        if isinstance(node.test, ast.Constant) and node.test.value is True:
            has_exit = False
            for subnode in ast.walk(node):
                if isinstance(subnode, (ast.Break, ast.Return, ast.Raise)):
                    has_exit = True
                    break
            if not has_exit:
                self.issues.append(self.analyzer.create_issue(
                    rule_id="BUG-PY-007",
                    title="Potential Infinite Loop",
                    description="'while True:' loop detected without any 'break', 'return', or 'raise' termination statements inside its block.",
                    category=IssueCategory.BUG_LOGIC,
                    severity=IssueSeverity.HIGH,
                    line_number=node.lineno,
                    column_number=node.col_offset,
                    code=self.code,
                    suggestion="Add a proper exit condition or a 'break' statement inside the loop."
                ))
        self.generic_visit(node)


class PythonAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__("python")

    def analyze(self, code: str, filename: Optional[str] = None) -> List[CodeIssue]:
        issues: List[CodeIssue] = []

        # 1. Parse AST to check for Syntax and Indentation Errors
        try:
            tree = ast.parse(code, filename=filename or "<input>")
        except (SyntaxError, IndentationError, TabError) as e:
            issues.append(self.create_issue(
                rule_id="SYNTAX-PY-001",
                title=f"Python Syntax Error: {e.msg}",
                description=f"Parsing failed at line {e.lineno}, column {e.offset}: {e.msg}",
                category=IssueCategory.SYNTAX,
                severity=IssueSeverity.CRITICAL,
                line_number=e.lineno,
                column_number=e.offset,
                code=code,
                suggestion="Fix the syntax error at the indicated position to allow code compilation and execution."
            ))
            return issues

        # 2. Pre-scan symbol table to resolve defined symbols vs undefined variables
        collector = SymbolCollector()
        collector.visit(tree)

        # 3. Walk AST with visitor
        visitor = PythonASTVisitor(code, self, collector.defined)
        visitor.visit(tree)
        issues.extend(visitor.issues)

        # 4. Check line-by-line checks
        lines = code.splitlines()
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                issues.append(self.create_issue(
                    rule_id="STYLE-PY-006",
                    title=f"Line Exceeds Maximum Length ({len(line)} > 120)",
                    description="Line exceeds standard PEP 8 readability recommendations (120 characters).",
                    category=IssueCategory.CODE_STYLE,
                    severity=IssueSeverity.INFO,
                    line_number=i,
                    column_number=120,
                    code=code,
                    suggestion="Break long expressions or imports across multiple lines."
                ))

        return issues
