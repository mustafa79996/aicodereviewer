import os
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json

from app.config import APP_TITLE, APP_VERSION, BASE_DIR
from app.models import ReviewRequest, ReviewResponse
from app.database import (
    init_db,
    get_recent_reviews,
    get_review_by_id,
    delete_review,
    get_analytics_summary
)
from app.engine.orchestrator import ReviewOrchestrator

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

# Initialize FastAPI application
app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description="Automated AI Code Review & Bug Detection System combining Static Code Analysis with AI / LLM Intelligence.",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files
static_dir = BASE_DIR / "app" / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

orchestrator = ReviewOrchestrator()



@app.get("/", response_class=HTMLResponse)
async def serve_index():
    template_path = BASE_DIR / "app" / "templates" / "index.html"
    if template_path.exists():
        return HTMLResponse(content=template_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>AI Code Reviewer</h1><p>UI template loading...</p>")

@app.post("/api/review", response_model=ReviewResponse)
async def analyze_code(request: ReviewRequest):
    if not request.code or not request.code.strip():
        raise HTTPException(status_code=400, detail="Source code cannot be empty.")
    try:
        response = await orchestrator.execute_review(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review execution failed: {str(e)}")

@app.post("/api/upload", response_model=ReviewResponse)
async def upload_code_file(
    file: UploadFile = File(...),
    ai_provider: str = Form("built-in"),
    api_key: Optional[str] = Form(None),
    model_name: Optional[str] = Form(None),
    ollama_url: Optional[str] = Form("http://localhost:11434")
):
    try:
        content_bytes = await file.read()
        code_text = content_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unable to read file: {str(e)}")

    filename = file.filename or "uploaded_code.txt"
    ext = Path(filename).suffix.lower()

    # Detect language from extension
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "javascript",
        ".jsx": "javascript",
        ".tsx": "javascript",
        ".java": "java",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".c": "cpp",
        ".h": "cpp",
        ".hpp": "cpp",
        ".go": "go",
        ".sql": "sql"
    }
    language = ext_map.get(ext, "universal")

    request = ReviewRequest(
        code=code_text,
        language=language,
        filename=filename,
        ai_provider=ai_provider,
        api_key=api_key,
        model_name=model_name,
        ollama_url=ollama_url,
        run_ai_deep_review=True
    )

    return await orchestrator.execute_review(request)

@app.get("/api/samples")
def get_sample_codes():
    samples_file = BASE_DIR / "app" / "static" / "samples" / "samples.json"
    if samples_file.exists():
        return json.loads(samples_file.read_text(encoding="utf-8"))
    return {}

@app.get("/api/history")
def get_history(limit: int = 30):
    return get_recent_reviews(limit=limit)

@app.get("/api/history/{review_id}")
def get_review_detail(review_id: str):
    review = get_review_by_id(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")
    return review

@app.delete("/api/history/{review_id}")
def delete_review_endpoint(review_id: str):
    success = delete_review(review_id)
    if not success:
        raise HTTPException(status_code=404, detail="Review not found or could not be deleted.")
    return {"status": "deleted", "id": review_id}

@app.get("/api/analytics")
def get_analytics():
    return get_analytics_summary()

@app.get("/api/export/{review_id}/markdown", response_class=PlainTextResponse)
def export_markdown_report(review_id: str):
    review = get_review_by_id(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review record not found.")

    q = review.get("quality_score", {})
    m = review.get("metrics", {})
    issues = review.get("issues", [])

    md = []
    md.append(f"# 🛡️ AI Code Review Audit Report")
    md.append(f"**Date:** {review.get('timestamp')} | **File:** `{review.get('filename')}` | **Language:** {review.get('language')}\n")
    md.append(f"## 📊 Executive Summary")
    md.append(f"- **Overall Code Quality Grade:** **{q.get('grade')}** ({q.get('overall_score')}/100)")
    md.append(f"- **Security Score:** {q.get('security_score')}/100")
    md.append(f"- **Reliability Score:** {q.get('reliability_score')}/100")
    md.append(f"- **Maintainability Score:** {q.get('maintainability_score')}/100")
    md.append(f"- **Total Issues Identified:** {len(issues)}")
    md.append(f"- **Cyclomatic Complexity:** {m.get('cyclomatic_complexity')}")
    md.append(f"- **Maintainability Index:** {m.get('maintainability_index')}/100\n")

    md.append(f"## 🔍 Detected Issues List\n")
    if not issues:
        md.append("✅ No bugs or security issues detected! Outstanding job.\n")
    else:
        for idx, iss in enumerate(issues, 1):
            md.append(f"### {idx}. [{iss.get('severity')}] {iss.get('title')}")
            md.append(f"- **Category:** {iss.get('category')}")
            if iss.get('line_number'):
                md.append(f"- **Location:** Line {iss.get('line_number')}")
            md.append(f"- **Explanation:** {iss.get('description')}")
            if iss.get('suggestion'):
                md.append(f"- **Recommendation:** {iss.get('suggestion')}")
            if iss.get('code_snippet'):
                md.append(f"\n```\n{iss.get('code_snippet')}\n```\n")

    if review.get("ai_insights"):
        md.append(f"\n## 🧠 AI Deep Semantic Insights")
        md.append(review.get("ai_insights"))

    md.append(f"\n## 📝 Unified Patch / Corrected Diff")
    md.append(f"```diff\n{review.get('unified_diff', '')}\n```\n")

    return "\n".join(md)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": APP_TITLE, "version": APP_VERSION}
