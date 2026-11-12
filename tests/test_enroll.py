"""Tests for the MVP operation: enroll a student in a course group.

Run from the project folder:  python -m unittest discover -s tests -v
"""
import os
import tempfile
import threading
import unittest

from linguapro import create_app
from linguapro.db import get_db

VALID = {
    "full_name": "Test Student",
    "email": "test.student@example.com",
    "phone": "+48 123 456 789",
    "goal": "Work",
}


class EnrollTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING": True, "DATABASE": os.path.join(self.tmp.name, "test.db")})
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    # helpers ---------------------------------------------------------------------------------
    def group_id(self, title):
        with self.app.app_context():
            return get_db().execute("SELECT id FROM course_groups WHERE title = ?", (title,)).fetchone()["id"]

    def count(self, table):
        with self.app.app_context():
            return get_db().execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def post_enroll(self, client=None, **overrides):
        data = dict(VALID, group_id=self.group_id("English A2 - evenings"))
        data.update(overrides)
        return (client or self.client).post("/enroll", data=data)

    # pages -----------------------------------------------------------------------------------
    def test_home_page_loads(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"LinguaPro", r.data)
        self.assertIn(b"Enroll a student", r.data)

    def test_groups_page_shows_free_seats(self):
        r = self.client.get("/groups")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"English A2 - evenings", r.data)
        self.assertIn(b"8 of 8", r.data)
        self.assertIn(b"Full", r.data)  # the demo Spanish A2 group is full

    def test_groups_can_be_filtered_by_language(self):
        r = self.client.get("/groups?language=German")
        self.assertIn(b"German A1", r.data)
        self.assertNotIn(b"English A2", r.data)

    def test_enroll_form_loads(self):
        r = self.client.get("/enroll")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'name="full_name"', r.data)

    def test_unknown_enrollment_returns_404(self):
        self.assertEqual(self.client.get("/enrollments/99999").status_code, 404)

    # the MVP operation -----------------------------------------------------------------------
    def test_valid_enrollment_is_saved_and_confirmed(self):
        before = self.count("enrollments")
        r = self.post_enroll()
        self.assertEqual(r.status_code, 303)
        page = self.client.get(r.headers["Location"])
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Enrollment confirmed", page.data)
        self.assertIn(b"Test Student", page.data)
        self.assertEqual(self.count("enrollments"), before + 1)
        self.assertIn(b"7 of 8", self.client.get("/groups").data)  # free seats went down by one

    def test_email_is_stored_in_lowercase_and_name_is_tidied(self):
        self.post_enroll(email="Test.Student@Example.COM", full_name="  Test    Student ")
        with self.app.app_context():
            s = get_db().execute("SELECT * FROM students WHERE email LIKE 'test.student%'").fetchone()
        self.assertEqual(s["email"], "test.student@example.com")
        self.assertEqual(s["full_name"], "Test Student")

    def test_full_group_is_rejected(self):
        before = self.count("enrollments")
        r = self.post_enroll(group_id=self.group_id("Spanish A2 - evenings"))
        self.assertEqual(r.status_code, 409)
        self.assertIn(b"is full", r.data)
        self.assertEqual(self.count("enrollments"), before)

    def test_duplicate_enrollment_is_rejected(self):
        self.assertEqual(self.post_enroll().status_code, 303)
        before = self.count("enrollments")
        r = self.post_enroll()
        self.assertEqual(r.status_code, 409)
        self.assertIn(b"already enrolled", r.data)
        self.assertEqual(self.count("enrollments"), before)

    def test_same_student_can_join_a_second_group(self):
        self.assertEqual(self.post_enroll().status_code, 303)
        r = self.post_enroll(group_id=self.group_id("German A1 - beginners"))
        self.assertEqual(r.status_code, 303)
        self.assertEqual(self.count("students"), 4 + 1)  # 4 demo students + this one

    def test_invalid_input_is_rejected_and_nothing_is_saved(self):
        bad_inputs = {
            "full_name": "A",
            "email": "not-an-email",
            "phone": "abc",
            "goal": "Fun",
            "group_id": "",
        }
        for field, value in bad_inputs.items():
            with self.subTest(field=field):
                before = self.count("enrollments")
                r = self.post_enroll(**{field: value})
                self.assertEqual(r.status_code, 400)
                self.assertEqual(self.count("enrollments"), before)

    def test_unknown_group_is_rejected(self):
        r = self.post_enroll(group_id=99999)
        self.assertEqual(r.status_code, 400)

    def test_last_seat_goes_to_exactly_one_student(self):
        """Twenty-four students press 'Enroll' at the same moment for a group with ONE free seat (NFR-08)."""
        gid = self.group_id("Spanish B1 - weekends")  # capacity 3, 2 demo seats taken
        n = 24
        barrier = threading.Barrier(n)
        statuses = []
        lock = threading.Lock()

        def worker(i):
            client = self.app.test_client()
            barrier.wait()
            r = client.post("/enroll", data=dict(VALID, email=f"racer{i}@example.com", group_id=gid))
            with lock:
                statuses.append(r.status_code)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(statuses.count(303), 1, statuses)
        self.assertEqual(statuses.count(409), n - 1, statuses)
        with self.app.app_context():
            taken = get_db().execute("SELECT COUNT(*) FROM enrollments WHERE group_id = ?", (gid,)).fetchone()[0]
        self.assertEqual(taken, 3)


if __name__ == "__main__":
    unittest.main()
