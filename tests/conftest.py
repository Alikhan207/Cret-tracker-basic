import pytest

from app import create_app
from app.db import connect, init_db
from app.seed import seed


@pytest.fixture
def app(tmp_path):
    db_path = str(tmp_path / "test.sqlite")
    conn = connect(db_path)
    init_db(conn)
    seed(conn)
    conn.close()
    app = create_app({"TESTING": True, "DATABASE": db_path, "CSRF_ENABLED": False, "SECRET_KEY": "test"})
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    """A raw connection for service-level tests (no HTTP involved)."""
    conn = connect(app.config["DATABASE"])
    yield conn
    conn.close()


def login(client, email="ali@cmrit.ac.in", password="Student@123"):
    return client.post("/login", data={"email": email, "password": password})


@pytest.fixture
def student(client):
    login(client)
    return client


@pytest.fixture
def mentor(client):
    login(client, "mentor@cmrit.ac.in", "Mentor@123")
    return client
