"""
Persistence layer for the ERP Integration Hub.

Uses SQLite for a self-contained, zero-setup local backend. The schema
is written in plain SQL so it maps directly onto PostgreSQL in a real
deployment — only the connection string changes, not the logic.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "erp_hub.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS requisitions (
    requisition_id TEXT PRIMARY KEY,
    requester TEXT,
    department TEXT,
    item_description TEXT,
    quantity INTEGER,
    unit_cost REAL,
    total_cost REAL,
    status TEXT,
    approver TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    source TEXT,
    department TEXT,
    amount REAL,
    description TEXT,
    timestamp TEXT,
    linked_requisition_id TEXT
);

CREATE TABLE IF NOT EXISTS security_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    severity TEXT,
    event_type TEXT,
    transaction_id TEXT,
    message TEXT,
    timestamp TEXT
);
"""


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def save_requisition(conn: sqlite3.Connection, req) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO requisitions
           (requisition_id, requester, department, item_description,
            quantity, unit_cost, total_cost, status, approver, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (req.requisition_id, req.requester, req.department, req.item_description,
         req.quantity, req.unit_cost, req.total_cost, req.status.value,
         req.approver, req.created_at.isoformat()),
    )
    conn.commit()


def save_transactions(conn: sqlite3.Connection, transactions) -> None:
    conn.executemany(
        """INSERT OR REPLACE INTO transactions
           (transaction_id, source, department, amount, description,
            timestamp, linked_requisition_id)
           VALUES (?,?,?,?,?,?,?)""",
        [
            (t.transaction_id, t.source.value, t.department, t.amount,
             t.description, t.timestamp.isoformat(), t.linked_requisition_id)
            for t in transactions
        ],
    )
    conn.commit()


def save_security_events(conn: sqlite3.Connection, events) -> None:
    conn.executemany(
        """INSERT INTO security_events
           (severity, event_type, transaction_id, message, timestamp)
           VALUES (?,?,?,?,?)""",
        [
            (e.severity, e.event_type, e.transaction_id, e.message, e.timestamp.isoformat())
            for e in events
        ],
    )
    conn.commit()


def query(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cur = conn.execute(sql, params)
    return [dict(row) for row in cur.fetchall()]


def reset_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        DELETE FROM requisitions;
        DELETE FROM transactions;
        DELETE FROM security_events;
    """)
    conn.commit()