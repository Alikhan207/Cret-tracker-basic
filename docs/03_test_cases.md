# Test Cases

Automated: `python -m pytest -v` → **50 tests** (validators 25, services 12, web + API 13 — parametrised cases counted individually).

## Manual / functional test cases

| ID | Feature | Steps | Input | Expected | Automated test |
|---|---|---|---|---|---|
| TC01 | Register | Fill register form | valid name/email, `Passw0rd` ×2 | Redirect to login, success message | `test_register_then_login` |
| TC02 | Register validation | Submit bad data | email `bad`, password `x` | Form re-shown with field errors | `test_register_shows_errors` |
| TC03 | Duplicate email | Register existing email | `ali@cmrit.ac.in` | "account already exists" | `test_duplicate_email_rejected` |
| TC04 | Login failure | Wrong password | `ali@…` / `wrong` | "Invalid email or password" | `test_wrong_password_rejected` |
| TC05 | Auth guard | Open `/certifications` logged out | — | Redirect to `/login` | `test_pages_require_login` |
| TC06 | Create cert | Add form | valid planned cert | Saved, detail page shown | `test_create_edit_delete_flow` |
| TC07 | Edit cert | Edit title + status | in_progress, 20% | Updated values shown | `test_create_edit_delete_flow` |
| TC08 | Delete cert | Delete, confirm | — | Gone; URL now 404 | `test_create_edit_delete_flow` |
| TC09 | Duplicate cert | Add same title+provider (`aws` lower-case) | — | "already tracking" (409 in API) | `test_duplicate_certification_rejected_case_insensitive_provider`, `test_api_duplicate_is_409` |
| TC10 | Date rule | Target before start | start 01-12, target 01-11 | Error on target date | `test_target_before_start_rejected` |
| TC11 | Completed rule | Status completed, no date | — | "need a completion date" | `test_completed_needs_completion_date` |
| TC12 | Future completion | Completed date in future | — | Error | `test_completion_date_cannot_be_in_future` |
| TC13 | Expiry rule | Expiry before completion | — | Error | `test_expiry_must_be_after_completion` |
| TC14 | Progress range | Progress 150 / "abc" | — | Error | `test_field_rules` |
| TC15 | Log progress | Log 2h → 40% on planned cert | — | Status becomes In progress | `test_progress_log_moves_planned_to_in_progress_then_completed` |
| TC16 | Auto-complete | Log → 100% | — | Status Completed, completion date = today | same |
| TC17 | No going backwards | Log 30% when at 50% | — | Error | `test_progress_cannot_go_backwards` |
| TC18 | Invalid hours | 0, -1, 25, "two" | — | Error | `test_invalid_hours` |
| TC19 | Search | Filter status=completed | — | Only completed shown | `test_search_filter` |
| TC20 | Privacy | Student opens another student's cert | `/certifications/5` | 403 | `test_student_blocked_from_reports_and_other_records` |
| TC21 | Mentor read-only | Mentor deletes student cert | — | PermissionDenied / 403 | `test_cannot_edit_someone_elses_record` |
| TC22 | Mentor report | Open `/reports` | — | Per-student table, pending list | `test_mentor_report_and_csv` |
| TC23 | CSV export | Click Export CSV | — | `.csv` download | `test_mentor_report_and_csv` |
| TC24 | Dashboard | Login as Ali | — | 4 tracked, 1 overdue, 1 expiring, 13h | `test_dashboard_numbers` |
| TC25 | CSRF | POST form without token | — | 400 | `test_csrf_blocks_forged_post` |
| TC26 | API CRUD | POST → PUT → log → GET → DELETE | JSON | 201, 200, 201, 200, 204 | `test_api_crud` |
| TC27 | API errors | Bad JSON / missing fields | — | 400 with `fields` | `test_api_validation_errors_are_json` |

## Debugging log (examples from building this — add your own)

| Bug | Cause | Fix |
|---|---|---|
| CSRF check let a forged POST through when no session existed | `None == None` evaluated true | Require both tokens to be present; compare with `secrets.compare_digest` |
| Foreign key delete didn't cascade | SQLite has FKs **off** by default | `PRAGMA foreign_keys = ON` on every connection |
| Edit form showed blank progress for 0% | `v or ""` treats `0` as falsy | Use `"" if v is None else v` |
| Dashboard hours test expected 13.5 | Wrong manual sum in the test | Recomputed: 2+3+2.5+1.5+2+2 = 13 |
