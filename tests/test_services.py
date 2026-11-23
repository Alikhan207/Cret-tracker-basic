"""Service-layer tests: business logic + access control against a real (temp) database."""
from datetime import date, timedelta

import pytest

from app.exceptions import AuthenticationError, DuplicateError, PermissionDenied
from app.models import Certification, Status
from app.repositories import UserRepository
from app.services import AuthService, CertificationService, ReportService


@pytest.fixture
def users(db):
    repo = UserRepository(db)
    return {
        "ali": repo.get_by_email("ali@cmrit.ac.in"),
        "riya": repo.get_by_email("riya@cmrit.ac.in"),
        "mentor": repo.get_by_email("mentor@cmrit.ac.in"),
    }


def test_password_is_hashed_and_login_works(db):
    AuthService(db).register({"name": "Test User", "email": "Test@X.com",
                              "password": "Passw0rd", "confirm_password": "Passw0rd"})
    user = UserRepository(db).get_by_email("test@x.com")
    assert user.password_hash != "Passw0rd"            # never stored in plain text
    assert AuthService(db).authenticate("test@x.com", "Passw0rd").id == user.id


def test_wrong_password_rejected(db):
    with pytest.raises(AuthenticationError):
        AuthService(db).authenticate("ali@cmrit.ac.in", "wrong")


def test_duplicate_email_rejected(db):
    with pytest.raises(DuplicateError):
        AuthService(db).register({"name": "Another Ali", "email": "ali@cmrit.ac.in",
                                  "password": "Passw0rd", "confirm_password": "Passw0rd"})


def test_create_and_search(db, users):
    svc = CertificationService(db)
    svc.create(users["ali"], {"title": "Terraform Associate", "provider": "HashiCorp",
                              "category": "Cloud", "status": "planned"})
    found = svc.search(users["ali"], {"q": "terraform"})
    assert [c.title for c in found] == ["Terraform Associate"]


def test_duplicate_certification_rejected_case_insensitive_provider(db, users):
    svc = CertificationService(db)
    with pytest.raises(DuplicateError):
        svc.create(users["ali"], {"title": "AWS Certified Cloud Practitioner", "provider": "aws",
                                  "category": "Cloud", "status": "planned"})


def test_student_only_sees_own_records(db, users):
    titles = {c.title for c in CertificationService(db).search(users["ali"], {})}
    assert "Cisco CCNA" not in titles                     # Riya's record
    mentor_titles = {c.title for c in CertificationService(db).search(users["mentor"], {})}
    assert "Cisco CCNA" in mentor_titles


def test_cannot_edit_someone_elses_record(db, users):
    svc = CertificationService(db)
    riya_cert = svc.search(users["riya"], {})[0]
    with pytest.raises(PermissionDenied):
        svc.delete(users["ali"], riya_cert.id)
    with pytest.raises(PermissionDenied):                 # mentors are read-only
        svc.delete(users["mentor"], riya_cert.id)


def test_progress_log_moves_planned_to_in_progress_then_completed(db, users):
    svc = CertificationService(db)
    cid = svc.create(users["ali"], {"title": "Python PCEP", "provider": "Python Institute",
                                    "category": "Programming", "status": "planned"})
    svc.log_progress(users["ali"], cid, {"hours": "2", "progress": "40"})
    assert svc.get_for_view(users["ali"], cid).status is Status.IN_PROGRESS

    svc.log_progress(users["ali"], cid, {"hours": "3", "progress": "100"})
    cert = svc.get_for_view(users["ali"], cid)
    assert cert.status is Status.COMPLETED and cert.completed_date == date.today()
    assert svc.hours_for(cid) == 5


def test_cannot_log_on_completed(db, users):
    svc = CertificationService(db)
    done = next(c for c in svc.search(users["ali"], {}) if c.status is Status.COMPLETED)
    with pytest.raises(PermissionDenied):
        svc.log_progress(users["ali"], done.id, {"hours": "1", "progress": "100"})


def test_dashboard_numbers(db, users):
    d = CertificationService(db).dashboard(users["ali"])
    assert d["total"] == 4
    assert d["counts"][Status.COMPLETED] == 1
    assert [c.title for c in d["overdue"]] == ["Oracle Database SQL Associate"]
    assert [c.title for c in d["expiring"]] == ["AWS Certified Cloud Practitioner"]
    assert d["hours"] == 13.0   # 2 + 3 + 2.5 + 1.5 + 2 + 2


def test_mentor_report_and_permission(db, users):
    report = ReportService(db).mentor_report(users["mentor"])
    assert report["totals"]["students"] == 3
    assert {c.title for c in report["pending"]} == {"Oracle Database SQL Associate", "Cisco CCNA"}
    assert [s["name"] for s in report["inactive"]] == ["Arjun Rao"]
    with pytest.raises(PermissionDenied):
        ReportService(db).mentor_report(users["ali"])


def test_model_health_labels():
    today = date(2026, 11, 23)
    base = dict(id=1, user_id=1, title="T", provider_name="P", category="Cloud")
    assert Certification(**base, status=Status.IN_PROGRESS, target_date=today - timedelta(days=1)).health(today) == "Overdue"
    assert Certification(**base, status=Status.IN_PROGRESS, target_date=today + timedelta(days=1)).health(today) == "On track"
    assert Certification(**base, status=Status.COMPLETED, expiry_date=today + timedelta(days=10)).health(today) == "Expiring soon"
    assert Certification(**base, status=Status.COMPLETED, expiry_date=today - timedelta(days=1)).health(today) == "Expired"
    assert Certification(**base, status=Status.COMPLETED).health(today) == "Done"
