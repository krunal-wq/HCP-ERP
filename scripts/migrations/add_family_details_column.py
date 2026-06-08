# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
Run this script ONCE to add `family_details_json` column to the `employees`
table in your MySQL database (erpdb).

Usage:
    python add_family_details_column.py

`config.py` se DB URI automatically uthega.
"""
import os
import sys


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
        if 'employees' not in insp.get_table_names():
            print("âŒ 'employees' table nahi mili!")
            return

        cols = [c['name'] for c in insp.get_columns('employees')]
        if 'family_details_json' in cols:
            print("â„¹ï¸  family_details_json column already exists â€” skip.")
            return

        # Place after emergency_address if it exists, else just add
        after_clause = " AFTER `emergency_address`" if 'emergency_address' in cols else ""
        sql = f"ALTER TABLE `employees` ADD COLUMN `family_details_json` TEXT NULL{after_clause}"
        print(f"ðŸ›   {sql}")
        conn.execute(text(sql))
        try:
            conn.commit()
        except AttributeError:
            pass
        print("âœ… family_details_json column add ho gaya.")


if __name__ == '__main__':
    migrate()


