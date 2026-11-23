"""Registration, login, logout and access-control decorators."""
import functools

from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, session, url_for

from .db import get_db
from .exceptions import AuthenticationError, DuplicateError, ValidationError
from .repositories import UserRepository
from .services import AuthService

bp = Blueprint("auth", __name__)


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = UserRepository(get_db()).get(user_id) if user_id else None


def login_required(view):
    @functools.wraps(view)
    def wrapped(**kwargs):
        if g.user is None:
            if request.path.startswith("/api/"):
                return jsonify(error="Login required"), 401
            return redirect(url_for("auth.login", next=request.path))
        return view(**kwargs)
    return wrapped


def mentor_required(view):
    @functools.wraps(view)
    @login_required
    def wrapped(**kwargs):
        if not g.user.is_mentor:
            if request.path.startswith("/api/"):
                return jsonify(error="Mentor access required"), 403
            flash("That page is only for mentors.", "error")
            return redirect(url_for("views.dashboard"))
        return view(**kwargs)
    return wrapped


@bp.route("/register", methods=("GET", "POST"))
def register():
    errors, form = {}, {}
    if request.method == "POST":
        form = request.form
        try:
            AuthService(get_db()).register(form)
            flash("Account created - please log in.", "success")
            return redirect(url_for("auth.login"))
        except ValidationError as e:
            errors = e.errors
        except DuplicateError as e:
            errors = {"email": e.message}
    return render_template("register.html", errors=errors, form=form)


@bp.route("/login", methods=("GET", "POST"))
def login():
    error = None
    if request.method == "POST":
        try:
            user = AuthService(get_db()).authenticate(request.form.get("email"), request.form.get("password"))
            csrf = session.get("_csrf")
            session.clear()                 # prevent session fixation
            session["user_id"] = user.id
            if csrf:
                session["_csrf"] = csrf
            nxt = request.args.get("next", "")
            # only follow local redirects (avoid open-redirect attacks)
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("views.dashboard"))
        except AuthenticationError as e:
            error = e.message
    return render_template("login.html", error=error)


@bp.route("/logout", methods=("POST",))
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("auth.login"))
