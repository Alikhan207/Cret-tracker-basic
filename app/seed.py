"""Demo data so the app is not empty during the demo / viva."""
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from .repositories import CertificationRepository, ProgressLogRepository, UserRepository
from .models import Status


def seed(db, today: date | None = None):
    today = today or date.today()
    d = lambda days: today + timedelta(days=days)  # noqa: E731

    users = UserRepository(db)
    mentor = users.create("Prof Demo Mentor", "mentor@cmrit.ac.in", generate_password_hash("Mentor@123"),
                          "mentor", "AI & DS")
    ali = users.create("Mohammed Ali Khan", "ali@cmrit.ac.in", generate_password_hash("Student@123"),
                       "student", "AI & DS")
    riya = users.create("Riya Sharma", "riya@cmrit.ac.in", generate_password_hash("Student@123"),
                        "student", "CSE")
    users.create("Arjun Rao", "arjun@cmrit.ac.in", generate_password_hash("Student@123"), "student", "ISE")

    certs = CertificationRepository(db)
    logs = ProgressLogRepository(db)

    def add(user_id, title, provider, category, status, progress, start=None, target=None,
            completed=None, expiry=None, cred_id=None, url=None, notes=None, log_rows=()):
        cid = certs.create(user_id, {
            "title": title, "provider": provider, "category": category, "status": status,
            "progress": progress, "start_date": start, "target_date": target,
            "completed_date": completed, "expiry_date": expiry, "credential_id": cred_id,
            "credential_url": url, "notes": notes,
        })
        for log_date, hours, prog, note in log_rows:
            logs.add(cid, {"log_date": log_date, "hours": hours, "progress": prog, "note": note})
        db.commit()
        return cid

    add(ali, "AWS Certified Cloud Practitioner", "AWS", "Cloud", Status.COMPLETED, 100,
        d(-120), d(-60), d(-70), d(20), "AWS-CCP-48213", "https://www.credly.com/badges/demo",
        "Renewal due soon", [(d(-110), 2, 20, "Cloud concepts"), (d(-90), 3, 60, "Billing + security"),
                             (d(-70), 2.5, 100, "Passed exam")])
    add(ali, "Google Cloud Generative AI Leader", "Google Cloud", "AI/ML", Status.IN_PROGRESS, 45,
        d(-20), d(25), notes="Part of GSA plan",
        log_rows=[(d(-18), 1.5, 15, "Intro modules"), (d(-5), 2, 45, "Prompt design")])
    add(ali, "Oracle Database SQL Associate", "Oracle", "Data", Status.IN_PROGRESS, 30,
        d(-40), d(-3), notes="Deadline slipped",
        log_rows=[(d(-35), 2, 30, "Joins and subqueries")])
    add(ali, "Certified Kubernetes Application Developer", "CNCF", "Cloud", Status.PLANNED, 0, None, d(90))
    add(riya, "Microsoft Azure Fundamentals AZ-900", "Microsoft", "Cloud", Status.COMPLETED, 100,
        d(-200), d(-150), d(-160), None, "AZ900-7731")
    add(riya, "Cisco CCNA", "Cisco", "Networking", Status.IN_PROGRESS, 60, d(-60), d(-10),
        log_rows=[(d(-50), 3, 30, "Subnetting"), (d(-20), 2, 60, "Routing")])
    add(riya, "CompTIA Security+", "CompTIA", "Security", Status.DROPPED, 10, d(-90), d(-30),
        notes="Switched focus to CCNA")
    return mentor
