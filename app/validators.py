"""Input validation.

Every function takes raw input (a form or JSON dict of strings), collects ALL
problems into an `errors` dict, and either raises ValidationError(errors) or
returns a cleaned dict with proper Python types. The database also has CHECK
constraints as a second line of defence.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Optional

from .exceptions import ValidationError
from .models import CATEGORIES, Status

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
URL_RE = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)


# ---------------------------------------------------------------- helpers --
def _text(data: dict, key: str) -> str:
    value = data.get(key)
    return str(value).strip() if value is not None else ""


def _parse_date(data: dict, key: str, errors: dict) -> Optional[date]:
    raw = _text(data, key)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        errors[key] = "Use a valid date (YYYY-MM-DD)"
        return None


def _parse_int(data: dict, key: str, errors: dict, lo: int, hi: int, default=None):
    raw = _text(data, key)
    if raw == "":
        if default is None:
            errors[key] = "This field is required"
        return default
    try:
        value = int(raw)
    except ValueError:
        errors[key] = "Must be a whole number"
        return default
    if not lo <= value <= hi:
        errors[key] = f"Must be between {lo} and {hi}"
    return value


def _length(value: str, key: str, errors: dict, lo: int, hi: int, label: str):
    if not lo <= len(value) <= hi:
        errors[key] = f"{label} must be {lo}-{hi} characters"


# ------------------------------------------------------------------ users --
def validate_name(name: str, errors: dict):
    _length(name, "name", errors, 2, 80, "Name")
    if name and not re.fullmatch(r"[A-Za-z .'-]+", name):
        errors["name"] = "Name can only contain letters, spaces, . ' -"


def validate_password(password: str, errors: dict, key: str = "password"):
    if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        errors[key] = "Password needs 8+ characters with at least one letter and one number"


def validate_registration(data: dict) -> dict:
    errors: dict[str, str] = {}
    name = _text(data, "name")
    email = _text(data, "email").lower()
    password = data.get("password") or ""
    department = _text(data, "department")

    validate_name(name, errors)
    if not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address"
    validate_password(password, errors)
    if password != (data.get("confirm_password") or ""):
        errors["confirm_password"] = "Passwords do not match"
    if len(department) > 60:
        errors["department"] = "Department must be at most 60 characters"

    if errors:
        raise ValidationError(errors)
    return {"name": name, "email": email, "password": password, "department": department or None}


def validate_profile(data: dict) -> dict:
    errors: dict[str, str] = {}
    name = _text(data, "name")
    department = _text(data, "department")
    new_password = data.get("new_password") or ""

    validate_name(name, errors)
    if len(department) > 60:
        errors["department"] = "Department must be at most 60 characters"
    if new_password:
        validate_password(new_password, errors, key="new_password")
        if new_password != (data.get("confirm_password") or ""):
            errors["confirm_password"] = "Passwords do not match"

    if errors:
        raise ValidationError(errors)
    return {"name": name, "department": department or None, "new_password": new_password or None}


# --------------------------------------------------------- certifications --
def validate_certification(data: dict, today: Optional[date] = None) -> dict:
    """Field rules + cross-field (business) rules for a certification."""
    today = today or date.today()
    errors: dict[str, str] = {}

    title = _text(data, "title")
    provider = _text(data, "provider")
    category = _text(data, "category")
    status_raw = _text(data, "status") or Status.PLANNED.value
    credential_id = _text(data, "credential_id")
    credential_url = _text(data, "credential_url")
    notes = _text(data, "notes")

    _length(title, "title", errors, 3, 120, "Title")
    _length(provider, "provider", errors, 2, 60, "Provider")
    if category not in CATEGORIES:
        errors["category"] = "Choose a category from the list"
    if status_raw not in Status.values():
        errors["status"] = "Invalid status"
    status = Status(status_raw) if status_raw in Status.values() else Status.PLANNED

    progress = _parse_int(data, "progress", errors, 0, 100, default=0)
    start = _parse_date(data, "start_date", errors)
    target = _parse_date(data, "target_date", errors)
    completed = _parse_date(data, "completed_date", errors)
    expiry = _parse_date(data, "expiry_date", errors)

    if credential_url and not URL_RE.match(credential_url):
        errors["credential_url"] = "Must start with http:// or https://"
    if len(credential_id) > 80:
        errors["credential_id"] = "Credential ID must be at most 80 characters"
    if len(notes) > 1000:
        errors["notes"] = "Notes must be at most 1000 characters"

    # --- business rules ---------------------------------------------------
    # (a future start date is allowed - students plan ahead)
    if start and target and target < start:
        errors["target_date"] = "Target date cannot be before the start date"

    if status == Status.COMPLETED:
        if not completed:
            errors["completed_date"] = "Completed certifications need a completion date"
        progress = 100  # completed always means 100 %
    else:
        if completed:
            errors["completed_date"] = "Only completed certifications can have a completion date"
        if expiry:
            errors["expiry_date"] = "Expiry date only applies to completed certifications"
        if status == Status.PLANNED and progress and progress > 0:
            errors["progress"] = "A planned certification must have 0% progress (set it In Progress)"
        if progress == 100 and status != Status.DROPPED:
            errors["progress"] = "100% progress means completed - change the status to Completed"

    if completed and completed > today:
        errors["completed_date"] = "Completion date cannot be in the future"
    if completed and start and completed < start:
        errors["completed_date"] = "Completion date cannot be before the start date"
    if completed and expiry and expiry <= completed:
        errors["expiry_date"] = "Expiry date must be after the completion date"

    if errors:
        raise ValidationError(errors)

    return {
        "title": title,
        "provider": provider,
        "category": category,
        "status": status,
        "progress": progress,
        "start_date": start,
        "target_date": target,
        "completed_date": completed,
        "expiry_date": expiry,
        "credential_id": credential_id or None,
        "credential_url": credential_url or None,
        "notes": notes or None,
    }


def validate_progress_log(data: dict, current_progress: int, today: Optional[date] = None) -> dict:
    today = today or date.today()
    errors: dict[str, str] = {}

    log_date = _parse_date(data, "log_date", errors) or (today if not _text(data, "log_date") else None)
    note = _text(data, "note")

    hours_raw = _text(data, "hours")
    hours = None
    try:
        hours = float(hours_raw)
        if not 0 < hours <= 24:
            errors["hours"] = "Hours must be more than 0 and at most 24"
    except ValueError:
        errors["hours"] = "Enter hours as a number, e.g. 1.5"

    progress = _parse_int(data, "progress", errors, 0, 100)
    if progress is not None and "progress" not in errors and progress < current_progress:
        errors["progress"] = f"Progress cannot go backwards (currently {current_progress}%)"
    if log_date and log_date > today:
        errors["log_date"] = "You cannot log study time in the future"
    if len(note) > 300:
        errors["note"] = "Note must be at most 300 characters"

    if errors:
        raise ValidationError(errors)
    return {"log_date": log_date, "hours": round(hours, 2), "progress": progress, "note": note or None}
