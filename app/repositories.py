"""Repository layer: the ONLY place that contains SQL.

Every query uses `?` placeholders (parameterised queries), so user input is
never concatenated into SQL - this is what prevents SQL injection.
"""
from __future__ import annotations

import sqlite3
from datetime import date
from typing import Optional

from .exceptions import DuplicateError
from .models import Certification, ProgressLog, Status, User


def _iso(d: Optional[date]) -> Optional[str]:
    return d.isoformat() if d else None


class UserRepository:
    def __init__(self, db: sqlite3.Connection):
        self.db = db

    def create(self, name, email, password_hash, role="student", department=None) -> int:
        try:
            cur = self.db.execute(
                "INSERT INTO users (name, email, password_hash, role, department) VALUES (?, ?, ?, ?, ?)",
                (name, email, password_hash, role, department),
            )
        except sqlite3.IntegrityError:
            raise DuplicateError("An account with this email already exists")
        self.db.commit()
        return cur.lastrowid

    def get(self, user_id: int) -> Optional[User]:
        row = self.db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return User.from_row(row) if row else None

    def get_by_email(self, email: str) -> Optional[User]:
        row = self.db.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
        return User.from_row(row) if row else None

    def update_profile(self, user_id: int, name: str, department: Optional[str]):
        self.db.execute("UPDATE users SET name = ?, department = ? WHERE id = ?", (name, department, user_id))
        self.db.commit()

    def update_password(self, user_id: int, password_hash: str):
        self.db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
        self.db.commit()


class ProviderRepository:
    def __init__(self, db: sqlite3.Connection):
        self.db = db

    def get_or_create(self, name: str) -> int:
        row = self.db.execute("SELECT id FROM providers WHERE name = ? COLLATE NOCASE", (name,)).fetchone()
        if row:
            return row["id"]
        return self.db.execute("INSERT INTO providers (name) VALUES (?)", (name,)).lastrowid

    def list_names(self) -> list[str]:
        return [r["name"] for r in self.db.execute("SELECT name FROM providers ORDER BY name")]


class CertificationRepository:
    BASE_SELECT = """
        SELECT c.*, p.name AS provider_name, u.name AS owner_name
        FROM certifications c
        JOIN providers p ON p.id = c.provider_id
        JOIN users u     ON u.id = c.user_id
    """
    # Whitelist for ORDER BY - column names cannot be parameterised with "?",
    # so we only ever insert one of these fixed strings.
    SORTS = {
        "target": "c.target_date IS NULL, c.target_date ASC",
        "updated": "c.updated_at DESC",
        "progress": "c.progress DESC",
        "title": "c.title COLLATE NOCASE ASC",
    }

    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.providers = ProviderRepository(db)

    def _values(self, data: dict) -> tuple:
        return (
            data["title"], data["category"], data["status"].value, data["progress"],
            _iso(data["start_date"]), _iso(data["target_date"]),
            _iso(data["completed_date"]), _iso(data["expiry_date"]),
            data["credential_id"], data["credential_url"], data["notes"],
        )

    def create(self, user_id: int, data: dict) -> int:
        provider_id = self.providers.get_or_create(data["provider"])
        try:
            cur = self.db.execute(
                """INSERT INTO certifications
                   (title, category, status, progress, start_date, target_date, completed_date,
                    expiry_date, credential_id, credential_url, notes, user_id, provider_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                self._values(data) + (user_id, provider_id),
            )
        except sqlite3.IntegrityError:
            self.db.rollback()
            raise DuplicateError("You are already tracking this certification from this provider")
        self.db.commit()
        return cur.lastrowid

    def update(self, cert_id: int, data: dict):
        provider_id = self.providers.get_or_create(data["provider"])
        try:
            self.db.execute(
                """UPDATE certifications SET
                   title = ?, category = ?, status = ?, progress = ?, start_date = ?, target_date = ?,
                   completed_date = ?, expiry_date = ?, credential_id = ?, credential_url = ?, notes = ?,
                   provider_id = ?, updated_at = datetime('now')
                   WHERE id = ?""",
                self._values(data) + (provider_id, cert_id),
            )
        except sqlite3.IntegrityError:
            self.db.rollback()
            raise DuplicateError("You are already tracking this certification from this provider")
        self.db.commit()

    def delete(self, cert_id: int):
        self.db.execute("DELETE FROM certifications WHERE id = ?", (cert_id,))
        self.db.commit()

    def get(self, cert_id: int) -> Optional[Certification]:
        row = self.db.execute(self.BASE_SELECT + " WHERE c.id = ?", (cert_id,)).fetchone()
        return Certification.from_row(row) if row else None

    def search(self, user_id: Optional[int] = None, q: str = "", status: str = "",
               category: str = "", provider: str = "", sort: str = "target") -> list[Certification]:
        """Build a WHERE clause from whichever filters were supplied."""
        clauses, params = [], []
        if user_id is not None:
            clauses.append("c.user_id = ?")
            params.append(user_id)
        if q:
            clauses.append("(c.title LIKE ? OR p.name LIKE ? OR c.notes LIKE ? OR c.credential_id LIKE ?)")
            params.extend([f"%{q}%"] * 4)
        if status:
            clauses.append("c.status = ?")
            params.append(status)
        if category:
            clauses.append("c.category = ?")
            params.append(category)
        if provider:
            clauses.append("p.name = ? COLLATE NOCASE")
            params.append(provider)

        sql = self.BASE_SELECT
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY " + self.SORTS.get(sort, self.SORTS["target"])
        return [Certification.from_row(r) for r in self.db.execute(sql, params)]

    def apply_progress(self, cert_id: int, progress: int, status: Status, completed_date: Optional[date]):
        self.db.execute(
            """UPDATE certifications
               SET progress = ?, status = ?, completed_date = COALESCE(?, completed_date),
                   updated_at = datetime('now')
               WHERE id = ?""",
            (progress, status.value, _iso(completed_date), cert_id),
        )


class ProgressLogRepository:
    def __init__(self, db: sqlite3.Connection):
        self.db = db

    def add(self, cert_id: int, data: dict) -> int:
        cur = self.db.execute(
            "INSERT INTO progress_logs (certification_id, log_date, hours, progress, note) VALUES (?, ?, ?, ?, ?)",
            (cert_id, _iso(data["log_date"]), data["hours"], data["progress"], data["note"]),
        )
        return cur.lastrowid

    def list_for(self, cert_id: int) -> list[ProgressLog]:
        rows = self.db.execute(
            "SELECT * FROM progress_logs WHERE certification_id = ? ORDER BY log_date DESC, id DESC", (cert_id,)
        )
        return [ProgressLog.from_row(r) for r in rows]

    def total_hours(self, cert_id: Optional[int] = None, user_id: Optional[int] = None) -> float:
        sql = """SELECT COALESCE(SUM(l.hours), 0) AS total FROM progress_logs l
                 JOIN certifications c ON c.id = l.certification_id WHERE 1 = 1"""
        params = []
        if cert_id is not None:
            sql += " AND l.certification_id = ?"
            params.append(cert_id)
        if user_id is not None:
            sql += " AND c.user_id = ?"
            params.append(user_id)
        return float(self.db.execute(sql, params).fetchone()["total"])


class ReportRepository:
    """Aggregate queries for the mentor report (GROUP BY, CASE, LEFT JOIN)."""

    def __init__(self, db: sqlite3.Connection):
        self.db = db

    def student_summary(self, today: date) -> list[dict]:
        rows = self.db.execute(
            """
            SELECT u.id, u.name, u.email, u.department,
                   COUNT(c.id)                                              AS total,
                   SUM(CASE WHEN c.status = 'completed'   THEN 1 ELSE 0 END) AS completed,
                   SUM(CASE WHEN c.status = 'in_progress' THEN 1 ELSE 0 END) AS in_progress,
                   SUM(CASE WHEN c.status = 'planned'     THEN 1 ELSE 0 END) AS planned,
                   SUM(CASE WHEN c.status IN ('planned', 'in_progress')
                             AND c.target_date < ? THEN 1 ELSE 0 END)       AS overdue,
                   ROUND(AVG(CASE WHEN c.status != 'dropped' THEN c.progress END), 1) AS avg_progress,
                   (SELECT COALESCE(SUM(l.hours), 0) FROM progress_logs l
                      JOIN certifications c2 ON c2.id = l.certification_id
                     WHERE c2.user_id = u.id)                                AS hours,
                   MAX(c.updated_at)                                         AS last_activity
            FROM users u
            LEFT JOIN certifications c ON c.user_id = u.id
            WHERE u.role = 'student'
            GROUP BY u.id
            ORDER BY overdue DESC, u.name
            """,
            (today.isoformat(),),
        )
        return [dict(r) for r in rows]

    def provider_popularity(self) -> list[dict]:
        rows = self.db.execute(
            """SELECT p.name, COUNT(c.id) AS total,
                      SUM(CASE WHEN c.status = 'completed' THEN 1 ELSE 0 END) AS completed
               FROM providers p JOIN certifications c ON c.provider_id = p.id
               GROUP BY p.id ORDER BY total DESC, p.name LIMIT 8"""
        )
        return [dict(r) for r in rows]
