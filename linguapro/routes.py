"""Web routes and input validation."""
import re

from flask import Blueprint, abort, redirect, render_template, request, url_for

from . import service
from .db import get_db

bp = Blueprint("main", __name__)

GOALS = ["Work", "Travel", "Exam preparation", "Hobby"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9][0-9 \-]{6,19}$")


def validate_enrollment(form):
    """Check the form fields on the server. Returns (clean_data, errors); errors maps field -> message."""
    errors = {}
    full_name = " ".join(form.get("full_name", "").split())
    email = form.get("email", "").strip().lower()
    phone = form.get("phone", "").strip()
    goal = form.get("goal", "").strip()
    group_raw = form.get("group_id", "").strip()

    if not 2 <= len(full_name) <= 80:
        errors["full_name"] = "Enter your full name (2 to 80 characters)."
    if len(email) > 120 or not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid e-mail address, for example name@example.com."
    if not PHONE_RE.match(phone):
        errors["phone"] = "Enter a phone number with 7 to 20 digits, spaces or hyphens (a leading + is allowed)."
    if goal not in GOALS:
        errors["goal"] = "Choose one of the learning goals from the list."
    group_id = None
    if not group_raw.isdigit():
        errors["group_id"] = "Choose a group."
    else:
        group_id = int(group_raw)

    clean = {"full_name": full_name, "email": email, "phone": phone, "goal": goal, "group_id": group_id}
    return clean, errors


@bp.route("/")
def home():
    return render_template("home.html", stats=service.stats(get_db()))


@bp.route("/groups")
def groups():
    conn = get_db()
    language = request.args.get("language") or None
    languages = service.list_languages(conn)
    if language not in languages:
        language = None
    return render_template(
        "groups.html", groups=service.list_groups(conn, language), languages=languages, selected=language
    )


def render_form(values, errors, status=200, error_message=None):
    conn = get_db()
    return (
        render_template(
            "enroll.html",
            groups=service.list_groups(conn),
            goals=GOALS,
            values=values,
            errors=errors,
            error_message=error_message,
        ),
        status,
    )


@bp.route("/enroll", methods=["GET", "POST"])
def enroll():
    if request.method == "GET":
        values = {"group_id": request.args.get("group_id", "")}
        return render_form(values, {})

    clean, errors = validate_enrollment(request.form)
    values = {k: ("" if v is None else str(v)) for k, v in clean.items()}
    if errors:
        return render_form(values, errors, status=400)
    try:
        enrollment_id = service.enroll_student(get_db(), clean)
    except service.EnrollmentError as err:
        return render_form(values, {err.field or "group_id": err.message}, status=err.status,
                           error_message=err.message)
    return redirect(url_for("main.confirmation", enrollment_id=enrollment_id), code=303)


@bp.route("/enrollments")
def enrollments():
    return render_template("enrollments.html", rows=service.recent_enrollments(get_db()))


@bp.route("/enrollments/<int:enrollment_id>")
def confirmation(enrollment_id):
    row = service.get_enrollment(get_db(), enrollment_id)
    if row is None:
        abort(404)
    return render_template("confirmation.html", e=row)
