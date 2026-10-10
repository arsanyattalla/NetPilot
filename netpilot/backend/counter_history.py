
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent / "netpilot_history.db"

COUNTER_KEYS = (
    "input_errors",
    "crc_errors",
    "output_errors",
)


def initialize_database():
    """Create history tables and indexes without deleting existing data."""
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS interface_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device TEXT NOT NULL,
                interface TEXT NOT NULL,
                input_errors INTEGER NOT NULL,
                crc_errors INTEGER NOT NULL,
                output_errors INTEGER NOT NULL,
                captured_at TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_interface_snapshots
            ON interface_snapshots (device, interface, id)
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS cpu_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device TEXT NOT NULL,
                cpu_percent REAL NOT NULL CHECK(cpu_percent >= 0 AND cpu_percent <= 100),
                captured_at TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_cpu_snapshots_device_id
            ON cpu_snapshots (device, id)
        """)


def record_cpu_snapshot(device, cpu_percent, captured_at=None):
    """Persist one valid CPU utilization reading."""
    if isinstance(cpu_percent, bool) or not isinstance(
        cpu_percent, (int, float)
    ):
        return None

    cpu_percent = float(cpu_percent)

    if not 0 <= cpu_percent <= 100:
        return None

    captured_at = captured_at or datetime.now(timezone.utc).isoformat()
    initialize_database()

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute("""
            INSERT INTO cpu_snapshots (device, cpu_percent, captured_at)
            VALUES (?, ?, ?)
        """, (device, cpu_percent, captured_at))

        return {
            "id": cursor.lastrowid,
            "device": device,
            "cpu_percent": cpu_percent,
            "captured_at": captured_at,
        }


def get_recent_cpu_history(device, limit=100):
    """Return recent CPU readings, newest first."""
    initialize_database()

    limit = max(1, min(int(limit), 500))

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("""
            SELECT id, device, cpu_percent, captured_at
            FROM cpu_snapshots
            WHERE device = ?
            ORDER BY id DESC
            LIMIT ?
        """, (device, limit)).fetchall()

    return [dict(row) for row in rows]


def record_interface_snapshot(device, interfaces):
    """Save interface counters and compare them with prior snapshots."""
    initialize_database()
    results = []
    captured_at = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DB_PATH) as connection:
        for interface in interfaces:
            name = interface.get("interface", "Unknown")
            current = {
                key: max(0, int(interface.get(key, 0) or 0))
                for key in COUNTER_KEYS
            }

            previous_row = connection.execute("""
                SELECT input_errors, crc_errors, output_errors
                FROM interface_snapshots
                WHERE device = ? AND interface = ?
                ORDER BY id DESC
                LIMIT 1
            """, (device, name)).fetchone()

            if previous_row is None:
                status = "baseline"
                deltas = None
            else:
                previous = dict(zip(COUNTER_KEYS, previous_row))

                if any(
                    current[key] < previous[key]
                    for key in COUNTER_KEYS
                ):
                    status = "counter_reset_or_decrease"
                    deltas = None
                else:
                    deltas = {
                        key: current[key] - previous[key]
                        for key in COUNTER_KEYS
                    }
                    status = (
                        "increasing"
                        if any(value > 0 for value in deltas.values())
                        else "unchanged"
                    )

            connection.execute("""
                INSERT INTO interface_snapshots
                (device, interface, input_errors, crc_errors,
                 output_errors, captured_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                device,
                name,
                current["input_errors"],
                current["crc_errors"],
                current["output_errors"],
                captured_at,
            ))

            results.append({
                "interface": name,
                "status": status,
                "current": current,
                "new_errors_since_previous_poll": deltas,
                "captured_at": captured_at,
            })

    return results


def get_interface_trends(device):
    """Read the two newest snapshots per interface without writing data."""
    initialize_database()
    results = []

    with sqlite3.connect(DB_PATH) as connection:
        interfaces = connection.execute("""
            SELECT DISTINCT interface
            FROM interface_snapshots
            WHERE device = ?
        """, (device,)).fetchall()

        for (name,) in interfaces:
            rows = connection.execute("""
                SELECT input_errors, crc_errors, output_errors, captured_at
                FROM interface_snapshots
                WHERE device = ? AND interface = ?
                ORDER BY id DESC
                LIMIT 2
            """, (device, name)).fetchall()

            if not rows:
                continue

            latest = rows[0]
            current = dict(zip(COUNTER_KEYS, latest[:3]))

            if len(rows) < 2:
                results.append({
                    "interface": name,
                    "status": "baseline",
                    "current": current,
                    "new_errors_since_previous_poll": None,
                    "captured_at": latest[3],
                })
                continue

            previous = rows[1]
            previous_counters = dict(zip(COUNTER_KEYS, previous[:3]))

            if any(
                current[key] < previous_counters[key]
                for key in COUNTER_KEYS
            ):
                status = "counter_reset_or_decrease"
                deltas = None
            else:
                deltas = {
                    key: current[key] - previous_counters[key]
                    for key in COUNTER_KEYS
                }
                status = (
                    "increasing"
                    if any(value > 0 for value in deltas.values())
                    else "unchanged"
                )

            results.append({
                "interface": name,
                "status": status,
                "current": current,
                "new_errors_since_previous_poll": deltas,
                "captured_at": latest[3],
                "previous_captured_at": previous[3],
            })

    return results


def get_recent_history(device, limit=100):
    """Return recent interface snapshots, newest first."""
    initialize_database()
    limit = max(1, min(int(limit), 500))

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("""
            SELECT device, interface, input_errors, crc_errors,
                   output_errors, captured_at
            FROM interface_snapshots
            WHERE device = ?
            ORDER BY id DESC
            LIMIT ?
        """, (device, limit)).fetchall()

    return [dict(row) for row in rows]
