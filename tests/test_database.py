"""Tests for the database layer: schema, constraints, foreign keys, persistence (Laboratory 8).

Run from the project folder:  python -m unittest discover -s tests -v
"""
import os
import sqlite3
import tempfile
import unittest

from linguapro import create_app
from linguapro.db import get_db

VALID = {"full_name": "Test Student", "email": "test.student@example.com", "phone": "+48 123 456 789", "goal": "Work"}


class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "test.db")
        self.app = create_app({"TESTING": True, "DATABASE": self.path})

    def tearDown(self):
        self.tmp.cleanup()

    def run_sql(self, sql, params=()):
        """Run one statement the way the app does (foreign keys ON). Returns all rows."""
        with self.app.app_context():
            return get_db().execute(sql, params).fetchall()

    def one(self, sql, params=()):
        return self.run_sql(sql, params)[0][0]

    def group_id(self, title):
        with self.app.app_context():
            return get_db().execute("SELECT id FROM course_groups WHERE title = ?", (title,)).fetchone()["id"]

    # schema ----------------------------------------------------------------------------------
    def test_schema_has_the_seven_entities_of_the_erd(self):
        with self.app.app_context():
            names = {r["name"] for r in get_db().execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")}
        self.assertEqual(names, {"teachers", "course_groups", "students", "enrollments",
                                 "placement_tests", "payments", "waitlist_entries"})

    def test_foreign_keys_are_enforced(self):
        with self.app.app_context():
            self.assertEqual(get_db().execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_enrollment_with_unknown_student_or_group_is_rejected_by_the_database(self):
        gid = self.group_id("English A2 - evenings")
        with self.assertRaises(sqlite3.IntegrityError):
            self.run_sql("INSERT INTO enrollments (student_id, group_id, goal) VALUES (99999, ?, 'Work')", (gid,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.run_sql("INSERT INTO enrollments (student_id, group_id, goal) VALUES (1, 99999, 'Work')")

    def test_group_needs_an_existing_teacher(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.run_sql("INSERT INTO course_groups (teacher_id, language, level, title, schedule, start_date, capacity) "
                         "VALUES (99999, 'English', 'A1', 'X', 'Mon', '2026-12-01', 5)")

    def test_check_constraints(self):
        bad = [
            "INSERT INTO course_groups (teacher_id, language, level, title, schedule, start_date, capacity) "
            "VALUES (1, 'English', 'A1', 'Zero seats', 'Mon', '2026-12-01', 0)",
            "INSERT INTO course_groups (teacher_id, language, level, title, schedule, start_date, capacity) "
            "VALUES (1, 'English', 'Z9', 'Bad level', 'Mon', '2026-12-01', 5)",
            "INSERT INTO students (full_name, email, phone) VALUES ('Ann', 'no-at-sign', '123456789')",
            "INSERT INTO enrollments (student_id, group_id, goal) VALUES (1, 1, 'Fun')",
        ]
        for sql in bad:
            with self.subTest(sql=sql[:60]):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.run_sql(sql)

    def test_duplicate_student_email_is_rejected_by_the_database(self):
        self.run_sql("INSERT INTO students (full_name, email, phone) VALUES ('Ann Lee', 'ann@example.com', '123456789')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.run_sql("INSERT INTO students (full_name, email, phone) VALUES ('Ann Two', 'ann@example.com', '123456789')")

    def test_database_init_is_repeatable(self):
        create_app({"TESTING": True, "DATABASE": self.path})  # second start on the same file
        self.assertEqual(self.one("SELECT COUNT(*) FROM course_groups"), 6)
        self.assertEqual(self.one("SELECT COUNT(*) FROM teachers"), 3)

    def test_old_lab7_database_is_kept_as_backup(self):
        old = os.path.join(self.tmp.name, "old.db")
        conn = sqlite3.connect(old)
        conn.execute("CREATE TABLE course_groups (id INTEGER PRIMARY KEY, title TEXT)")  # old shape, user_version 0
        conn.commit(); conn.close()
        app = create_app({"TESTING": True, "DATABASE": old})
        with app.app_context():
            self.assertEqual(get_db().execute("SELECT COUNT(*) FROM teachers").fetchone()[0], 3)
        self.assertTrue(any("old_schema_backup" in f for f in os.listdir(self.tmp.name)))

    # feature + persistence -------------------------------------------------------------------
    def test_missing_required_fields_are_rejected_and_nothing_is_saved(self):
        client = self.app.test_client()
        before = self.one("SELECT COUNT(*) FROM enrollments")
        for missing in ("full_name", "email", "phone", "goal", "group_id"):
            with self.subTest(missing=missing):
                data = dict(VALID, group_id=self.group_id("English A2 - evenings"))
                del data[missing]
                self.assertEqual(client.post("/enroll", data=data).status_code, 400)
        self.assertEqual(self.one("SELECT COUNT(*) FROM enrollments"), before)
        self.assertEqual(self.one("SELECT COUNT(*) FROM students WHERE email = ?", (VALID["email"],)), 0)

    def test_saved_enrollment_survives_an_application_restart(self):
        client = self.app.test_client()
        r = client.post("/enroll", data=dict(VALID, group_id=self.group_id("English B1 - mornings")))
        self.assertEqual(r.status_code, 303)
        location = r.headers["Location"]
        restarted = create_app({"TESTING": True, "DATABASE": self.path})  # new app object = new start
        page = restarted.test_client().get(location)
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Test Student", page.data)
        self.assertIn(b"English B1 - mornings", page.data)
        self.assertIn(b"Anna Kowalska", page.data)  # teacher comes from a joined table
        self.assertIn(b"Test Student", restarted.test_client().get("/enrollments").data)

    def test_groups_page_shows_teacher(self):
        page = self.app.test_client().get("/groups").data
        self.assertIn(b"Hans Becker", page)


if __name__ == "__main__":
    unittest.main()
