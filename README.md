# LinguaPro - Language Education Center

Project for Introduction to Engineering Design (Laboratories 7 and 8).
The school, the course groups, the teachers and all data are simulated.

## Implemented operation

**Enroll a student in a course group**, end to end:
form -> server-side validation -> save in the SQLite database -> confirmation page -> record can be
retrieved later (also after the application is restarted).

Input: full name, e-mail, phone, group, learning goal.

Validation (server side, `linguapro/routes.py`):
- name 2 to 80 characters; e-mail valid, at most 120 characters, stored in lowercase;
  phone 7 to 20 digits, spaces or hyphens, optional leading `+`;
  goal one of Work, Travel, Exam preparation, Hobby; group must exist
- bad input -> HTTP 400, the form is shown again with a message under each wrong field, nothing is saved

Business rules (`linguapro/service.py`):
- full group -> rejected (HTTP 409)
- same student (same e-mail) twice in the same group -> rejected (HTTP 409)
- seat check and insert happen in one `BEGIN IMMEDIATE` transaction, so the last seat goes to one person only

The database adds a second line of defence: foreign keys, UNIQUE and CHECK constraints
(see `linguapro/schema.sql`). Even a bug in the application cannot save an enrollment for an unknown student or group.

## Requirements traceability

| Requirement (Lab 4) | Where it is implemented |
|---------------------|-------------------------|
| FR-01 register student data | enrollment form, `validate_enrollment` in `routes.py`, table `students` |
| FR-02 choose language and goal | groups list (language, level), goal field, table `enrollments` |
| FR-07 show groups with free seats | `/groups`, `list_groups` in `service.py` (joins `teachers`) |
| FR-08 block enrollment in a full group | `enroll_student` (409) and disabled option in the form |
| FR-13 create enrollment record | `enroll_student`, tables `students` and `enrollments` |
| FR-14 confirmation | confirmation page (on screen only, no e-mail yet) |
| NFR-07 data is persistent | SQLite file; test T8 restarts the server |
| NFR-08 last seat goes to one student | transaction + threaded test with 24 requests |

## Database

ERD: `docs/erd.png` (7 entities). Schema: `linguapro/schema.sql`.

| Table | Used now? | Purpose |
|-------|-----------|---------|
| teachers | yes (MVP) | teacher of a group |
| course_groups | yes (MVP) | groups with schedule, capacity, teacher |
| students | yes (MVP) | people who enroll |
| enrollments | yes (MVP) | student in a group (UNIQUE student+group) |
| placement_tests | later | Lab 4 FR-03/FR-04 |
| payments | later | Lab 4 FR-11/FR-12 |
| waitlist_entries | later | Lab 4 FR-09/FR-10 |

Initialization is repeatable. The database file `instance/linguapro.db` (with the tables and 3 demo teachers,
6 demo groups, 4 demo students) is created automatically on the first start. It can also be created on its own:

```
python -m flask --app run init-db
```

To start again from zero, stop the app and delete the `instance` folder.
A database made by the Laboratory 7 version has another schema; the app keeps it as
`linguapro_old_schema_backup.db` and creates a new one.

## Dependencies and technologies

Python 3.10 or newer (developed with 3.13), Flask 3 (see `requirements.txt`), SQLite through the standard
library `sqlite3`, HTML and CSS, `unittest`.

## Setup and run

Windows (PowerShell). If activating is blocked, first run `Set-ExecutionPolicy -Scope Process Bypass`:

```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```


Open http://127.0.0.1:5000. Another port: set `PORT`, for example `PORT=5001 python3 run.py`.
The app must keep running in its terminal window while you use the browser.

## Tests

Automated tests (24, use temporary databases):

```
python -m unittest discover -s tests -v
```

Acceptance check with a real server and a real restart (8 documented tests; writes `docs/test-results.md`):

```
python scripts/acceptance_check.py
```

| ID | Test | Expected |
|----|------|----------|
| T1 | valid submission | record saved and displayed |
| T2 | missing required fields | validation error (400), nothing saved |
| T3 | unknown group | rejected (400), data unchanged |
| T4 | full group | rejected (409), data unchanged |
| T5 | same student, same group | rejected (409), data unchanged |
| T6 | foreign key (direct SQL) | database rejects the row |
| T7 | check constraint (direct SQL) | database rejects the row |
| T8 | server restarted | earlier record still retrievable |

Actual results are in `docs/test-results.md`.



```
run.py                       starts the app
requirements.txt             dependencies
linguapro/                   application (db.py, schema.sql, routes.py, service.py, templates/, static/)
tests/                       unittest tests
scripts/acceptance_check.py  acceptance check with a real restart
docs/                        erd.png, architecture.png, screenshots/, test-results.md
```

Architecture: browser -> Flask (routes -> service -> templates) -> SQLite. See `docs/architecture.png`.


## Team contributions

TODO - the team must fill this in honestly before submitting.

| Member          |
|-----------------|
| Yvan shema      |
| UMULISA JOYEUSE |
| SHRINITTI       | 

