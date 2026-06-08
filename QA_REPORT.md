# HCP-ERP — End-to-End QA & Security Audit Report

**Date:** 2026-06-08
**Auditor:** Senior QA / Security / Full-stack review (automated + manual)
**Application:** HCP ERP — Flask 3.x, SQLAlchemy, Flask-Login, MySQL (PyMySQL), Jinja2
**Codebase size:** 210 Python files (~48 K LOC), 172 Jinja templates, 28 CSS, 649 registered routes, 127 DB tables
**Status:** ⚠️ **NOT production-ready.** Multiple Critical authentication/authorization and data-integrity defects must be fixed before deployment.

---

## 1. Methodology

The audit combined **static** and **dynamic** techniques against the live application (the MySQL DB `erpdb` was reachable with 127 tables, and the app imported and ran cleanly under a Flask test client):

1. **Structure mapping** — full inventory of modules, blueprints, routes, models, templates, permissions.
2. **Compile / import verification** — byte-compiled all 210 `.py` files; imported the app and enumerated all 649 routes.
3. **Dynamic probing** — drove every GET route with a Flask test client both **unauthenticated** (to find auth gaps) and **authenticated as admin** (to find 500 crashes), skipping mutating endpoints.
4. **Dependency verification** — checked every third-party import is installed.
5. **Template/DB integrity** — cross-referenced every `render_template()` literal against the Jinja loader.
6. **Security pattern scan** — grep for raw SQL, `render_template_string`, `eval/exec`, CSRF config, `|safe`, file-upload sinks.
7. **Deep manual review** — 6 parallel expert passes over every route file (CRM, NPD/R&D, HR, Purchase/Inventory, QC/Packing/Accounts, Admin/Settings/Core) hunting IDOR, broken access control, logic bugs, mass assignment, workflow flaws.

A reusable probe was added at `scripts/diagnostics/qa_audit_probe.py`.

---

## 2. Executive Summary

| Severity | Count | Theme |
|----------|-------|-------|
| **Critical** | 9 | CSRF disabled app-wide; public setup/admin-creation routes; unauthenticated attendance manipulation; blanket IDOR on CRM leads & NPD; SQL injection in supplier; stored XSS via uploads |
| **High** | ~24 | Missing `require_perm` on entire modules (Master, Purchase, GRN, Supplier, Mail relay); employee PII/salary export by any user; stock-integrity drift; missing dependency (`reportlab`/`qrcode`) breaking all PDF/QR features; broken templates; login enumeration/cross-account |
| **Medium** | ~22 | Workflow/state-machine gaps; mass assignment of financial fields; CSV/Excel formula injection; unhandled missing-record 500s; weak default passwords; insecure cookies |
| **Low** | ~15 | Float currency math, debug endpoints leaking data, broad `except: pass`, pagination drift, dead code |

### Top systemic root causes
1. **Authorization is UI-deep, not server-deep.** Many modules hide buttons in templates but the underlying POST/JSON/PDF/export endpoints enforce only `@login_required` (or stub `_can()` functions that `return True`). This produces pervasive IDOR and privilege-escalation.
2. **CSRF protection is configured but inert.** `WTF_CSRF_ENABLED=True` does nothing because `CSRFProtect(app)` is never instantiated and routes read `request.form`/`request.json` directly. Every state-changing endpoint is forgeable.
3. **Secrets and bootstrap routes are exposed.** Hardcoded SECRET_KEY / DB password / live Gmail app-password in `core/config.py`, plus public `/setup` that can mint a known-credential admin.
4. **Missing runtime dependencies.** `reportlab` and `qrcode` are imported but not installed nor declared — every PDF and QR feature 500s.
5. **Pervasive broad exception swallowing** hides the above failures from operators.

### Positives (verified)
- All 210 source files compile; the app imports and registers 649 routes with no broken imports/circular deps.
- **No classic SQL injection** anywhere except the one confirmed supplier sink — all ORM queries use bound parameters (`.ilike(f'%{x}%')` is parameterized).
- User-management **CRUD** endpoints (`/admin/users/*`) correctly enforce `@admin_required` server-side.
- Passwords use Werkzeug hashing (not MD5/SHA1); non-admin permission checks fail **closed**.
- File uploads use `secure_filename`; no path traversal is currently exploitable (filenames are server-generated/sanitized).

---

## 3. Application Inventory

**Modules (blueprints):** CRM (leads, clients, quotations, sample orders, dispatch), HR (employees, attendance, salary, loans, challan, rules, QR kiosk), NPD (projects, milestones, daily reports, WhatsApp), R&D (samples, sample log, raw-material sample), Purchase (PO, GRN, supplier), Inventory (material/item master, formulation, packing BOM), QC (TRS, approvals), Production (packing), Accounts (depreciation note), Administration (users, approvals, mail), Settings (masters, module toggles), Reports.

**Core:** `core/config.py`, `core/permissions.py` (user-only RBAC model), `core/audit_helper.py`, `core/error_handlers.py`, `core/context_processors.py`.

**Largest route files:** `crm_routes.py` (5071), `npd_routes.py` (5067), `hr_routes.py` (3809), `grn_routes.py` (2924), `purchase_order_routes.py` (2470), `attendance_routes.py` (2112).

---

## 4. Findings by Category

> Full per-issue detail (severity, file:line, root cause, reproduction, fix) is in **`TODO.md`**. This section summarizes the themes; IDs (e.g. `C1`, `H4`) map to `TODO.md`.

### 4.1 Authentication & Session (C1–C3, H10–H12)
- **CSRF inert** across all POST/JSON routes (`C3`).
- **Public bootstrap routes** `/setup` (mints `admin`/`HCP@123`), `/seed-modules`, `/setup-procurement` (`C2`); `/fix-admin-perms` reachable by any logged-in user (`C1b`).
- **3-way login** (username/email/employee-code) enables user enumeration (distinct error messages), cross-account resolution via derived-username/email fallback, and lockout bypass via identifier rotation (`H11`).
- **Insecure cookies:** `SESSION_COOKIE_SECURE=False`, no `SAMESITE`, remember-me not Secure (`H12`).
- **Hardcoded secrets** in `core/config.py` (`H10`).

### 4.2 Authorization / Access Control (Critical theme)
- **CRM:** Any logged-in user can view/edit/delete **any** lead, client, quotation, sample order, invoice by id — the team-member visibility filter exists only on the list page (`C4`, `C5`, `C6`, `H1`–`H3`). `team_members LIKE '%uid%'` substring matching over-grants (uid 1 matches 11/21) (`C5`).
- **NPD/R&D:** Blanket IDOR — every milestone/formulation/packing/artwork/BOM/FDA/status mutation is `@login_required` only; `api_status` sets arbitrary status on any project (`C7`, `H4`–`H6`).
- **HR:** `/employees/<id>/export` dumps Aadhaar/PAN/bank/salary to any user; `create-login` mints accounts with default password for any employee (`H7`, `H8`).
- **Purchase/Inventory/QC:** `_can()` guards are stubs returning `True`; detail/PDF/export/scan endpoints not category-gated (`H13`–`H16`).
- **Master data CRUD** (`masters.add/edit/delete`) has **no permission check at all** (`H17`).
- **Mail relay:** any user can send mail to arbitrary recipients with arbitrary `From` via corporate SMTP (`H18`).
- **Audit log** readable/exportable by any user (`M-audit`).

### 4.3 Injection (C-SQLi, H-XSS, H-CSV)
- **SQL injection** (confirmed reachable) in `supplier_routes.py:99` via `supplier_type` in `/supplier/api/save` (`C-SQLi`). A second f-string sink at `:237` is blocked by an allow-list (defense-in-depth fix recommended).
- **Stored XSS** via inline-served uploads — `serve_upload` serves `.svg`/`.html` inline with no `as_attachment` (`C8`).
- **XSS in email/PDF bodies** — user fields interpolated unescaped into HTML email and reportlab Paragraph markup (`H9`).
- **CSV/Excel formula injection** — exports write user-controlled names/notes without neutralizing leading `= + - @` (`H-CSV`).

### 4.4 Data Integrity & Business Logic
- **GRN cancel** does not reverse scan-created stock and is non-idempotent → phantom stock / PO-qty drift (`H-GRN1`, `H-GRN2`).
- **Attendance status** classified by three divergent code paths → same punches yield Present vs Absent depending on which writer ran last; feeds payroll (`M-att1`).
- **Salary** LOP/half-day double-count risk; LOP leave bucketed into PL; negative-net edge (`M-sal1`–`M-sal3`).
- **Lead status** via Kanban/inline-edit doesn't set/clear `closed_at` → corrupts age & contribution math (`M-lead1`).
- **Daily report** `mod` used before assignment → audit-log section silently empty (`H-report1`).

### 4.5 Reliability / Crashes (found dynamically)
- **`reportlab` not installed** → every PDF route 500s (CRM PDFs, NPD form/labels, GRN PDF, PO PDF) (`H-dep1`).
- **`qrcode` not installed** → QR generation broken (`H-dep2`); **`rembg`** has no ONNX backend → image bg-removal fails (`M-dep3`).
- **Missing templates:** `npd/dashboard.html`, `npd/projects.html`, `npd/project_form.html`, `hr/loans/detail.html` (`H-tpl1`); `npd/npd_projects.html` has a `TemplateSyntaxError` (`unknown tag 'endblock'` ~line 1252) (`H-tpl2`); **`errors/500.html` missing** → the 500 handler itself crashes (`H-tpl3`).
- **`from config import Config`** (should be `core.config`) breaks `/crm/api/stale-leads` (`H-imp1`).
- **`role_perm_map` undefined** breaks `/admin/user-permissions/<id>` (`H-tpl4`).
- **`ar.request_type`** referenced but not a model column → every approval action 500s (`H-appr1`).
- Multiple unhandled `None`/missing-record dereferences → 500 instead of 404 (`M-null*`).

### 4.6 Information Disclosure
- Unauthenticated endpoints returning 200: `/hr/masters/api/{departments,designations,emp-types,locations}` (master data), `/hr/attendance/qr-today-list` (**every employee's name, code, photo, punch times — PII**), `/hr/attendance/qr-stats`, `/hr/attendance/qr-debug-attendance` (`H-info1`).
- Debug endpoints leaking employee rows to any logged-in user (`/npd/debug/*`, `?debug_visibility=1`, `rd_sample_log .../api/diagnose`) (`L-debug`).

---

## 5. Recommended Remediation Order

**Phase 0 — Stop-ship blockers (do first):**
1. Instantiate `CSRFProtect(app)` and add tokens to forms/AJAX (`C3`).
2. Remove/guard `/setup`, `/seed-modules`, `/setup-procurement`, `/fix-admin-perms` (`C1b`, `C2`).
3. Move all secrets to env; rotate the leaked Gmail app-password and DB password (`H10`); set `debug=False` (`H-debug`).
4. Parameterize the supplier SQL (`C-SQLi`).
5. Lock down `/hr/attendance/qr-lookup` (unauthenticated attendance punch) (`C1`).

**Phase 1 — Access control:**
6. Add server-side object-level authorization to every per-record CRM, NPD, HR, Purchase, GRN, QC, Master endpoint (replace stub `_can()` with real `require_perm` + ownership checks).
7. Gate mail relay, audit-log read, employee export.

**Phase 2 — Reliability:**
8. `pip install reportlab qrcode[pil]` + add to `requirements.txt`; fix `rembg` backend or guard it.
9. Create the 4 missing templates + `errors/500.html`; fix the `npd_projects.html` syntax error; fix `from config import` and `role_perm_map`; fix `ar.request_type`.

**Phase 3 — Data integrity & hardening:**
10. Fix GRN cancel reversal & attendance/salary calculations.
11. Escape email/PDF output; neutralize CSV formula injection; restrict uploads (no svg/html, serve as attachment).
12. Harden login (uniform error, drop fallback chain, IP throttle); set secure cookie flags.

---

## 6. Test Coverage Note

A `tests/` suite exists (`test_auth.py`, `test_models.py`, `test_permissions.py`, `test_routes.py`, `test_qr_scan.py`) but disables CSRF for testing and does not cover the IDOR/authorization gaps found here. Recommend adding negative authorization tests (low-priv user hitting privileged endpoints should get 403) as regression guards for the Phase-1 fixes.

---

*Granular, actionable issue cards with reproduction steps and fixes are in `TODO.md`.*
