# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
Run this script ONCE to add `manpower_capacity` column to the `contractors`
table in your MySQL database (erpdb).

Manpower Capacity = number of workers the contractor can supply.

Usage:
    python add_manpower_capacity_column.py

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
        if 'contractors' not in insp.get_table_names():
            print("âŒ 'contractors' table nahi mili!")
            return

        cols = [c['name'] for c in insp.get_columns('contractors')]
        if 'manpower_capacity' in cols:
            print("â„¹ï¸  manpower_capacity column already exists â€” skip.")
            return

        # Place after `supply` if it exists, else just add at the end
        after_clause = " AFTER `supply`" if 'supply' in cols else ""
        sql = f"ALTER TABLE `contractors` ADD COLUMN `manpower_capacity` INT NULL{after_clause}"
        print(f"ðŸ›   {sql}")
        conn.execute(text(sql))
        try:
            conn.commit()
        except AttributeError:
            pass
        print("âœ… manpower_capacity column add ho gaya.")


if __name__ == '__main__':
    migrate()


