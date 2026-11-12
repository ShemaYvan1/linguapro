-- LinguaPro MVP database schema (SQLite)

CREATE TABLE students (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name   TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    phone       TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE course_groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    language    TEXT NOT NULL,
    level       TEXT NOT NULL,
    title       TEXT NOT NULL,
    schedule    TEXT NOT NULL,
    start_date  TEXT NOT NULL,
    capacity    INTEGER NOT NULL CHECK (capacity > 0)
);

CREATE TABLE enrollments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  INTEGER NOT NULL REFERENCES students(id),
    group_id    INTEGER NOT NULL REFERENCES course_groups(id),
    goal        TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (student_id, group_id)
);
