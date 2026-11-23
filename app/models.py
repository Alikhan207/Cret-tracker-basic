"""Domain models (OOP layer).

Each table row is turned into a Python object so the rest of the code works
with `cert.is_overdue()` instead of raw tuples. Behaviour that belongs to a
certification (is it overdue? expiring?) lives on the class itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

CATEGORIES = ("Cloud", "AI/ML", "Data", "Security", "Programming", "Networking", "Other")
EXPIRY_WARNING_DAYS = 30


class Status(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DROPPED = "dropped"

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").title()

    @classmethod
    def values(cls) -> list[str]:
        return [s.value for s in cls]


class Role(str, Enum):
    STUDENT = "student"
    MENTOR = "mentor"


def to_date(value) -> Optional[date]:
    """Convert an ISO string from the database into a date (or None)."""
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


@dataclass
class User:
    id: Optional[int]
    name: str
    email: str
    role: Role = Role.STUDENT
    department: Optional[str] = None
    password_hash: str = field(default="", repr=False)  # never printed / serialised

    @property
    def is_mentor(self) -> bool:
        return self.role == Role.MENTOR

    @classmethod
    def from_row(cls, row) -> "User":
        return cls(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            role=Role(row["role"]),
            department=row["department"],
            password_hash=row["password_hash"],
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role.value,
            "department": self.department,
        }


@dataclass
class Certification:
    id: Optional[int]
    user_id: int
    title: str
    provider_name: str
    category: str
    status: Status = Status.PLANNED
    progress: int = 0
    start_date: Optional[date] = None
    target_date: Optional[date] = None
    completed_date: Optional[date] = None
    expiry_date: Optional[date] = None
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None
    notes: Optional[str] = None
    owner_name: Optional[str] = None
    updated_at: Optional[str] = None

    # ---- behaviour -------------------------------------------------------
    @property
    def is_active(self) -> bool:
        return self.status in (Status.PLANNED, Status.IN_PROGRESS)

    def is_overdue(self, today: Optional[date] = None) -> bool:
        today = today or date.today()
        return self.is_active and self.target_date is not None and self.target_date < today

    def days_to_expiry(self, today: Optional[date] = None) -> Optional[int]:
        if self.status != Status.COMPLETED or self.expiry_date is None:
            return None
        return (self.expiry_date - (today or date.today())).days

    def is_expired(self, today: Optional[date] = None) -> bool:
        days = self.days_to_expiry(today)
        return days is not None and days < 0

    def is_expiring_soon(self, today: Optional[date] = None) -> bool:
        days = self.days_to_expiry(today)
        return days is not None and 0 <= days <= EXPIRY_WARNING_DAYS

    def health(self, today: Optional[date] = None) -> str:
        """One short label the UI shows as a coloured badge."""
        if self.status == Status.DROPPED:
            return "Dropped"
        if self.is_expired(today):
            return "Expired"
        if self.is_expiring_soon(today):
            return "Expiring soon"
        if self.status == Status.COMPLETED:
            return "Done"
        if self.is_overdue(today):
            return "Overdue"
        return "On track"

    # ---- conversion ------------------------------------------------------
    @classmethod
    def from_row(cls, row) -> "Certification":
        keys = row.keys()
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            provider_name=row["provider_name"],
            category=row["category"],
            status=Status(row["status"]),
            progress=row["progress"],
            start_date=to_date(row["start_date"]),
            target_date=to_date(row["target_date"]),
            completed_date=to_date(row["completed_date"]),
            expiry_date=to_date(row["expiry_date"]),
            credential_id=row["credential_id"],
            credential_url=row["credential_url"],
            notes=row["notes"],
            owner_name=row["owner_name"] if "owner_name" in keys else None,
            updated_at=row["updated_at"],
        )

    def to_dict(self, today: Optional[date] = None) -> dict:
        iso = lambda d: d.isoformat() if d else None  # noqa: E731
        return {
            "id": self.id,
            "user_id": self.user_id,
            "owner_name": self.owner_name,
            "title": self.title,
            "provider": self.provider_name,
            "category": self.category,
            "status": self.status.value,
            "progress": self.progress,
            "start_date": iso(self.start_date),
            "target_date": iso(self.target_date),
            "completed_date": iso(self.completed_date),
            "expiry_date": iso(self.expiry_date),
            "credential_id": self.credential_id,
            "credential_url": self.credential_url,
            "notes": self.notes,
            "health": self.health(today),
        }


@dataclass
class ProgressLog:
    id: Optional[int]
    certification_id: int
    log_date: date
    hours: float
    progress: int
    note: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "ProgressLog":
        return cls(
            id=row["id"],
            certification_id=row["certification_id"],
            log_date=to_date(row["log_date"]),
            hours=row["hours"],
            progress=row["progress"],
            note=row["note"],
        )
