"""Database access: one SQLite connection per request, schema creation and demo data."""
import sqlite3
from pathlib import Path

from flask import current_app, g

SCHEMA = Path(__file__).with_name("schema.sql")

# Invented demo groups: (language, level, title, schedule, start_date, capacity)
DEMO_GROUPS = [
    ("English", "A2", "English A2 - evenings", "Mon and Wed 18:00-19:30", "2026-12-01", 8),
    ("English", "B1", "English B1 - mornings", "Tue and Thu 09:00-10:30", "2026-12-02", 6),
    ("German", "A1", "German A1 - beginners", "Mon and Wed 17:00-18:30", "2026-12-01", 8),
    ("German", "B1", "German B1 - evenings", "Tue and Thu 18:00-19:30", "2026-12-03", 6),
    ("Spanish", "A2", "Spanish A2 - evenings", "Tue and Thu 18:00-19:30", "2026-12-03", 2),
    ("Spanish", "B1", "Spanish B1 - weekends", "Sat 10:00-13:00", "2026-12-05", 3),
]
# Demo students who already fill the Spanish A2 group (2 of 2 seats) and 2 of 3 seats in Spanish B1.
DEMO_ENROLLMENTS = {
    "Spanish A2 - evenings": ["Demo Student 1", "Demo Student 2"],
    "Spanish B1 - weekends": ["Demo Student 3", "Demo Student 4"],
}


def get_db():
    """Return the SQLite connection of the current request.

    isolation_level=None means autocommit: transactions are started explicitly (see service.py),
    so the seat check and the insert can be done in one transaction.
    """
    if "db" not in g:
        conn = sqlite3.connect(current_app.config["DATABASE"], timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def close_db(_error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_app(app):
    app.teardown_appcontext(close_db)


def init_db_if_needed():
    """Create the tables and demo data the first time the app starts."""
    conn = get_db()
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'course_groups'"
    ).fetchone()
    if exists:
        return
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    seed_demo_data(conn)


def seed_demo_data(conn):
    for language, level, title, schedule, start_date, capacity in DEMO_GROUPS:
        conn.execute(
            "INSERT INTO course_groups (language, level, title, schedule, start_date, capacity) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (language, level, title, schedule, start_date, capacity),
        )
    n = 0
    for title, names in DEMO_ENROLLMENTS.items():
        group_id = conn.execute("SELECT id FROM course_groups WHERE title = ?", (title,)).fetchone()["id"]
        for name in names:
            n += 1
            cur = conn.execute(
                "INSERT INTO students (full_name, email, phone) VALUES (?, ?, ?)",
                (name, f"demo{n}@example.com", "+48 000 000 000"),
            )
            conn.execute(
                "INSERT INTO enrollments (student_id, group_id, goal) VALUES (?, ?, ?)",
                (cur.lastrowid, group_id, "Hobby"),
            )
