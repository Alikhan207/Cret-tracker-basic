"""End-to-end tests through HTTP (Flask test client)."""
from conftest import login


# ------------------------------------------------------------------- web --
def test_pages_require_login(client):
    r = client.get("/certifications")
    assert r.status_code == 302 and "/login" in r.location


def test_register_then_login(client):
    r = client.post("/register", data={"name": "New Student", "email": "new@cmrit.ac.in",
                                       "password": "Passw0rd", "confirm_password": "Passw0rd"})
    assert r.status_code == 302
    assert login(client, "new@cmrit.ac.in", "Passw0rd").status_code == 302


def test_register_shows_errors(client):
    r = client.post("/register", data={"name": "", "email": "bad", "password": "x", "confirm_password": "y"})
    assert r.status_code == 200 and b"Enter a valid email address" in r.data


def test_create_edit_delete_flow(student):
    r = student.post("/certifications/new", data={"title": "MongoDB Associate", "provider": "MongoDB",
                                                  "category": "Data", "status": "planned", "progress": "0"})
    assert r.status_code == 302
    detail = r.location
    assert b"MongoDB Associate" in student.get(detail).data

    cert_id = detail.rstrip("/").split("/")[-1]
    r = student.post(f"/certifications/{cert_id}/edit", data={"title": "MongoDB Associate Developer",
                     "provider": "MongoDB", "category": "Data", "status": "in_progress", "progress": "20"})
    assert r.status_code == 302
    assert b"MongoDB Associate Developer" in student.get(detail).data

    assert student.post(f"/certifications/{cert_id}/delete").status_code == 302
    assert student.get(detail).status_code == 404


def test_search_filter(student):
    r = student.get("/certifications?status=completed")
    assert b"AWS Certified Cloud Practitioner" in r.data
    assert b"Oracle Database" not in r.data


def test_student_blocked_from_reports_and_other_records(student):
    assert student.get("/reports").status_code == 302
    assert student.get("/certifications/5").status_code == 403      # Riya's record


def test_mentor_report_and_csv(mentor):
    assert b"Pending work" in mentor.get("/reports").data
    r = mentor.get("/reports/export.csv")
    assert r.mimetype == "text/csv" and b"Cisco CCNA" in r.data


def test_csrf_blocks_forged_post(app):
    app.config["CSRF_ENABLED"] = True
    client = app.test_client()
    r = client.post("/login", data={"email": "ali@cmrit.ac.in", "password": "Student@123"})
    assert r.status_code == 400


# ------------------------------------------------------------------- API --
def test_api_requires_login(client):
    assert client.get("/api/certifications").status_code == 401


def test_api_crud(client):
    assert client.post("/api/login", json={"email": "ali@cmrit.ac.in", "password": "Student@123"}).status_code == 200

    r = client.post("/api/certifications", json={"title": "Databricks Data Engineer", "provider": "Databricks",
                                                 "category": "Data", "status": "planned"})
    assert r.status_code == 201
    cid = r.get_json()["id"]

    r = client.put(f"/api/certifications/{cid}", json={"title": "Databricks Data Engineer", "provider": "Databricks",
                                                       "category": "Data", "status": "in_progress", "progress": 10})
    assert r.status_code == 200 and r.get_json()["progress"] == 10

    r = client.post(f"/api/certifications/{cid}/logs", json={"hours": 1.5, "progress": 35})
    assert r.status_code == 201 and r.get_json()["progress"] == 35

    assert client.get("/api/certifications?q=databricks").get_json()["count"] == 1
    assert client.delete(f"/api/certifications/{cid}").status_code == 204
    assert client.get(f"/api/certifications/{cid}").status_code == 404


def test_api_validation_errors_are_json(client):
    client.post("/api/login", json={"email": "ali@cmrit.ac.in", "password": "Student@123"})
    r = client.post("/api/certifications", json={"title": "x"})
    body = r.get_json()
    assert r.status_code == 400 and "title" in body["fields"] and "category" in body["fields"]
    assert client.post("/api/certifications", data="not json").status_code == 400


def test_api_duplicate_is_409(client):
    client.post("/api/login", json={"email": "ali@cmrit.ac.in", "password": "Student@123"})
    r = client.post("/api/certifications", json={"title": "AWS Certified Cloud Practitioner", "provider": "AWS",
                                                 "category": "Cloud", "status": "planned"})
    assert r.status_code == 409


def test_api_stats(client):
    client.post("/api/login", json={"email": "ali@cmrit.ac.in", "password": "Student@123"})
    body = client.get("/api/stats").get_json()
    assert body["total"] == 4 and body["by_status"]["completed"] == 1
