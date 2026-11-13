"""Documented acceptance tests (Laboratory 8) against a REAL running server, including a real restart.

Run from the project folder:   python scripts/acceptance_check.py
It uses a temporary database, starts `python run.py` as a separate process, sends HTTP requests,
stops the server, starts it again and checks that the saved record is still there.
The result table is printed and written to docs/test-results.md.
"""
import http.client
import os
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "test-results.md"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Server:
    def __init__(self, db, port):
        self.db, self.port, self.proc = db, port, None

    def start(self):
        env = dict(os.environ, LINGUAPRO_DB=self.db, PORT=str(self.port))
        self.proc = subprocess.Popen([sys.executable, str(ROOT / "run.py")], cwd=ROOT, env=env,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                self.request("GET", "/")
                return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError("server did not start")

    def stop(self):
        self.proc.terminate()
        self.proc.wait(timeout=10)

    def request(self, method, path, form=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        body = urllib.parse.urlencode(form) if form is not None else None
        headers = {"Content-Type": "application/x-www-form-urlencoded"} if form is not None else {}
        conn.request(method, path, body, headers)
        r = conn.getresponse()
        data = r.read().decode("utf-8")
        result = (r.status, r.getheader("Location"), data)
        conn.close()
        return result


def count(db, sql, params=()):
    conn = sqlite3.connect(db)
    try:
        return conn.execute(sql, params).fetchone()[0]
    finally:
        conn.close()


def main():
    tmp = tempfile.TemporaryDirectory()
    db = os.path.join(tmp.name, "acceptance.db")
    srv = Server(db, free_port())
    rows = []  # (id, test, input, expected, observed, passed)

    def record(tid, name, inp, expected, observed, passed):
        rows.append((tid, name, inp, expected, observed, "PASS" if passed else "FAIL"))

    srv.start()
    try:
        gid = count(db, "SELECT id FROM course_groups WHERE title = 'English B1 - mornings'")
        full_gid = count(db, "SELECT id FROM course_groups WHERE title = 'Spanish A2 - evenings'")
        valid = {"full_name": "Jan Nowak", "email": "jan.nowak@example.com", "phone": "+48 600 100 200",
                 "goal": "Work", "group_id": gid}
        base = count(db, "SELECT COUNT(*) FROM enrollments")

        # T1 valid submission
        st, loc, _ = srv.request("POST", "/enroll", valid)
        page = srv.request("GET", loc)[2] if loc else ""
        saved = count(db, "SELECT COUNT(*) FROM enrollments") == base + 1
        shown = "Enrollment confirmed" in page and "Jan Nowak" in page
        m = re.search(r"/enrollments/(\d+)", loc or "")
        enr_id = m.group(1) if m else None
        record("T1", "Valid submission", "Jan Nowak, jan.nowak@example.com, +48 600 100 200, Work, English B1 - mornings",
               "Record saved, redirect to a confirmation page that shows the details (HTTP 303, then 200)",
               f"HTTP {st}, redirect to {loc}; records {base} -> {base + 1}; confirmation page shows the name: {shown}",
               st == 303 and saved and shown)

        # T2 missing required field
        before = count(db, "SELECT COUNT(*) FROM enrollments")
        st, _, page = srv.request("POST", "/enroll", dict(valid, email="", full_name=""))
        record("T2", "Missing required fields", "Name and e-mail left empty",
               "Clear validation messages (HTTP 400), no record saved",
               f"HTTP {st}; messages shown: {'Enter your full name' in page and 'valid e-mail' in page}; "
               f"records {before} -> {count(db, 'SELECT COUNT(*) FROM enrollments')}",
               st == 400 and "Enter your full name" in page and "valid e-mail" in page
               and count(db, "SELECT COUNT(*) FROM enrollments") == before)

        # T3 invalid reference
        before = count(db, "SELECT COUNT(*) FROM enrollments")
        st, _, page = srv.request("POST", "/enroll", dict(valid, email="other@example.com", group_id=99999))
        record("T3", "Invalid reference (unknown group)", "group_id = 99999",
               "Rejected (HTTP 400), data unchanged",
               f"HTTP {st}; records {before} -> {count(db, 'SELECT COUNT(*) FROM enrollments')}",
               st == 400 and count(db, "SELECT COUNT(*) FROM enrollments") == before)

        # T4 business conflict: full group
        before = count(db, "SELECT COUNT(*) FROM enrollments")
        st, _, page = srv.request("POST", "/enroll", dict(valid, email="late@example.com", group_id=full_gid))
        record("T4", "Business conflict: full group", "Spanish A2 - evenings (2 of 2 seats taken)",
               "Rejected (HTTP 409) with message that the group is full, data unchanged",
               f"HTTP {st}; message 'is full' shown: {'is full' in page}; "
               f"records {before} -> {count(db, 'SELECT COUNT(*) FROM enrollments')}",
               st == 409 and "is full" in page and count(db, "SELECT COUNT(*) FROM enrollments") == before)

        # T5 business conflict: duplicate
        before = count(db, "SELECT COUNT(*) FROM enrollments")
        st, _, page = srv.request("POST", "/enroll", valid)
        record("T5", "Business conflict: same student, same group", "Jan Nowak sends the same form again",
               "Rejected (HTTP 409) with message 'already enrolled', data unchanged",
               f"HTTP {st}; message shown: {'already enrolled' in page}; "
               f"records {before} -> {count(db, 'SELECT COUNT(*) FROM enrollments')}",
               st == 409 and "already enrolled" in page and count(db, "SELECT COUNT(*) FROM enrollments") == before)

        # T6 database rejects a bad foreign key even without the application
        err = ""
        conn = sqlite3.connect(db)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            conn.execute("INSERT INTO enrollments (student_id, group_id, goal) VALUES (99999, ?, 'Work')", (gid,))
            conn.commit()
        except sqlite3.IntegrityError as e:
            err = str(e)
        finally:
            conn.close()
        record("T6", "Database foreign key", "INSERT INTO enrollments with student_id = 99999 (direct SQL)",
               "Database rejects the row (FOREIGN KEY constraint)",
               f"Error: {err or 'no error'}", "FOREIGN KEY" in err)

        # T7 database check constraint
        err = ""
        conn = sqlite3.connect(db)
        try:
            conn.execute("INSERT INTO course_groups (teacher_id, language, level, title, schedule, start_date, capacity) "
                         "VALUES (1, 'English', 'A1', 'Zero seats', 'Mon', '2026-12-01', 0)")
            conn.commit()
        except sqlite3.IntegrityError as e:
            err = str(e)
        finally:
            conn.close()
        record("T7", "Database check constraint", "INSERT INTO course_groups with capacity = 0 (direct SQL)",
               "Database rejects the row (CHECK constraint)", f"Error: {err or 'no error'}", "CHECK" in err)
    finally:
        srv.stop()

    # T8 restart
    srv.start()
    try:
        st, _, page = srv.request("GET", f"/enrollments/{enr_id}")
        st2, _, lst = srv.request("GET", "/enrollments")
        ok = st == 200 and "Jan Nowak" in page and "English B1 - mornings" in page and "Jan Nowak" in lst
        record("T8", "Persistence after restart", f"Server stopped and started again, then GET /enrollments/{enr_id}",
               "The earlier record is still there and is displayed",
               f"HTTP {st}; details page shows Jan Nowak and the group: {ok}; list page shows the record: {'Jan Nowak' in lst}",
               ok)
    finally:
        srv.stop()
        tmp.cleanup()

    lines = ["# Acceptance test results", "",
             "Produced by `python scripts/acceptance_check.py` (real server process, temporary database).", "",
             "| ID | Test | Input | Expected | Observed | Result |", "|----|------|-------|----------|----------|--------|"]
    for r in rows:
        lines.append("| " + " | ".join(c.replace("|", "/") for c in r) + " |")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for r in rows:
        print(f"{r[0]} {r[5]}  {r[1]}\n     observed: {r[4]}")
    failed = [r[0] for r in rows if r[5] != "PASS"]
    print("ALL PASSED" if not failed else f"FAILED: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
