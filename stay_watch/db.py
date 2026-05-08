from __future__ import annotations

import math
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from stay_watch.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT,
    msd TEXT,
    rssi INTEGER,
    count INTEGER
)
"""


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.execute(SCHEMA)


def clear() -> None:
    with connect() as conn:
        conn.execute("DELETE FROM users")


def upsert_beacon(conn: sqlite3.Connection, uuid: str, msd: str, rssi: int) -> None:
    cur = conn.cursor()
    row = cur.execute(
        "SELECT rssi, count FROM users WHERE uuid = ? AND msd = ?",
        (uuid, msd),
    ).fetchone()
    if row is None:
        cur.execute(
            "INSERT INTO users (uuid, msd, rssi, count) VALUES (?, ?, ?, 1)",
            (uuid, msd, rssi),
        )
    else:
        cur.execute(
            "UPDATE users SET rssi = ?, count = ? WHERE uuid = ? AND msd = ?",
            (row[0] + rssi, row[1] + 1, uuid, msd),
        )


def aggregated_beacons() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT uuid, msd, rssi, count FROM users"
        ).fetchall()
    return [
        {"uuid": r[0], "msd": r[1], "rssi": math.floor(r[2] / r[3])}
        for r in rows
    ]
