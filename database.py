"""
SQLite persistence for GMC scan results.
Database file: /data/scans.db (mounted volume, survives rebuilds)
Fallback: /tmp/scans.db (for local dev without volume)
"""
import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", "/data/scans.db"))


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                domain      TEXT NOT NULL,
                url         TEXT NOT NULL,
                scanned_at  TEXT NOT NULL,
                score_pct   REAL,
                passed      INTEGER DEFAULT 0,
                failed      INTEGER DEFAULT 0,
                warnings    INTEGER DEFAULT 0,
                result_json TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_domain ON scans(domain)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_scanned_at ON scans(scanned_at)")
        conn.commit()


def save_scan(url: str, score: dict, result: dict) -> int:
    """Persist a completed scan. Returns the new row id."""
    domain = url.replace("https://", "").replace("http://", "").split("/")[0].lstrip("www.")
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        with get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO scans (domain, url, scanned_at, score_pct, passed, failed, warnings, result_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    domain,
                    url,
                    now,
                    score.get("score_pct", 0),
                    score.get("passed", 0),
                    score.get("failed", 0),
                    score.get("warnings", 0),
                    json.dumps(result),
                ),
            )
            conn.commit()
            return cur.lastrowid
    except Exception as e:
        print(f"[DB] save_scan failed: {e}")
        return -1


def get_recent_scans(limit: int = 20) -> list[dict]:
    """Return the most recent scans, newest first."""
    try:
        with get_conn() as conn:
            rows = conn.execute(
                """SELECT id, domain, url, scanned_at, score_pct, passed, failed, warnings
                   FROM scans ORDER BY id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def get_scan_by_id(scan_id: int) -> dict | None:
    """Return full scan result by id."""
    try:
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
            if row:
                d = dict(row)
                d["result"] = json.loads(d.pop("result_json", "{}") or "{}")
                return d
    except Exception:
        pass
    return None


def get_scans_for_domain(domain: str, limit: int = 10) -> list[dict]:
    """Return scan history for a specific domain."""
    try:
        with get_conn() as conn:
            rows = conn.execute(
                """SELECT id, domain, url, scanned_at, score_pct, passed, failed, warnings
                   FROM scans WHERE domain = ? ORDER BY id DESC LIMIT ?""",
                (domain, limit),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []
