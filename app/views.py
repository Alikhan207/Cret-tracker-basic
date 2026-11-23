"""HTML pages: dashboard, certification CRUD, search, profile, mentor reports."""
import csv
import io
from datetime import date

from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for

from .auth import login_required, mentor_required
from .db import get_db
from .exceptions import DuplicateError, PermissionDenied, ValidationError
from .models import CATEGORIES, Status
from .services import AuthService, CertificationService, ReportService

bp = Blueprint("views", __name__)


def _svc() -> CertificationService:
    return CertificationService(get_db())


@bp.app_context_processor
def inject_globals():
    return {"STATUSES": list(Status), "CATEGORIES": CATEGORIES, "today": date.today()}


@bp.route("/")
@login_required
def dashboard():
    if g.user.is_mentor:
        return redirect(url_for("views.reports"))
    return render_template("dashboard.html", d=_svc().dashboard(g.user))


@bp.route("/certifications")
@login_required
def cert_list():
    filters = {k: request.args.get(k, "") for k in ("q", "status", "category", "provider", "sort")}
    svc = _svc()
    certs = svc.search(g.user, filters)
    return render_template("cert_list.html", certs=certs, filters=filters, providers=svc.provider_names())


@bp.route("/certifications/new", methods=("GET", "POST"))
@login_required
def cert_create():
    if g.user.is_mentor:
        raise PermissionDenied("Mentors review certifications; they do not add their own here")
    errors, form = {}, request.form
    if request.method == "POST":
        try:
            cid = _svc().create(g.user, form)
            flash("Certification added.", "success")
            return redirect(url_for("views.cert_detail", cert_id=cid))
        except ValidationError as e:
            errors = e.errors
        except DuplicateError as e:
            errors = {"title": e.message}
    return render_template("cert_form.html", form=form, errors=errors, cert=None,
                           providers=_svc().provider_names())


@bp.route("/certifications/<int:cert_id>")
@login_required
def cert_detail(cert_id):
    svc = _svc()
    cert = svc.get_for_view(g.user, cert_id)
    return render_template("cert_detail.html", cert=cert, logs=svc.logs_for(cert_id),
                           hours=svc.hours_for(cert_id), errors={}, form={})


@bp.route("/certifications/<int:cert_id>/edit", methods=("GET", "POST"))
@login_required
def cert_edit(cert_id):
    svc = _svc()
    cert = svc.get_for_edit(g.user, cert_id)
    errors = {}
    if request.method == "POST":
        form = request.form
        try:
            svc.update(g.user, cert_id, form)
            flash("Certification updated.", "success")
            return redirect(url_for("views.cert_detail", cert_id=cert_id))
        except ValidationError as e:
            errors = e.errors
        except DuplicateError as e:
            errors = {"title": e.message}
    else:
        form = {k: ("" if v is None else v) for k, v in cert.to_dict().items()}
    return render_template("cert_form.html", form=form, errors=errors, cert=cert,
                           providers=svc.provider_names())


@bp.route("/certifications/<int:cert_id>/delete", methods=("POST",))
@login_required
def cert_delete(cert_id):
    _svc().delete(g.user, cert_id)
    flash("Certification deleted.", "success")
    return redirect(url_for("views.cert_list"))


@bp.route("/certifications/<int:cert_id>/progress", methods=("POST",))
@login_required
def cert_progress(cert_id):
    svc = _svc()
    try:
        svc.log_progress(g.user, cert_id, request.form)
        flash("Progress logged.", "success")
    except ValidationError as e:
        cert = svc.get_for_view(g.user, cert_id)
        return render_template("cert_detail.html", cert=cert, logs=svc.logs_for(cert_id),
                               hours=svc.hours_for(cert_id), errors=e.errors, form=request.form), 400
    except PermissionDenied as e:
        flash(e.message, "error")
    return redirect(url_for("views.cert_detail", cert_id=cert_id))


@bp.route("/profile", methods=("GET", "POST"))
@login_required
def profile():
    errors = {}
    if request.method == "POST":
        try:
            AuthService(get_db()).update_profile(g.user, request.form)
            flash("Profile updated.", "success")
            return redirect(url_for("views.profile"))
        except ValidationError as e:
            errors = e.errors
    return render_template("profile.html", errors=errors)


@bp.route("/reports")
@mentor_required
def reports():
    return render_template("reports.html", r=ReportService(get_db()).mentor_report(g.user))


@bp.route("/reports/export.csv")
@mentor_required
def reports_csv():
    certs = _svc().search(g.user, {})
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Student", "Title", "Provider", "Category", "Status", "Progress",
                     "Target date", "Completed", "Expiry", "Health"])
    for c in certs:
        d = c.to_dict()
        writer.writerow([c.owner_name, c.title, c.provider_name, c.category, c.status.label, c.progress,
                         d["target_date"] or "", d["completed_date"] or "", d["expiry_date"] or "", d["health"]])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=certification_report.csv"})
