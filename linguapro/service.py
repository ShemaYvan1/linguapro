"""Business rules of the MVP operation: enroll a student in a course group."""


class EnrollmentError(Exception):
    """A business rule was broken. `status` is the HTTP status the route should answer with."""

    def __init__(self, message, status=409, field=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.field = field


def list_groups(conn, language=None):
    """All groups with the number of free seats (capacity minus enrollments)."""
    sql = (
        "SELECT g.*, g.capacity - COUNT(e.id) AS free_seats "
        "FROM course_groups g LEFT JOIN enrollments e ON e.group_id = g.id "
    )
    params = ()
    if language:
        sql += "WHERE g.language = ? "
        params = (language,)
    sql += "GROUP BY g.id ORDER BY g.language, g.level"
    return conn.execute(sql, params).fetchall()


def list_languages(conn):
    rows = conn.execute("SELECT DISTINCT language FROM course_groups ORDER BY language").fetchall()
    return [r["language"] for r in rows]


def enroll_student(conn, data):
    """Save the student and the enrollment, or raise EnrollmentError.

    Business rules:
      1. the group must exist
      2. a full group cannot be booked (FR-08)
      3. the same e-mail cannot enroll twice in the same group
      4. the seat check and the insert happen in ONE transaction (BEGIN IMMEDIATE takes the write lock),
         so when two students ask for the last seat at the same time, exactly one of them gets it (NFR-08)

    Returns the new enrollment id.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        group = conn.execute("SELECT * FROM course_groups WHERE id = ?", (data["group_id"],)).fetchone()
        if group is None:
            raise EnrollmentError("This group does not exist.", status=400, field="group_id")

        taken = conn.execute("SELECT COUNT(*) FROM enrollments WHERE group_id = ?", (group["id"],)).fetchone()[0]
        if taken >= group["capacity"]:
            raise EnrollmentError(
                f"Sorry, {group['title']} is full. Please choose another group.", status=409, field="group_id"
            )

        student = conn.execute("SELECT id FROM students WHERE email = ?", (data["email"],)).fetchone()
        if student is None:
            cur = conn.execute(
                "INSERT INTO students (full_name, email, phone) VALUES (?, ?, ?)",
                (data["full_name"], data["email"], data["phone"]),
            )
            student_id = cur.lastrowid
        else:
            student_id = student["id"]

        already = conn.execute(
            "SELECT 1 FROM enrollments WHERE student_id = ? AND group_id = ?", (student_id, group["id"])
        ).fetchone()
        if already:
            raise EnrollmentError("This e-mail address is already enrolled in this group.", status=409, field="email")

        cur = conn.execute(
            "INSERT INTO enrollments (student_id, group_id, goal) VALUES (?, ?, ?)",
            (student_id, group["id"], data["goal"]),
        )
        enrollment_id = cur.lastrowid
        conn.execute("COMMIT")
        return enrollment_id
    except Exception:
        conn.execute("ROLLBACK")
        raise


def get_enrollment(conn, enrollment_id):
    return conn.execute(
        "SELECT e.id, e.goal, e.created_at, s.full_name, s.email, g.title, g.language, g.level, g.schedule, "
        "g.start_date FROM enrollments e JOIN students s ON s.id = e.student_id "
        "JOIN course_groups g ON g.id = e.group_id WHERE e.id = ?",
        (enrollment_id,),
    ).fetchone()


def recent_enrollments(conn, limit=20):
    """Recent enrollments WITHOUT e-mail or phone (no login exists yet, so personal data is not shown)."""
    return conn.execute(
        "SELECT e.id, e.goal, e.created_at, s.full_name, g.title "
        "FROM enrollments e JOIN students s ON s.id = e.student_id "
        "JOIN course_groups g ON g.id = e.group_id ORDER BY e.id DESC LIMIT ?",
        (limit,),
    ).fetchall()


def stats(conn):
    groups = list_groups(conn)
    return {
        "groups": len(groups),
        "free_seats": sum(max(g["free_seats"], 0) for g in groups),
        "enrollments": conn.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0],
    }
