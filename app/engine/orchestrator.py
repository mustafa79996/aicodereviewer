import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from app.models import ReviewRequest, ReviewResponse, CodeIssue
from app.engine.analyzers import (
    PythonAnalyzer,
    JavaScriptAnalyzer,
    JavaAnalyzer,
    CppAnalyzer,
    GoAnalyzer,
    SqlAnalyzer,
    UniversalAnalyzer
)
from app.engine.syntax_engine import SyntaxEngine
from app.engine.metrics import compute_code_metrics, compute_quality_score
from app.engine.fixer import generate_heuristic_fix, compute_unified_diff
from app.engine.ai_engine import AIEngine
from app.database import save_review

ANALYZERS_MAP = {
    "python": PythonAnalyzer,
    "py": PythonAnalyzer,
    "javascript": JavaScriptAnalyzer,
    "js": JavaScriptAnalyzer,
    "typescript": JavaScriptAnalyzer,
    "ts": JavaScriptAnalyzer,
    "java": JavaAnalyzer,
    "cpp": CppAnalyzer,
    "c": CppAnalyzer,
    "c++": CppAnalyzer,
    "go": GoAnalyzer,
    "golang": GoAnalyzer,
    "sql": SqlAnalyzer
}

ai_engine = AIEngine()

class ReviewOrchestrator:
    def __init__(self):
        self.syntax_engine = SyntaxEngine()
        self.universal_analyzer = UniversalAnalyzer()

    async def execute_review(self, request: ReviewRequest) -> ReviewResponse:
        start_time = time.perf_counter()
        lang_key = request.language.lower().strip()
        code = request.code

        all_issues: List[CodeIssue] = []

        # 1. Run Comprehensive Multi-Pass Syntax Engine
        syntax_issues = self.syntax_engine.validate(code, lang_key, filename=request.filename)
        all_issues.extend(syntax_issues)

        # 2. Run specific language static analyzer
        analyzer_cls = ANALYZERS_MAP.get(lang_key)
        if analyzer_cls:
            analyzer = analyzer_cls()
            lang_issues = analyzer.analyze(code, filename=request.filename)
            all_issues.extend(lang_issues)

        # 3. Run universal cross-cutting analyzer
        universal_issues = self.universal_analyzer.analyze(code, filename=request.filename)
        all_issues.extend(universal_issues)

        # Deduplicate issues
        seen = set()
        deduped_issues: List[CodeIssue] = []
        for issue in all_issues:
            # Collapse duplicate syntax errors on the exact same line
            if issue.category.value == "Syntax Error":
                key = ("SYNTAX", issue.line_number, issue.title[:15])
            else:
                key = (issue.rule_id, issue.line_number)
            if key not in seen:
                seen.add(key)
                deduped_issues.append(issue)

        # Sort issues: Critical -> High -> Medium -> Low -> Info
        severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
        deduped_issues.sort(key=lambda x: (severity_order.get(x.severity.value, 5), x.line_number or 0))

        # 3. Compute Code Metrics & Health Quality Score
        metrics = compute_code_metrics(code, lang_key)
        quality_score = compute_quality_score(deduped_issues, metrics)

        # 4. AI Deep Semantic Analysis & Insights
        ai_insights: Optional[str] = None
        ai_refactored_code: Optional[str] = None

        if request.run_ai_deep_review:
            ai_insights, ai_refactored_code = await ai_engine.generate_deep_review(
                code=code,
                language=lang_key,
                provider=request.ai_provider or "built-in",
                api_key=request.api_key,
                model_name=request.model_name,
                ollama_url=request.ollama_url
            )

        # 5. Determine corrected code (AI refactored code or heuristic fix)
        if ai_refactored_code and ai_refactored_code.strip() != code.strip():
            corrected_code = ai_refactored_code
        else:
            corrected_code = generate_heuristic_fix(code, lang_key, deduped_issues)

        # 6. Compute Unified Diff
        unified_diff = compute_unified_diff(code, corrected_code, request.filename or "submitted_code")

        # 7. Compute Issue Counts
        counts_by_severity = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
        counts_by_category = {
            "Security": 0,
            "Bug & Logic": 0,
            "Syntax Error": 0,
            "Performance": 0,
            "Code Style & Standards": 0
        }
        for iss in deduped_issues:
            counts_by_severity[iss.severity.value] = counts_by_severity.get(iss.severity.value, 0) + 1
            counts_by_category[iss.category.value] = counts_by_category.get(iss.category.value, 0) + 1

        exec_time = round((time.perf_counter() - start_time) * 1000.0, 2)
        review_id = str(uuid.uuid4())
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        response = ReviewResponse(
            id=review_id,
            timestamp=now_iso,
            language=lang_key,
            filename=request.filename,
            issues=deduped_issues,
            issue_counts_by_severity=counts_by_severity,
            issue_counts_by_category=counts_by_category,
            metrics=metrics,
            quality_score=quality_score,
            original_code=code,
            corrected_code=corrected_code,
            unified_diff=unified_diff,
            ai_insights=ai_insights,
            execution_time_ms=exec_time
        )

        # 8. Persist review into SQLite database (all in D:)
        try:
            save_review(response)
        except Exception as e:
            # Don't let DB failure block review output
            print(f"Failed to persist review: {e}")

        return response
