# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
add_wop_to_attendance_status.py
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Run this ONCE to extend `attendance.status` ENUM and add 'WOP'
(Week Off Present â€” employee ne weekly off pe punch kiya hai).

Usage:  python add_wop_to_attendance_status.py
Pre-req: pip install pymysql
"""
import pymysql

# â”€â”€ DB Config â€” apna update karo agar zarurat ho â”€â”€
DB_HOST = 'localhost'
DB_PORT = 3306
DB_USER = 'root'
DB_PASS = 'Krunal@2424'
DB_NAME = 'erpdb'


def migrate():
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS,
        database=DB_NAME, charset='utf8mb4'
    )
    cur = conn.cursor()

    # Check current ENUM definition
    cur.execute("""
        SELECT COLUMN_TYPE FROM information_schema.COLUMNS
         WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'attendance'
           AND COLUMN_NAME = 'status'
    """, (DB_NAME,))
    row = cur.fetchone()
    if not row:
        print("âŒ attendance.status column not found")
        return

    current = row[0]
    print(f"Current ENUM: {current}")

    if "'WOP'" in current:
        print("â­  WOP already in ENUM. Nothing to do.")
        cur.close(); conn.close()
        return

    sql = """
        ALTER TABLE attendance
        MODIFY COLUMN status
        ENUM('Present','Absent','Half Day','Holiday','MIS-PUNCH','WOP')
        NOT NULL DEFAULT 'Present'
    """
    cur.execute(sql)
    conn.commit()
    print("âœ… WOP added to attendance.status ENUM")
    cur.close(); conn.close()


if __name__ == '__main__':
    migrate()


