# Git / GitHub Workflow

Evaluators look at commit history. Don't push everything as one "final" commit — build it up in meaningful steps, in **your own name**, as you work through and understand each part.

## One-time setup
```bash
git config --global user.name  "Mohammed Ali Khan"
git config --global user.email "<your GitHub email>"
cd cert-tracker
git init
git branch -M main
# create an empty repo on GitHub named cert-tracker (no README), then:
git remote add origin https://github.com/<your-username>/cert-tracker.git
```

## Suggested commit sequence
| # | Files | Message |
|---|---|---|
| 1 | `README.md`, `.gitignore`, `requirements.txt`, `docs/01_*` | `docs: add problem statement and design thinking` |
| 2 | `docs/02_data_model.md`, `app/schema.sql` | `db: add schema for users, providers, certifications, logs` |
| 3 | `app/models.py`, `app/exceptions.py` | `feat: add domain models and exception hierarchy` |
| 4 | `app/validators.py`, `tests/test_validators.py`, `pytest.ini`, `tests/conftest.py` | `feat: add input and business-rule validation with tests` |
| 5 | `app/db.py`, `app/repositories.py` | `feat: add repository layer with parameterised SQL` |
| 6 | `app/services.py`, `app/seed.py`, `tests/test_services.py` | `feat: add services, access control and seed data` |
| 7 | `app/__init__.py`, `app/auth.py`, `run.py`, auth templates, `base.html`, `style.css` | `feat: add registration, login and CSRF protection` |
| 8 | `app/views.py`, cert templates, `_macros.html` | `feat: certification CRUD, search and filters` |
| 9 | dashboard + reports templates | `feat: student dashboard and mentor report with CSV export` |
| 10 | `app/api.py`, `tests/test_web_and_api.py` | `feat: add JSON REST API with tests` |
| 11 | `docs/03_*`, `docs/04_*`, README screenshots | `docs: test cases, viva notes, screenshots` |

For each step:
```bash
git add <files>
git commit -m "<message>"
git push -u origin main     # -u only needed the first time
```

Optional but impressive: do one feature on a branch and merge it.
```bash
git checkout -b feature/api
# ...commit...
git checkout main && git merge feature/api
```
