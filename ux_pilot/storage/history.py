"""SQLite history — save and query past runs locally."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


def _db_path() -> Path:
    """Get the history database path (~/.ux-pilot/history.db)."""
    path = Path.home() / ".ux-pilot"
    path.mkdir(parents=True, exist_ok=True)
    return path / "history.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            persona_name TEXT NOT NULL,
            target_url TEXT NOT NULL,
            task_description TEXT NOT NULL,
            task_completed INTEGER NOT NULL DEFAULT 0,
            satisfaction_score INTEGER DEFAULT 0,
            summary TEXT DEFAULT '',
            failure_reason TEXT,
            total_steps INTEGER DEFAULT 0,
            total_duration_seconds REAL DEFAULT 0.0,
            frustration_level REAL DEFAULT 0.0,
            cost_usd REAL DEFAULT 0.0,
            emotion_journey TEXT DEFAULT '[]',
            friction_points TEXT DEFAULT '[]',
            recommendations TEXT DEFAULT '[]',
            full_result TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def save_run(result: Any) -> int:
    """Save a RunResult to history. Returns the row ID."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            """INSERT INTO runs (
                persona_name, target_url, task_description, task_completed,
                satisfaction_score, summary, failure_reason,
                total_steps, total_duration_seconds, frustration_level,
                cost_usd, emotion_journey, friction_points, recommendations,
                full_result, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.persona_name,
                result.target_url,
                result.task_description,
                int(result.task_completed),
                result.satisfaction_score,
                result.summary,
                result.failure_reason,
                result.total_steps,
                result.total_duration_seconds,
                result.frustration_level,
                result.cost.estimated_cost_usd,
                json.dumps(result.emotion_journey),
                json.dumps(result.friction_points),
                json.dumps([r.to_dict() for r in result.recommendations]),
                json.dumps(result.to_dict()),
                result.started_at.isoformat(),
            ),
        )
        conn.commit()
        return cursor.lastrowid or 0
    finally:
        conn.close()


def list_runs(limit: int = 20) -> list[dict]:
    """List recent runs from history."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT id, persona_name, target_url, task_description, task_completed, "
            "satisfaction_score, total_steps, total_duration_seconds, frustration_level, "
            "cost_usd, created_at FROM runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_run(run_id: int) -> dict | None:
    """Get a specific run by ID with full details."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row:
            result = dict(row)
            result["emotion_journey"] = json.loads(result["emotion_journey"])
            result["friction_points"] = json.loads(result["friction_points"])
            result["recommendations"] = json.loads(result["recommendations"])
            result["full_result"] = json.loads(result["full_result"])
            return result
        return None
    finally:
        conn.close()
