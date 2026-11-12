# LinguaPro - Language Education Center (MVP)

First working version for Introduction to Engineering Design, Laboratory 7.
The school, the course groups and all data are simulated.

## MVP operation

**Enroll a student in a course group.** The student (or office staff) opens the groups list,
picks a group with a free seat, fills in the enrollment form and gets a confirmation page.

Input: full name, e-mail, phone, group, learning goal.

Validation (done on the server, in `linguapro/routes.py`):
- name: 2 to 80 characters
- e-mail: valid format, at most 120 characters, stored in lowercase
- phone: 7 to 20 digits, spaces or hyphens, optional leading `+`
- goal: one of Work, Travel, Exam preparation, Hobby
- group: must exist

Business rules (in `linguapro/service.py`):
- a full group is rejected (HTTP 409)
- the same student cannot enroll twice in the same group (HTTP 409)
- the seat check and the insert run in one `BEGIN IMMEDIATE` transaction, so two people
  cannot take the last seat at the same time

Related requirements from the Lab 5 document: FR-01, FR-02, FR-07, FR-08, FR-13, FR-14, NFR-08.

## Technologies

- Python 3.10 or newer (developed with 3.13)
- Flask 3 (web framework, Jinja2 templates)
- SQLite (database, Python standard library `sqlite3`)
- plain HTML and CSS, no JavaScript framework
- `unittest` for tests

## Setup and run

Windows (PowerShell):

```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

macOS / Linux:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 run.py
```

Open http://127.0.0.1:5000 in a browser. The database file `instance/linguapro.db` is created
on the first start together with 6 demo groups (one of them full, one with a single free seat).
To start again from scratch, stop the app and delete the `instance` folder.

To use another port: set the `PORT` environment variable, for example `PORT=5001 python3 run.py`.

## Tests

```
python -m unittest discover -s tests -v
```

13 tests: pages load, valid enrollment, full group, duplicate, invalid input, unknown group,
and a test where 24 students try to take the last free seat at once (exactly one must succeed).

## Project structure

```
run.py                  starts the app
requirements.txt        Python dependencies
linguapro/
  __init__.py           creates the Flask app
  db.py                 database connection, schema creation, demo data
  schema.sql            tables: students, course_groups, enrollments
  routes.py             URLs and input validation
  service.py            business rules and database queries
  templates/            HTML pages
  static/style.css      styling
tests/test_enroll.py    automated tests
docs/architecture.png   architecture diagram
docs/screenshots/       screenshots of the running app
```

## Architecture

Browser -> Flask application (routes -> service -> templates) -> SQLite.
See `docs/architecture.png`. Validation and the seat check are on the server; the HTML
attributes in the form are only hints for the user.

## Not in this version

Placement test, online payment, e-mail notifications, waiting list, teacher notification,
administrator pages, login and user roles. These are planned for later laboratories.

## Team contributions

TODO - the team must fill this in honestly before submitting.

| Member | What they did |
|--------|---------------|
| (name) | (e.g. wrote the enrollment form and validation) |
| (name) | (e.g. database schema and tests) |
| (name) | (e.g. architecture diagram and documentation) |
| (name) | |

## Notes

No passwords or secrets are stored in this repository. The `instance` folder (database) is ignored by git.
