"""Service layer: business logic and access control.

Routes (web + API) call services; services call repositories. Nothing in
here knows about HTTP, which is why it is easy to unit test.
"""
from __future__ import annotations

import heapq
from collections import Counter, defaultdict
from datetime import date
from typing import Optional

from werkzeug.security import check_password_hash, generate_password_hash

from .exceptions import AuthenticationError, NotFoundError, PermissionDenied
from .models import Certification, Status, User
from .repositories import (
    CertificationRepository,
    ProgressLogRepository,
    ProviderRepository,
    ReportRepository,
    UserRepository,
)
from .validators import (
    validate_certification,
    validate_profile,
    validate_progress_log,
    validate_registration,
)


class AuthService:
    def __init__(self, db):
        self.users = UserRepository(db)

    def register(self, form: dict, role: str = "student") -> int:
        data = validate_registration(form)
        return self.users.create(
            data["name"], data["email"], generate_password_hash(data["password"]), role, data["department"]
        )

    def authenticate(self, email: str, password: str) -> User:
        user = self.users.get_by_email((email or "").strip())
        # Same message for "no such user" and "wrong password" so attackers
        # cannot discover which emails are registered.
        if not user or not check_password_hash(user.password_hash, password or ""):
            raise AuthenticationError("Invalid email or password")
        return user

    def update_profile(self, user: User, form: dict) -> None:
        data = validate_profile(form)
        self.users.update_profile(user.id, data["name"], data["department"])
        if data["new_password"]:
            self.users.update_password(user.id, generate_password_hash(data["new_password"]))


class CertificationService:
    def __init__(self, db):
        self.db = db
        self.certs = CertificationRepository(db)
        self.logs = ProgressLogRepository(db)
        self.providers = ProviderRepository(db)

    # ---------------------------------------------------------- access --
    def _load(self, cert_id: int) -> Certification:
        cert = self.certs.get(cert_id)
        if cert is None:
            raise NotFoundError("Certification not found")
        return cert

    def get_for_view(self, user: User, cert_id: int) -> Certification:
        """Owners and mentors may view."""
        cert = self._load(cert_id)
        if cert.user_id != user.id and not user.is_mentor:
            raise PermissionDenied("You can only view your own certifications")
        return cert

    def get_for_edit(self, user: User, cert_id: int) -> Certification:
        """Only the owner may change a record - mentors are read-only."""
        cert = self._load(cert_id)
        if cert.user_id != user.id:
            raise PermissionDenied("Only the owner can modify this certification")
        return cert

    # ------------------------------------------------------------ CRUD --
    def create(self, user: User, form: dict) -> int:
        return self.certs.create(user.id, validate_certification(form))

    def update(self, user: User, cert_id: int, form: dict) -> None:
        self.get_for_edit(user, cert_id)
        self.certs.update(cert_id, validate_certification(form))

    def delete(self, user: User, cert_id: int) -> None:
        self.get_for_edit(user, cert_id)
        self.certs.delete(cert_id)

    def search(self, user: User, filters: dict) -> list[Certification]:
        """Students search their own records; mentors search everyone's."""
        return self.certs.search(
            user_id=None if user.is_mentor else user.id,
            q=(filters.get("q") or "").strip(),
            status=filters.get("status") or "",
            category=filters.get("category") or "",
            provider=filters.get("provider") or "",
            sort=filters.get("sort") or "target",
        )

    # -------------------------------------------------- progress logs --
    def log_progress(self, user: User, cert_id: int, form: dict, today: Optional[date] = None) -> None:
        """Add a study log and move the certification through its states:
        planned --(progress > 0)--> in_progress --(progress = 100)--> completed
        """
        cert = self.get_for_edit(user, cert_id)
        if cert.status in (Status.COMPLETED, Status.DROPPED):
            raise PermissionDenied(f"Cannot log progress on a {cert.status.label.lower()} certification")

        data = validate_progress_log(form, cert.progress, today)

        new_status, completed_date = cert.status, None
        if data["progress"] == 100:
            new_status, completed_date = Status.COMPLETED, data["log_date"]
        elif data["progress"] > 0 and cert.status == Status.PLANNED:
            new_status = Status.IN_PROGRESS

        # Both writes succeed or neither does (transaction).
        try:
            self.logs.add(cert_id, data)
            self.certs.apply_progress(cert_id, data["progress"], new_status, completed_date)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def logs_for(self, cert_id: int):
        return self.logs.list_for(cert_id)

    def hours_for(self, cert_id: int) -> float:
        return self.logs.total_hours(cert_id=cert_id)

    def provider_names(self) -> list[str]:
        return self.providers.list_names()

    # ------------------------------------------------------- dashboard --
    def dashboard(self, user: User, today: Optional[date] = None) -> dict:
        today = today or date.today()
        certs = self.certs.search(user_id=user.id)

        counts = Counter(c.status for c in certs)                    # status -> count
        by_category: dict[str, list[Certification]] = defaultdict(list)
        for c in certs:
            by_category[c.category].append(c)

        active = [c for c in certs if c.is_active and c.target_date]
        # heapq.nsmallest = "5 nearest deadlines" without sorting everything
        upcoming = heapq.nsmallest(5, (c for c in active if not c.is_overdue(today)), key=lambda c: c.target_date)
        overdue = sorted((c for c in active if c.is_overdue(today)), key=lambda c: c.target_date)
        expiring = [c for c in certs if c.is_expiring_soon(today) or c.is_expired(today)]

        countable = [c for c in certs if c.status != Status.DROPPED]
        completed = counts[Status.COMPLETED]
        return {
            "total": len(certs),
            "counts": {s: counts.get(s, 0) for s in Status},
            "completion_rate": round(100 * completed / len(countable)) if countable else 0,
            "avg_progress": round(sum(c.progress for c in countable) / len(countable)) if countable else 0,
            "hours": self.logs.total_hours(user_id=user.id),
            "upcoming": upcoming,
            "overdue": overdue,
            "expiring": expiring,
            "by_category": dict(sorted(by_category.items(), key=lambda kv: -len(kv[1]))),
        }


class ReportService:
    def __init__(self, db):
        self.reports = ReportRepository(db)
        self.certs = CertificationRepository(db)

    def mentor_report(self, user: User, today: Optional[date] = None) -> dict:
        if not user.is_mentor:
            raise PermissionDenied("Reports are only available to mentors")
        today = today or date.today()
        all_certs = self.certs.search(user_id=None)
        pending = [c for c in all_certs if c.is_overdue(today)]
        expiring = [c for c in all_certs if c.is_expiring_soon(today) or c.is_expired(today)]
        students = self.reports.student_summary(today)
        inactive = [s for s in students if s["total"] == 0]
        return {
            "students": students,
            "pending": sorted(pending, key=lambda c: c.target_date),
            "expiring": expiring,
            "inactive": inactive,
            "providers": self.reports.provider_popularity(),
            "totals": {
                "students": len(students),
                "certifications": len(all_certs),
                "completed": sum(1 for c in all_certs if c.status == Status.COMPLETED),
                "overdue": len(pending),
            },
        }
