"""JSON REST API - demonstrates HTTP methods, status codes and JSON.

    POST   /api/login                 -> 200 / 401
    POST   /api/logout                -> 200
    GET    /api/certifications        -> 200   (?q=&status=&category=&provider=&sort=)
    POST   /api/certifications        -> 201 / 400 / 409
    GET    /api/certifications/<id>   -> 200 / 403 / 404
    PUT    /api/certifications/<id>   -> 200 / 400 / 403 / 404
    DELETE /api/certifications/<id>   -> 204 / 403 / 404
    POST   /api/certifications/<id>/logs -> 201 / 400
    GET    /api/stats                 -> 200
"""
from flask import Blueprint, g, jsonify, request, session

from .auth import login_required
from .db import get_db
from .exceptions import AppError, ValidationError
from .services import AuthService, CertificationService

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.errorhandler(AppError)
def handle_app_error(err: AppError):
    body = {"error": err.message}
    if isinstance(err, ValidationError):
        body["fields"] = err.errors
    return jsonify(body), err.status_code


def _json() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError({"body": "Request body must be a JSON object"})
    return data


@bp.post("/login")
def api_login():
    data = _json()
    user = AuthService(get_db()).authenticate(data.get("email"), data.get("password"))
    session.clear()
    session["user_id"] = user.id
    return jsonify(user=user.to_dict())


@bp.post("/logout")
def api_logout():
    session.clear()
    return jsonify(message="Logged out")


@bp.get("/certifications")
@login_required
def list_certs():
    certs = CertificationService(get_db()).search(g.user, request.args)
    return jsonify(count=len(certs), items=[c.to_dict() for c in certs])


@bp.post("/certifications")
@login_required
def create_cert():
    svc = CertificationService(get_db())
    cid = svc.create(g.user, _json())
    return jsonify(svc.get_for_view(g.user, cid).to_dict()), 201


@bp.get("/certifications/<int:cert_id>")
@login_required
def get_cert(cert_id):
    svc = CertificationService(get_db())
    body = svc.get_for_view(g.user, cert_id).to_dict()
    body["logs"] = [{"date": l.log_date.isoformat(), "hours": l.hours, "progress": l.progress, "note": l.note}
                    for l in svc.logs_for(cert_id)]
    return jsonify(body)


@bp.put("/certifications/<int:cert_id>")
@login_required
def update_cert(cert_id):
    svc = CertificationService(get_db())
    svc.update(g.user, cert_id, _json())
    return jsonify(svc.get_for_view(g.user, cert_id).to_dict())


@bp.delete("/certifications/<int:cert_id>")
@login_required
def delete_cert(cert_id):
    CertificationService(get_db()).delete(g.user, cert_id)
    return "", 204


@bp.post("/certifications/<int:cert_id>/logs")
@login_required
def add_log(cert_id):
    svc = CertificationService(get_db())
    svc.log_progress(g.user, cert_id, _json())
    return jsonify(svc.get_for_view(g.user, cert_id).to_dict()), 201


@bp.get("/stats")
@login_required
def stats():
    d = CertificationService(get_db()).dashboard(g.user)
    return jsonify(
        total=d["total"],
        by_status={s.value: n for s, n in d["counts"].items()},
        completion_rate=d["completion_rate"],
        average_progress=d["avg_progress"],
        study_hours=d["hours"],
        overdue=[c.title for c in d["overdue"]],
        expiring=[c.title for c in d["expiring"]],
    )
