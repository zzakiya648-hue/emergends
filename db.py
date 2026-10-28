import sqlite3
import threading

DB = "intern.db"
_lock = threading.Lock()


def _conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _lock:
        c = _conn()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS interns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, email TEXT, domain TEXT,
            skills TEXT, goals TEXT,
            start_date TEXT, end_date TEXT,
            completed INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intern_id INTEGER, week INTEGER,
            description TEXT, deadline TEXT,
            status TEXT DEFAULT 'assigned'
        );
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER, intern_reply TEXT,
            feedback_text TEXT, score INTEGER
        );
        """)
        c.commit()
        c.close()


def query(sql, params=()):
    with _lock:
        c = _conn()
        rows = [dict(r) for r in c.execute(sql, params).fetchall()]
        c.close()
        return rows


def execute(sql, params=()):
    with _lock:
        c = _conn()
        cur = c.execute(sql, params)
        c.commit()
        last = cur.lastrowid
        c.close()
        return last
