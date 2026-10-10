
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta

DB_PATH = Path(__file__).resolve().parent / "netpilot_alerts.db"


def initialize_alerts_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device TEXT NOT NULL,
                severity TEXT NOT NULL,
                category TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)


def create_alert(device, severity, category, message):
    initialize_alerts_db()

    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(minutes=10)).isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        existing = conn.execute("""
            SELECT id FROM alerts
            WHERE device = ?
              AND category = ?
              AND message = ?
              AND created_at >= ?
            LIMIT 1
        """, (device, category, message, cutoff)).fetchone()

        if existing:
            return

        conn.execute("""
            INSERT INTO alerts
            (device, severity, category, message, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (device, severity, category, message, now.isoformat()))


def get_alerts(device, limit=50):
    initialize_alerts_db()

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT id, device, severity, category, message, created_at
            FROM alerts
            WHERE device = ?
            ORDER BY id DESC
            LIMIT ?
        """, (device, limit)).fetchall()

    return [dict(row) for row in rows]