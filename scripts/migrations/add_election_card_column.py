# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
Run this script ONCE to add `election_card_no` column to the `employees`
table in your MySQL database (erpdb).

Usage:
    python add_election_card_column.py

Yeh script `config.py` se DB URI automatically uthata hai.
Agar DATABASE_URL env var set hai to wo use hogi.
"""
import os
import sys


def _load_uri():
    """Pick up the DB URI from config.py (or DATABASE_URL env)."""
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


def _safe_uri(uri: str) -> str:
    """Mask password for log output."""
    try:
        # mysql+pymysql://user:PASSWORD@host:port/db
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
        print("âŒ DB URI nahi mili. config.py check karo.")
        return

    print(f"ðŸ”— DB URI: {_safe_uri(uri)}")

    try:
        from sqlalchemy import create_engine, text, inspect
    except ImportError:
        print("âŒ SQLAlchemy install nahi hai. pip install sqlalchemy pymysql cryptography")
        return

    try:
        engine = create_engine(uri, pool_pre_ping=True)
    except Exception as e:
        print(f"âŒ Engine create nahi hua: {e}")
        return

    try:
        with engine.connect() as conn:
            insp = inspect(conn)
            tables = insp.get_table_names()
            if 'employees' not in tables:
                print("âŒ 'employees' table nahi mili!")
                print(f"ðŸ“‹ Available tables ({len(tables)}): {tables[:25]}{' ...' if len(tables) > 25 else ''}")
                return
            print("âœ… 'employees' table mil gayi.")

            cols = [c['name'] for c in insp.get_columns('employees')]
            if 'election_card_no' in cols:
                print("â„¹ï¸  election_card_no column already exists â€” kuch karne ki zarurat nahi.")
                return

            # MySQL: ADD COLUMN with safe placement (after pan_number if it exists)
            after_clause = " AFTER `pan_number`" if 'pan_number' in cols else ""
            sql = f"ALTER TABLE `employees` ADD COLUMN `election_card_no` VARCHAR(30) NULL{after_clause}"
            print(f"ðŸ›   Running: {sql}")
            conn.execute(text(sql))
            try:
                conn.commit()                # SQLAlchemy 2.x
            except AttributeError:
                pass                          # 1.x autocommits via begin()
            print("âœ… election_card_no column add ho gaya.")
    except Exception as e:
        print(f"âŒ Migration fail hui: {e}")
        return


if __name__ == '__main__':
    migrate()


