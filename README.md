# HCP ERP

Flask-based ERP application for CRM, HR, NPD, RD, purchase, GRN, QC, packing,
materials, approvals, mail, reports, and WhatsApp/QR integrations.

## Run

```bash
python index.py
```

App URL: `http://127.0.0.1:5000`

## Structure

```text
index.py          Flask entry point
core/             config, permissions, audit, app helpers
routes/           Flask blueprint modules
models/           SQLAlchemy models
services/         WhatsApp, QR, and integration helpers
templates/        Jinja templates
static/           CSS, JS, images, uploads
scripts/          migrations, seeds, fixes, diagnostics
docs/             setup notes, patch notes, structure docs
archive/          backups and retired files
```

Detailed layout: `docs/PROJECT_STRUCTURE.md`
