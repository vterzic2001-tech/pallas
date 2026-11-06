# storage.py
import json
import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "output/pallas.db")


def get_conn():
    d = os.path.dirname(DB_PATH)
    if d:
        os.makedirs(d, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT
            );
            CREATE TABLE IF NOT EXISTS zadaci (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                category_slug TEXT NOT NULL,
                difficulty INTEGER NOT NULL,
                stem TEXT NOT NULL,
                options_json TEXT NOT NULL,
                correct_index INTEGER NOT NULL,
                rule TEXT NOT NULL,
                derivation TEXT,
                why_wrong_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS pokusaji (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                zadatak_id INTEGER,
                category_slug TEXT NOT NULL,
                difficulty INTEGER NOT NULL,
                user_index INTEGER NOT NULL,
                correct_index INTEGER NOT NULL,
                is_correct INTEGER NOT NULL,
                time_ms INTEGER,
                explanation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_pokusaji_user ON pokusaji(user_id);
        """)


def seed_db():
    cats = [
        ("sequences", "Number Sequences", "Find the rule governing a numeric sequence."),
        ("analogies", "Verbal Analogies", "Identify the semantic relation between word pairs."),
        ("matrices", "Matrix Reasoning", "Detect the pattern in a 3x3 grid."),
    ]
    with get_conn() as c:
        for slug, name, desc in cats:
            c.execute(
                "INSERT OR IGNORE INTO categories (slug, name, description) VALUES (?,?,?)",
                (slug, name, desc),
            )


def create_user(email, password_hash):
    try:
        with get_conn() as c:
            cur = c.execute(
                "INSERT INTO users (email, password_hash) VALUES (?,?)",
                (email, password_hash),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def get_user_by_email(email):
    with get_conn() as c:
        r = c.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return dict(r) if r else None


def get_user_by_id(uid):
    with get_conn() as c:
        r = c.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    return dict(r) if r else None


def save_task(user_id, task):
    with get_conn() as c:
        cur = c.execute(
            """INSERT INTO zadaci
               (user_id, category_slug, difficulty, stem, options_json,
                correct_index, rule, derivation, why_wrong_json)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                user_id,
                task["category"],
                task["difficulty"],
                task["stem"],
                json.dumps(task["options"]),
                task["correct_index"],
                task["rule"],
                task.get("derivation", ""),
                json.dumps(task.get("why_wrong", {})),
            ),
        )
        return cur.lastrowid


def get_task_by_id(task_id):
    with get_conn() as c:
        r = c.execute("SELECT * FROM zadaci WHERE id = ?", (task_id,)).fetchone()
    if not r:
        return None
    return {
        "id": r["id"],
        "category": r["category_slug"],
        "difficulty": r["difficulty"],
        "stem": r["stem"],
        "options": json.loads(r["options_json"]),
        "correct_index": r["correct_index"],
        "rule": r["rule"],
        "derivation": r["derivation"] or "",
        "why_wrong": json.loads(r["why_wrong_json"] or "{}"),
    }


def get_last_stem(user_id, category):
    with get_conn() as c:
        r = c.execute(
            "SELECT stem FROM zadaci WHERE user_id = ? AND category_slug = ? "
            "ORDER BY id DESC LIMIT 1",
            (user_id, category),
        ).fetchone()
    return r["stem"] if r else None


def save_attempt(user_id, task_id, category, difficulty, user_index,
                 correct_index, is_correct, time_ms, explanation):
    with get_conn() as c:
        c.execute(
            """INSERT INTO pokusaji
               (user_id, zadatak_id, category_slug, difficulty, user_index,
                correct_index, is_correct, time_ms, explanation)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (user_id, task_id, category, difficulty, user_index,
             correct_index, 1 if is_correct else 0, time_ms, explanation),
        )


def get_progress(user_id):
    with get_conn() as c:
        rows = c.execute(
            """SELECT category_slug,
                      COUNT(*) AS total,
                      SUM(is_correct) AS correct,
                      AVG(time_ms) AS avg_time
               FROM pokusaji WHERE user_id = ?
               GROUP BY category_slug""",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_days_practiced(user_id):
    with get_conn() as c:
        r = c.execute(
            "SELECT COUNT(DISTINCT DATE(created_at)) AS d FROM pokusaji WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return r["d"] if r else 0
