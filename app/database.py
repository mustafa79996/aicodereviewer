import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.config import DATABASE_PATH
from app.models import ReviewResponse

def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        language TEXT NOT NULL,
        filename TEXT,
        overall_score INTEGER NOT NULL,
        grade TEXT NOT NULL,
        issues_count INTEGER NOT NULL,
        critical_count INTEGER NOT NULL,
        high_count INTEGER NOT NULL,
        medium_count INTEGER NOT NULL,
        low_count INTEGER NOT NULL,
        info_count INTEGER NOT NULL,
        sloc INTEGER NOT NULL,
        cyclomatic_complexity INTEGER NOT NULL,
        data_json TEXT NOT NULL
    )
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_reviews_timestamp ON reviews(timestamp DESC)
    """)
    conn.commit()
    conn.close()

# Ensure table is initialized on module load
init_db()

def save_review(review: ReviewResponse) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO reviews (
        id, timestamp, language, filename, overall_score, grade,
        issues_count, critical_count, high_count, medium_count, low_count, info_count,
        sloc, cyclomatic_complexity, data_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        review.id,
        review.timestamp,
        review.language,
        review.filename,
        review.quality_score.overall_score,
        review.quality_score.grade,
        len(review.issues),
        review.issue_counts_by_severity.get("Critical", 0),
        review.issue_counts_by_severity.get("High", 0),
        review.issue_counts_by_severity.get("Medium", 0),
        review.issue_counts_by_severity.get("Low", 0),
        review.issue_counts_by_severity.get("Info", 0),
        review.metrics.sloc,
        review.metrics.cyclomatic_complexity,
        review.model_dump_json()
    ))
    conn.commit()
    conn.close()

def get_recent_reviews(limit: int = 30) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, timestamp, language, filename, overall_score, grade,
           issues_count, critical_count, high_count, medium_count, low_count, sloc
    FROM reviews
    ORDER BY timestamp DESC
    LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_review_by_id(review_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT data_json FROM reviews WHERE id = ?", (review_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row["data_json"])
    return None

def delete_review(review_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
    conn.commit()
    affected = cursor.rowcount > 0
    conn.close()
    return affected

def get_analytics_summary() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 
        COUNT(*) as total_reviews,
        COALESCE(AVG(overall_score), 0) as avg_score,
        COALESCE(SUM(issues_count), 0) as total_issues,
        COALESCE(SUM(critical_count), 0) as total_critical,
        COALESCE(SUM(high_count), 0) as total_high,
        COALESCE(SUM(sloc), 0) as total_sloc
    FROM reviews
    """)
    totals = dict(cursor.fetchone())
    
    cursor.execute("""
    SELECT language, COUNT(*) as count 
    FROM reviews 
    GROUP BY language 
    ORDER BY count DESC
    """)
    languages = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return {
        "totals": totals,
        "languages": languages
    }
