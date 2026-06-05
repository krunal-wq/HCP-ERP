# Project Structure

HCP ERP is a Flask application. The root has been cleaned so only entry-point
and project-level files stay outside folders.

## Run

```bash
python index.py
```

Local server: `http://127.0.0.1:5000`

## Root Layout

```text
.
|-- index.py              # Flask entry point and blueprint registration
|-- requirements.txt      # Python dependencies
|-- README.md             # Current project note
|-- .gitignore
|
|-- core/                 # Config, permissions, audit, context, error handlers
|-- models/               # SQLAlchemy models and db package
|-- routes/               # All Flask blueprint/route modules
|-- services/             # Integration/service helpers such as WhatsApp and QR
|-- templates/            # Jinja templates
|-- static/               # CSS, JS, uploads, images
|-- scripts/              # One-off scripts, migrations, fixes, diagnostics
|-- docs/                 # Documentation and patch notes
|-- archive/              # Backups and retired/legacy files
```

## Important Paths

```text
core/config.py
core/permissions.py
core/audit_helper.py
core/error_handlers.py

routes/crm_routes.py
routes/hr_routes.py
routes/npd_routes.py
routes/purchase_order_routes.py
routes/qc_routes.py
routes/module_settings_routes.py

services/whatsapp_sender.py
services/npd_whatsapp_auto.py
services/qr_generator.py

scripts/setup_app.py
docs/README_legacy.txt
```

## Notes

The old duplicate `routes/hr_routes.py` was preserved at
`archive/legacy/hr_routes_from_routes_backup.py` before the active root
`hr_routes.py` was moved into `routes/hr_routes.py`.

Run scripts from the project root so imports resolve correctly:

```bash
python scripts/migrations/migrate.py
python scripts/seeds/seed_projects.py
```
