# Acceptance test results

Produced by `python scripts/acceptance_check.py` (real server process, temporary database).

| ID | Test | Input | Expected | Observed | Result |
|----|------|-------|----------|----------|--------|
| T1 | Valid submission | Jan Nowak, jan.nowak@example.com, +48 600 100 200, Work, English B1 - mornings | Record saved, redirect to a confirmation page that shows the details (HTTP 303, then 200) | HTTP 303, redirect to /enrollments/5; records 4 -> 5; confirmation page shows the name: True | PASS |
| T2 | Missing required fields | Name and e-mail left empty | Clear validation messages (HTTP 400), no record saved | HTTP 400; messages shown: True; records 5 -> 5 | PASS |
| T3 | Invalid reference (unknown group) | group_id = 99999 | Rejected (HTTP 400), data unchanged | HTTP 400; records 5 -> 5 | PASS |
| T4 | Business conflict: full group | Spanish A2 - evenings (2 of 2 seats taken) | Rejected (HTTP 409) with message that the group is full, data unchanged | HTTP 409; message 'is full' shown: True; records 5 -> 5 | PASS |
| T5 | Business conflict: same student, same group | Jan Nowak sends the same form again | Rejected (HTTP 409) with message 'already enrolled', data unchanged | HTTP 409; message shown: True; records 5 -> 5 | PASS |
| T6 | Database foreign key | INSERT INTO enrollments with student_id = 99999 (direct SQL) | Database rejects the row (FOREIGN KEY constraint) | Error: FOREIGN KEY constraint failed | PASS |
| T7 | Database check constraint | INSERT INTO course_groups with capacity = 0 (direct SQL) | Database rejects the row (CHECK constraint) | Error: CHECK constraint failed: capacity > 0 | PASS |
| T8 | Persistence after restart | Server stopped and started again, then GET /enrollments/5 | The earlier record is still there and is displayed | HTTP 200; details page shows Jan Nowak and the group: True; list page shows the record: True | PASS |
