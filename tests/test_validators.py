"""Unit tests for validation rules (no database, no web server)."""
from datetime import date

import pytest

from app.exceptions import ValidationError
from app.models import Status
from app.validators import validate_certification, validate_progress_log, validate_registration

TODAY = date(2026, 11, 23)


def cert(**overrides):
    data = {"title": "AWS Cloud Practitioner", "provider": "AWS", "category": "Cloud",
            "status": "in_progress", "progress": "40", "start_date": "2026-10-01", "target_date": "2026-12-15"}
    data.update(overrides)
    return data


def errors_of(fn, *args, **kwargs) -> dict:
    with pytest.raises(ValidationError) as exc:
        fn(*args, **kwargs)
    return exc.value.errors


# ---------------------------------------------------------------- happy path
def test_valid_certification_is_cleaned():
    out = validate_certification(cert(title="  AWS Cloud Practitioner  "), TODAY)
    assert out["title"] == "AWS Cloud Practitioner"
    assert out["status"] is Status.IN_PROGRESS
    assert out["progress"] == 40
    assert out["target_date"] == date(2026, 12, 15)


def test_completed_forces_progress_to_100():
    out = validate_certification(cert(status="completed", progress="70", completed_date="2026-11-01"), TODAY)
    assert out["progress"] == 100


# ------------------------------------------------------------- field rules
@pytest.mark.parametrize("field,value", [
    ("title", "AB"),             # too short
    ("title", "x" * 121),        # too long
    ("provider", ""),            # required
    ("category", "Cooking"),     # not in list
    ("status", "finished"),      # not an allowed status
    ("progress", "150"),         # out of range
    ("progress", "abc"),         # not a number
    ("target_date", "15/12/2026"),  # wrong date format
    ("credential_url", "ftp://x.com"),
])
def test_field_rules(field, value):
    assert field in errors_of(validate_certification, cert(**{field: value}), TODAY)


# ---------------------------------------------------------- business rules
def test_target_before_start_rejected():
    errs = errors_of(validate_certification, cert(start_date="2026-12-01", target_date="2026-11-01"), TODAY)
    assert "target_date" in errs


def test_completed_needs_completion_date():
    assert "completed_date" in errors_of(validate_certification, cert(status="completed"), TODAY)


def test_completion_date_cannot_be_in_future():
    errs = errors_of(validate_certification, cert(status="completed", completed_date="2026-12-01"), TODAY)
    assert "completed_date" in errs


def test_expiry_must_be_after_completion():
    errs = errors_of(validate_certification,
                     cert(status="completed", completed_date="2026-11-01", expiry_date="2026-10-01"), TODAY)
    assert "expiry_date" in errs


def test_planned_cannot_have_progress():
    assert "progress" in errors_of(validate_certification, cert(status="planned", progress="20"), TODAY)


def test_all_errors_reported_at_once():
    errs = errors_of(validate_certification, {"title": "", "provider": "", "category": ""}, TODAY)
    assert {"title", "provider", "category"} <= errs.keys()


# ------------------------------------------------------------ progress log
def test_progress_cannot_go_backwards():
    errs = errors_of(validate_progress_log, {"hours": "1", "progress": "30"}, 50, TODAY)
    assert "progress" in errs


@pytest.mark.parametrize("hours", ["0", "-1", "25", "two"])
def test_invalid_hours(hours):
    assert "hours" in errors_of(validate_progress_log, {"hours": hours, "progress": "60"}, 50, TODAY)


def test_log_in_future_rejected():
    errs = errors_of(validate_progress_log, {"hours": "1", "progress": "60", "log_date": "2026-12-01"}, 50, TODAY)
    assert "log_date" in errs


# -------------------------------------------------------------- registration
def test_weak_password_and_bad_email():
    errs = errors_of(validate_registration, {"name": "Ali", "email": "not-an-email",
                                             "password": "short", "confirm_password": "short"})
    assert {"email", "password"} <= errs.keys()


def test_password_mismatch():
    errs = errors_of(validate_registration, {"name": "Ali Khan", "email": "a@b.com",
                                             "password": "Secret123", "confirm_password": "Secret124"})
    assert "confirm_password" in errs
