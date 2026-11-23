# Viva Preparation

This is an **individual viva**, so be ready to open any file and explain it line by line. Before the viva, change at least one thing yourself and redo it from memory (e.g. add a new category, or a new filter).

## 1. Two-minute walkthrough (say this out loud)
1. Problem: students lose track of certification deadlines and expiry; mentors have no overview.
2. Demo as **Ali**: dashboard (overdue Oracle, expiring AWS) → list → filter "Cloud" → add a cert with a bad date (show validation) → fix it → log progress (status changes automatically).
3. Demo as **mentor**: report → overdue students → CSV export.
4. Show code layers: `views → services → repositories → schema.sql`.
5. Run `pytest` live: 50 passed.

## 2. Likely questions

**OOP**
- *Where is OOP used?* `models.py`: `User`, `Certification`, `ProgressLog` are dataclasses; `Status`/`Role` are Enums. Repositories and services are classes that take the DB connection in their constructor (dependency injection).
- *Encapsulation example?* `Certification.is_overdue()`, `health()` — the rule lives with the data. `password_hash` has `repr=False` and is excluded from `to_dict()`.
- *Inheritance?* `exceptions.py`: `ValidationError`, `NotFoundError`… all inherit `AppError`, so one handler (`api.py → handle_app_error`) catches them all — that's polymorphism via `err.status_code`.
- *Why a dataclass?* Auto-generates `__init__`, `__repr__`, `__eq__`; less boilerplate.

**Data structures / collections**
- `Counter` — count certifications per status (dashboard).
- `defaultdict(list)` — group certifications by category.
- `heapq.nsmallest(5, …)` — 5 nearest deadlines in O(n log 5) instead of sorting all.
- `dict` — validation `errors` (field → message), `SORTS` whitelist.
- `tuple` — `CATEGORIES` (immutable).
- List comprehensions/generators for filtering overdue/expiring.

**SQL / DBMS**
- *Primary vs foreign key?* PK uniquely identifies a row; FK references a PK in another table to enforce relationships.
- *Why a providers table?* Normalisation (3NF) — avoid "AWS" / "aws" / "Amazon" duplicates.
- *Why LEFT JOIN in the report?* So students with **zero** certifications still appear (Arjun).
- *What is ON DELETE CASCADE?* Deleting a certification deletes its logs automatically.
- *How do you prevent SQL injection?* `?` placeholders — the driver sends values separately from the SQL text. `ORDER BY` can't take a placeholder so I use a whitelist dict.
- *What is a transaction? Where?* `services.log_progress`: insert log + update certification commit together or roll back together (atomicity — the A in ACID).
- *Why indexes?* Speed up `WHERE user_id = ?`, `status`, `target_date` filters.
- *Why store dates as TEXT?* SQLite has no DATE type; ISO `YYYY-MM-DD` strings sort correctly, so `<` comparisons work.

**Validation / exceptions**
- Two layers: Python validation (friendly messages, all errors at once) + DB constraints (safety net if someone bypasses the app).
- Example business rules: target ≥ start; completed ⇒ completion date & 100%; expiry > completion; progress never decreases.
- *Why custom exceptions?* Services don't know about HTTP; the web layer maps exception type → status code (400/401/403/404/409).

**HTTP / API**
- GET reads, POST creates, PUT updates, DELETE removes. 201 Created, 204 No Content, 400 bad input, 401 not logged in, 403 not allowed, 404 not found, 409 conflict.
- *Stateless?* HTTP is stateless; login state is kept in a signed session cookie (`SECRET_KEY`).
- *What is CSRF?* A malicious site making your browser submit a form to this site. Each form has a random token stored in the session; POSTs without the right token are rejected.

**Security**
- Passwords: `generate_password_hash` (salted, slow hash). Can't be reversed; login compares hashes.
- Same error for wrong email and wrong password → attackers can't enumerate users.
- Mentors can't self-register — created via `flask --app run create-mentor`.

**Git / GitHub**
- `git add`, `commit`, `push`, `branch`, `merge`, `log`, `.gitignore` (why the database file and venv are ignored).

**Testing**
- Unit tests (validators — pure functions), integration tests (services with a temp DB), end-to-end (Flask test client). Each test gets a fresh database via a fixture in `conftest.py`.
- `pytest.mark.parametrize` runs one test with many inputs.

## 3. "What would you improve?"
Email reminders for deadlines, PostgreSQL for multiple users, Credly import, pagination for large lists, token-based API auth, role for admin separate from mentor.

## 4. Be honest about
If asked whether you had help: say which parts you wrote, which you adapted, and show you understand all of it. Being able to modify the code live is the best proof.
