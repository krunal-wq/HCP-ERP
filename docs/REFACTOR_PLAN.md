# Module-wise Refactor — Analysis & Plan

> HCP ERP (Flask monolith). Goal: reorganize into a clean, scalable, module-based
> architecture **without breaking functionality**. Approach approved by owner:
> **pragmatic split** (routes + templates + module-specific services move into
> `modules/<m>/`; `models/` and `core/` stay as a **shared** layer to keep the
> single SQLAlchemy registry and avoid circular imports). **Pilot-first**, then roll out.

## 1. Current structure (before)

```
index.py                  # app + login + dashboard + setup routes; registers 33 blueprints
routes/        (33 files) # all blueprints, default (global) templates/ folder
models/        (27 files) # single shared SQLAlchemy registry (models/__init__.py)
core/                     # config, permissions, audit_helper, context_processors, error_handlers
services/                 # qr_generator, whatsapp_sender, npd_whatsapp_auto
reports/                  # universal_activity_report
templates/    (169 html)  # already grouped by module folder; ALL extend root base.html
static/                   # css, images (shared)
scripts/                  # one-time setup/migration/seed/diagnostic scripts (not app runtime)
```

Scale: ~48k LOC Python · 169 templates · 33 blueprints.

## 2. Key dependency facts (verified, read-only)

- **Templates already module-organized** (`templates/hr/`, `templates/crm/`, …) and
  **all 165 page templates extend root `base.html`** → base/macros/partials/errors are shared.
- **Sidebar/nav is DB-driven** (`Module` table via `core/context_processors.py`), **not**
  template-path-driven → moving template files does NOT affect navigation.
- **Models = one shared registry** with cross-module relationships. `from models import …`
  used 77×, `from models.npd` 64×, `from models.employee` 35×, etc. → models stay shared.
- **Routes are nearly independent.** Only cross-route import: NPD sub-files reuse
  `npd_report_bp` from `npd_daily_report_routes` (3 files) — stays within the NPD module.
- Blueprints use **absolute** imports (`from models …`, `from core …`) → these keep working
  as long as project root stays on `sys.path` (it does). Only `index.py`'s blueprint imports
  and the NPD intra-module imports need updating.

## 3. The proven mechanism (validated by the QC pilot)

For each module:
1. `git mv routes/<x>_routes.py  modules/<m>/routes/<x>_routes.py`
2. `git mv templates/<ns>        modules/<m>/templates/<ns>`   (keep the namespace subfolder)
3. In the blueprint: add `template_folder='../templates'`
4. In `index.py`: `from routes.<x> import bp` → `from modules.<m>.routes.<x> import bp`

**`render_template('<ns>/file.html')` calls stay UNCHANGED** because the namespace subfolder
is preserved and Flask's `DispatchingJinjaLoader` searches every blueprint's `template_folder`
plus the app's shared `templates/`. Zero churn on template paths, redirects, or `url_for`
(endpoints names unchanged).

## 4. Proposed module taxonomy (blueprint → module)

| Module          | Route files (blueprints)                                                              | Template folders                |
|-----------------|----------------------------------------------------------------------------------------|---------------------------------|
| **qc** ✅ done   | qc_routes, trs_routes                                                                  | qc, trs                         |
| administration  | user_routes (users_bp), approval_routes, mail_routes                                   | admin, approval, mail           |
| settings        | module_settings_routes, master_routes                                                  | settings, masters               |
| crm             | crm_routes, client_dispatch_routes                                                     | crm, client_dispatch            |
| hr              | hr_routes, hr_master_routes, hr_rules_routes, late_rule_routes, attendance_routes, qr_scan_routes | hr                   |
| npd             | npd_routes, npd_daily_report_routes, npd_report_pages, npd_wa_web_report, npd_whatsapp_routes | npd                      |
| rnd             | rd_routes, rd_sample_log_routes, raw_material_sample_routes                            | rd, raw_material_sample         |
| purchase        | purchase_order_routes, supplier_routes, grn_routes                                     | purchase_order, grn, supplier   |
| inventory       | material_routes, formulation_routes, packing_bom_routes                               | material, formulation, packing_bom |
| production      | packing_routes                                                                        | packing                         |
| accounts        | depreciation_note_routes                                                               | depreciation_note               |
| reports         | daily_report_share                                                                    | daily_report                    |

**Shared (stay put):** `models/`, `core/`, `services/` (npd_whatsapp_auto → npd module),
`reports/`, `static/`, and `templates/{base.html, base_1.html, dashboard.html, login.html, macros/, partials/, errors/}`.

### Judgment calls to confirm
- `qr_scan_routes` → **HR** (its routes live under `/hr/attendance/qr-scan`).
- `formulation_routes` → **inventory** (registered "under Raw Material"); could be **rnd**.
- `approval_routes` / `mail_routes` → **administration**; both are generic — could be **shared** instead.
- `packing` (production) vs `packing_bom` (inventory) — split as above, or keep both under production.

## 5. Risks
- **No git originally** → mitigated: baseline + per-module commits now exist (revertable).
- `index.py` has fragile bare fallback imports (`from hr_master_routes import …`,
  `from permissions import …`) inside `try/except pass` — already no-ops; will fix to package paths.
- Old `scripts/` reference legacy flat paths (`from trs_routes import …`) — **archival, not app
  runtime**; left untouched (documented).
- DB schema drift (GRN `has_depreciation_note`) is pre-existing and unrelated to this refactor.

## 6. Validation per module (smoke test, no DB needed)
`app.jinja_env.get_template(<tpl>)` resolves every moved template · blueprints register ·
route count unchanged · `base.html` still shared. Pilot result: **ALL PASS** (22 qc/trs routes).

## 7. Rollout order (low-coupling → high)
accounts → reports → production → settings → administration → purchase → inventory → crm → rnd → hr → npd
(commit per module; smoke test after each).
