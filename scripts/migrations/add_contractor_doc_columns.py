# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
Run ONCE to add new contractor document columns to the `contractors` table
in MySQL (erpdb): EPFO, PT, GLWF, Contract License, ESIC, Agreement
(each: number + file path).

Usage:
    python add_contractor_doc_columns.py
"""
import os
import sys

# (column_name, SQL type) â€” order also used for AFTER placement
NEW_COLUMNS = [
    ("epfo_no",               "VARCHAR(30) NULL"),
    ("pt_no",                 "VARCHAR(30) NULL"),
    ("glwf_no",               "VARCHAR(30) NULL"),
    ("contract_license_no",   "VARCHAR(50) NULL"),
    ("esic_no",               "VARCHAR(30) NULL"),
    ("agreement_no",          "VARCHAR(50) NULL"),
    ("epfo_file",             "VARCHAR(255) NULL"),
    ("pt_file",               "VARCHAR(255) NULL"),
    ("glwf_file",             "VARCHAR(255) NULL"),
    ("contract_license_file", "VARCHAR(255) NULL"),
    ("esic_file",             "VARCHAR(255) NULL"),
    ("agreement_file",        "VARCHAR(255) NULL"),
]


def _load_uri():
    uri = os.environ.get('DATABASE_URL')
    if uri:
        return uri
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from config import Config
        return Config.SQLALCHEMY_DATABASE_URI
    except Exception as e:
        print(f"âŒ config.py se DB URI load nahi hua: {e}")
        return None


def _safe_uri(uri):
    try:
        if '://' in uri and '@' in uri:
            scheme, rest = uri.split('://', 1)
            creds, host = rest.split('@', 1)
            if ':' in creds:
                user, _ = creds.split(':', 1)
                return f"{scheme}://{user}:****@{host}"
        return uri
    except Exception:
        return uri


def migrate():
    uri = _load_uri()
    if not uri:
        return
    print(f"ðŸ”— DB URI: {_safe_uri(uri)}")

    try:
        from sqlalchemy import create_engine, text, inspect
    except ImportError:
        print("âŒ pip install sqlalchemy pymysql cryptography")
        return

    engine = create_engine(uri, pool_pre_ping=True)
    with engine.connect() as conn:
        insp = inspect(conn)
        if 'contractors' not in insp.get_table_names():
            print("âŒ 'contractors' table nahi mili!")
            return

        existing = [c['name'] for c in insp.get_columns('contractors')]
        added = 0
        for col, ddl in NEW_COLUMNS:
            if col in existing:
                print(f"â„¹ï¸  {col} already exists â€” skip.")
                continue
            sql = f"ALTER TABLE `contractors` ADD COLUMN `{col}` {ddl}"
            print(f"ðŸ›   {sql}")
            conn.execute(text(sql))
            existing.append(col)
            added += 1
        try:
            conn.commit()
        except AttributeError:
            pass
        print(f"âœ… Done. {added} naye column add hue.")


if __name__ == '__main__':
    migrate()


