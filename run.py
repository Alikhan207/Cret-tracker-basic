"""Entry point.

    python run.py           start the app (creates an EMPTY database on first run)
    python run.py --demo    wipe the database and load sample data (for demos/viva)
    python run.py --fresh   wipe the database and start empty
"""
import argparse
import os

from app import create_app
from app.db import connect, init_db
from app.seed import seed

app = create_app()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Certification Progress Tracker")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--demo", action="store_true", help="reset DB and load sample data")
    group.add_argument("--fresh", action="store_true", help="reset DB to empty")
    args = parser.parse_args()

    db_path = app.config["DATABASE"]
    if args.demo or args.fresh or not os.path.exists(db_path):
        conn = connect(db_path)
        init_db(conn)
        if args.demo:
            seed(conn)
            print("Database reset with demo data (ali@cmrit.ac.in / Student@123, mentor@cmrit.ac.in / Mentor@123).")
        else:
            print("Created an empty database. Register an account at http://127.0.0.1:5000/register")
            print("To add a mentor:  flask --app run create-mentor")
        conn.close()

    # use_reloader=False so --demo/--fresh don't run twice in debug mode
    app.run(debug=True, use_reloader=not (args.demo or args.fresh))
