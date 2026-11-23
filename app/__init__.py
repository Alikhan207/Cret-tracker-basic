"""Application factory."""
import os
import secrets
from pathlib import Path

from flask import Flask, abort, render_template, request, session

from . import db
from .exceptions import NotFoundError, PermissionDenied


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        DATABASE=os.environ.get("DATABASE", str(Path(app.instance_path) / "tracker.sqlite")),
        CSRF_ENABLED=True,
    )
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)

    from .auth import bp as auth_bp
    from .views import bp as views_bp
    from .api import bp as api_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp)

    # ---- CSRF protection for HTML forms (the JSON API is exempt) ---------
    def csrf_token() -> str:
        if "_csrf" not in session:
            session["_csrf"] = secrets.token_hex(16)
        return session["_csrf"]

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def check_csrf():
        if (app.config["CSRF_ENABLED"] and request.method == "POST"
                and not request.path.startswith("/api/")):
            sent, expected = request.form.get("_csrf"), session.get("_csrf")
            if not sent or not expected or not secrets.compare_digest(sent, expected):
                abort(400, description="Form expired - please reload the page and try again.")

    # ---- error pages ------------------------------------------------------
    @app.errorhandler(NotFoundError)
    @app.errorhandler(404)
    def not_found(err):
        msg = getattr(err, "message", None) or "Page not found"
        return render_template("error.html", code=404, message=msg), 404

    @app.errorhandler(PermissionDenied)
    def forbidden(err):
        return render_template("error.html", code=403, message=err.message), 403

    @app.errorhandler(400)
    def bad_request(err):
        return render_template("error.html", code=400, message=err.description), 400

    return app
