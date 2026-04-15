import sqlite3

def get_conn():
    return sqlite3.connect("fire_alarm.db")

def delete_inspection(insp_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM inspections WHERE id=?", (insp_id,))
        conn.commit()
