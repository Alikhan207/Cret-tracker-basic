# Problem Statement & Design Thinking

> **Note to self before submission:** the empathy findings below are a draft based on common student experience. Replace them with what you actually heard when you spoke to 4–5 classmates and your mentor — the viva panel will ask who you interviewed.

## 1. Problem statement

Engineering students pursue several industry certifications (cloud, AI/ML, data, networking) alongside coursework. Today that progress lives in memory, phone notes, screenshots and ad-hoc spreadsheets. As a result:

- target exam dates slip without anyone noticing;
- completed certifications quietly **expire** (many cloud certs are valid only 2–3 years);
- credential IDs and verification links are hard to find when a placement form asks for them;
- mentors/faculty cannot see which students are stuck or haven't started.

**Goal:** a simple web application where each student maintains an accurate, searchable record of their certifications and study progress, and a mentor can review activity and identify pending work.

**Scope (in):** individual records, CRUD, progress logs, search/filter, validation, dashboard, mentor report, REST API.
**Scope (out):** exam booking, payments, document uploads, email/WhatsApp notifications.

## 2. Design Thinking

### 2.1 Empathize
Who: 3rd-year students preparing for placements, and their mentor.

| Method | What I did |
|---|---|
| Interviews | Spoke to _N_ classmates + mentor (fill in) |
| Observation | Looked at how people currently record certs (notes app, Excel, LinkedIn) |

Typical findings (replace with yours):
- "I started AWS in July and forgot about it after mid-sems." → nobody tracks the **target date**.
- "I had to dig through my email for the credential ID for a placement form." → credentials need one home.
- "I didn't know my Azure cert had expired." → **expiry** is invisible.
- Mentor: "I ask on the class group and only three people reply." → mentor needs a **summary view**, not more messages.

### 2.2 Define
**Persona — "Ananya", 3rd-year AI&DS student:** juggling 2–3 certifications, studies in short bursts, needs to show credentials during placements.

**Point of view:** Ananya needs one place to see each certification's status and deadline because otherwise she only notices slippage when it is too late.

**How might we…**
- …make the next deadline and overdue items impossible to miss?
- …let a student update progress in under 30 seconds?
- …give a mentor the class picture without chasing students?

### 2.3 Ideate
| Idea | Decision |
|---|---|
| Spreadsheet template | Rejected — no validation, no mentor view, easy to break |
| Mobile app | Rejected for scope — web UI works on phones too |
| Web app with dashboard + logs | **Chosen** |
| Auto-import from Credly | Future work (needs external API) |
| Gamification / streaks | Rejected — adds noise, not the core problem |

Prioritised (MoSCoW): **Must** — CRUD, status, dates, search, validation, dashboard, mentor report. **Should** — progress logs with hours, expiry warnings, CSV export. **Could** — API. **Won't (now)** — notifications, uploads.

### 2.4 Prototype
1. Paper sketch of dashboard + list screens.
2. ER model (see `02_data_model.md`).
3. Working Flask prototype with seed data for realistic testing.

### 2.5 Test
- Asked 2–3 classmates to: add a certification, log a study session, find all "Cloud" certs. Note time taken and confusion points (fill in).
- Changes made from feedback (examples to replace with yours): added "days left" next to deadlines; made status move automatically to *In progress* on first log and to *Completed* at 100%; added "Health" badge (On track / Overdue / Expiring soon) so status is visible at a glance.

## 3. User stories → features

| User story | Implemented as |
|---|---|
| As a user, I want to create and update my records so that information stays current. | Add/Edit/Delete certification forms, progress log, profile page |
| As a user, I want to search/filter records so that I can find information quickly. | `/certifications` search box + status/category/provider filters + sort |
| As a mentor/admin, I want simple reports so that I can review activity and identify pending work. | `/reports`: per-student summary, overdue list, renewals, inactive students, CSV export |
