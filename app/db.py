"""Database connection handling (one SQLite connection per request)."""
import sqlite3
from pathlib import Path

import click
from flask import current_app, g

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row          # rows behave like dicts: row["title"]
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite has FKs off by default!
    return conn


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(conn: sqlite3.Connection):
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()


@click.command("init-db")
def init_db_command():
    """Drop and recreate all tables."""
    init_db(get_db())
    click.echo("Database initialised.")


@click.command("seed")
def seed_command():
    """Recreate tables and load demo data."""
    from .seed import seed
    db = get_db()
    init_db(db)
    seed(db)
    click.echo("Demo data loaded. Log in as mentor@cmrit.ac.in / Mentor@123 or ali@cmrit.ac.in / Student@123")


@click.command("create-mentor")
@click.option("--name", prompt=True)
@click.option("--email", prompt=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
def create_mentor_command(name, email, password):
    """Mentors cannot self-register; an admin creates them from the CLI."""
    from .services import AuthService
    AuthService(get_db()).register(
        {"name": name, "email": email, "password": password, "confirm_password": password},
        role="mentor",
    )
    click.echo(f"Mentor {email} created.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_command)
    app.cli.add_command(create_mentor_command)
