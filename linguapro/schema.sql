-- LinguaPro database schema (SQLite), Laboratory 8.
-- MVP tables (used by the working feature): teachers, course_groups, students, enrollments.
-- Later tables (created now so the schema matches the ERD, not used by the app yet):
-- placement_tests, payments, waitlist_entries.
-- Foreign keys are enforced because every connection runs PRAGMA foreign_keys = ON (see db.py).

-- ---------------------------------------------------------------- MVP tables
CREATE TABLE teachers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name   TEXT NOT NULL CHECK (length(trim(full_name)) >= 2),
    email       TEXT NOT NULL UNIQUE
);

CREATE TABLE course_groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id  INTEGER NOT NULL REFERENCES teachers(id),
    language    TEXT NOT NULL,
    level       TEXT NOT NULL CHECK (level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')),
    title       TEXT NOT NULL UNIQUE,
    schedule    TEXT NOT NULL,
    start_date  TEXT NOT NULL,
    capacity    INTEGER NOT NULL CHECK (capacity > 0)
);

CREATE TABLE students (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name   TEXT NOT NULL CHECK (length(trim(full_name)) >= 2),
    email       TEXT NOT NULL UNIQUE CHECK (email LIKE '%_@_%._%'),
    phone       TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE enrollments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  INTEGER NOT NULL REFERENCES students(id),
    group_id    INTEGER NOT NULL REFERENCES course_groups(id),
    goal        TEXT NOT NULL CHECK (goal IN ('Work', 'Travel', 'Exam preparation', 'Hobby')),
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (student_id, group_id)
);

-- ---------------------------------------------------------------- later tables
CREATE TABLE placement_tests (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id         INTEGER NOT NULL REFERENCES students(id),
    language           TEXT NOT NULL,
    score              INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    recommended_level  TEXT NOT NULL CHECK (recommended_level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')),
    taken_at           TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE payments (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id  INTEGER NOT NULL UNIQUE REFERENCES enrollments(id),
    amount_pln     INTEGER NOT NULL CHECK (amount_pln > 0),
    status         TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'failed')),
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE waitlist_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  INTEGER NOT NULL REFERENCES students(id),
    group_id    INTEGER NOT NULL REFERENCES course_groups(id),
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (student_id, group_id)
);

PRAGMA user_version = 2;
