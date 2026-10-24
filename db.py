import sqlite3
import os
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(os.getenv("DB_PATH", str(Path(__file__).resolve().parent / "nexusbot.sqlite3")))

def connect():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db(owner_id):
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
          updated_at TEXT NOT NULL, dm_started INTEGER NOT NULL DEFAULT 0
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username COLLATE NOCASE) WHERE username IS NOT NULL;
        CREATE TABLE IF NOT EXISTS name_history(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, username TEXT, first_name TEXT, changed_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS known_groups(
          chat_id INTEGER PRIMARY KEY, title TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS group_users(
          chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL, username TEXT, first_name TEXT,
          updated_at TEXT NOT NULL, PRIMARY KEY(chat_id,user_id)
        );
        CREATE TABLE IF NOT EXISTS filters(
          keyword TEXT PRIMARY KEY COLLATE NOCASE, response TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS media_filters(
          media_key TEXT PRIMARY KEY, media_type TEXT NOT NULL, file_unique_id TEXT NOT NULL,
          response TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
        );
        -- Scoped filter tables keep each group's admins from changing filters in other groups.
        CREATE TABLE IF NOT EXISTS filters_scoped(
          chat_id INTEGER NOT NULL DEFAULT 0, keyword TEXT NOT NULL COLLATE NOCASE,
          response TEXT NOT NULL DEFAULT '', PRIMARY KEY(chat_id, keyword)
        );
        CREATE TABLE IF NOT EXISTS media_filters_scoped(
          chat_id INTEGER NOT NULL DEFAULT 0, media_key TEXT NOT NULL, media_type TEXT NOT NULL,
          file_unique_id TEXT NOT NULL, response TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
          PRIMARY KEY(chat_id, media_key)
        );
        CREATE TABLE IF NOT EXISTS logs(
          id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
          actor_id INTEGER NOT NULL DEFAULT 0, action TEXT NOT NULL,
          target_id INTEGER, details TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS group_scores(
          chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL, username TEXT, first_name TEXT,
          total_points INTEGER NOT NULL DEFAULT 0, aura_points INTEGER NOT NULL DEFAULT 0,
          aura_protect_until REAL NOT NULL DEFAULT 0, updated_at TEXT NOT NULL,
          PRIMARY KEY(chat_id,user_id)
        );
        CREATE TABLE IF NOT EXISTS aura_message_cooldowns(
          chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL, last_award REAL NOT NULL DEFAULT 0,
          PRIMARY KEY(chat_id,user_id)
        );
        """)
        # Safe migration for databases created by earlier RoseBot versions.
        user_columns = {row[1] for row in c.execute("PRAGMA table_info(users)").fetchall()}
        if "dm_started" not in user_columns:
            c.execute("ALTER TABLE users ADD COLUMN dm_started INTEGER NOT NULL DEFAULT 0")
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('owner_id',?)", (str(owner_id),))
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('auto_approve','0')")
        # Preserve filters from older versions as global filters (chat_id=0).
        c.execute("INSERT OR IGNORE INTO filters_scoped(chat_id,keyword,response) SELECT 0,keyword,response FROM filters")
        c.execute("INSERT OR IGNORE INTO media_filters_scoped(chat_id,media_key,media_type,file_unique_id,response,created_at) SELECT 0,media_key,media_type,file_unique_id,response,created_at FROM media_filters")

def upsert_user(user_id, username, first_name):
    username = username.lstrip("@") if username else None
    first_name = first_name or ""
    now = datetime.now(timezone.utc).isoformat()
    with connect() as c:
        old = c.execute("SELECT username,first_name FROM users WHERE user_id=?", (int(user_id),)).fetchone()
        if old and ((old["username"] or None) != username or (old["first_name"] or "") != first_name):
            c.execute("INSERT INTO name_history(user_id,username,first_name,changed_at) VALUES(?,?,?,?)",
                      (int(user_id), old["username"], old["first_name"], now))
        c.execute("""INSERT INTO users(user_id,username,first_name,updated_at) VALUES(?,?,?,?)
          ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name, updated_at=excluded.updated_at""",
          (int(user_id), username, first_name, now))

def get_name_history(user_id, limit=20):
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT username,first_name,changed_at FROM name_history WHERE user_id=? ORDER BY id DESC LIMIT ?", (int(user_id), int(limit))).fetchall()]

def remember_group(chat_id, title):
    now = datetime.now(timezone.utc).isoformat()
    with connect() as c:
        c.execute("INSERT INTO known_groups(chat_id,title,updated_at) VALUES(?,?,?) ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title,updated_at=excluded.updated_at", (int(chat_id), str(title)[:200], now))

def get_known_groups():
    with connect() as c:
        return [r[0] for r in c.execute("SELECT chat_id FROM known_groups ORDER BY updated_at DESC").fetchall()]

def get_broadcast_users():
    with connect() as c:
        return [r[0] for r in c.execute("SELECT user_id FROM users WHERE dm_started=1 ORDER BY updated_at DESC").fetchall()]

def upsert_group_user(chat_id, user_id, username, first_name):
    username = username.lstrip("@") if username else None
    now = datetime.now(timezone.utc).isoformat()
    with connect() as c:
        c.execute("""INSERT INTO group_users(chat_id,user_id,username,first_name,updated_at) VALUES(?,?,?,?,?)
          ON CONFLICT(chat_id,user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name, updated_at=excluded.updated_at""",
          (int(chat_id), int(user_id), username, first_name or "", now))

def list_group_users(chat_id, limit=500):
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT user_id,username,first_name FROM group_users WHERE chat_id=? ORDER BY updated_at DESC LIMIT ?", (int(chat_id), int(limit))).fetchall()]

def get_user_by_username(username):
    with connect() as c:
        row = c.execute("SELECT * FROM users WHERE username=? COLLATE NOCASE", (username.lstrip("@"),)).fetchone()
        return dict(row) if row else None

def get_user_by_id(user_id):
    with connect() as c:
        row = c.execute("SELECT * FROM users WHERE user_id=?", (int(user_id),)).fetchone()
        return dict(row) if row else None

def add_log(actor_id, action, target_id=None, details=""):
    with connect() as c:
        c.execute("INSERT INTO logs(created_at,actor_id,action,target_id,details) VALUES(?,?,?,?,?)",
                  (datetime.now(timezone.utc).isoformat(timespec="seconds"), int(actor_id or 0), action, target_id, str(details)[:1000]))

def is_owner(user_id):
    return int(user_id) == get_owner_id()

def get_owner_id():
    with connect() as c:
        row = c.execute("SELECT value FROM settings WHERE key='owner_id'").fetchone()
        return int(row["value"]) if row else 0

def get_filters(chat_id=None):
    with connect() as c:
        if chat_id is None:
            rows = c.execute("SELECT chat_id,keyword,response FROM filters_scoped ORDER BY chat_id,keyword LIMIT 500").fetchall()
        else:
            rows = c.execute("SELECT chat_id,keyword,response FROM filters_scoped WHERE chat_id IN (0,?) ORDER BY CASE WHEN chat_id=? THEN 0 ELSE 1 END, keyword LIMIT 300", (int(chat_id), int(chat_id))).fetchall()
        return [dict(r) for r in rows]

def add_filter(keyword, response, chat_id=0):
    with connect() as c:
        c.execute("INSERT INTO filters_scoped(chat_id,keyword,response) VALUES(?,?,?) ON CONFLICT(chat_id,keyword) DO UPDATE SET response=excluded.response",
                  (int(chat_id or 0), keyword.strip().lower()[:100], response.strip()[:500]))

def remove_filter(keyword, chat_id=0):
    with connect() as c:
        c.execute("DELETE FROM filters_scoped WHERE chat_id=? AND keyword=? COLLATE NOCASE", (int(chat_id or 0), keyword))

def add_media_filter(media_type, file_unique_id, response, chat_id=0):
    key = f"{media_type}:{file_unique_id}"
    with connect() as c:
        c.execute("INSERT INTO media_filters_scoped(chat_id,media_key,media_type,file_unique_id,response,created_at) VALUES(?,?,?,?,?,?) "
                  "ON CONFLICT(chat_id,media_key) DO UPDATE SET response=excluded.response",
                  (int(chat_id or 0), key, media_type, file_unique_id, response.strip()[:500], datetime.now(timezone.utc).isoformat()))
    return key

def get_media_filters(chat_id=None):
    with connect() as c:
        if chat_id is None:
            rows = c.execute("SELECT chat_id,media_key,media_type,file_unique_id,response,created_at FROM media_filters_scoped ORDER BY created_at DESC LIMIT 500").fetchall()
        else:
            rows = c.execute("SELECT chat_id,media_key,media_type,file_unique_id,response,created_at FROM media_filters_scoped WHERE chat_id IN (0,?) ORDER BY created_at DESC LIMIT 300", (int(chat_id),)).fetchall()
        return [dict(r) for r in rows]

def get_media_filter(media_type, file_unique_id, chat_id=None):
    # Group-specific exact match, then group-wide type match, then legacy/global matches.
    exact_key = f"{media_type}:{file_unique_id}"
    generic_key = f"{media_type}:*"
    chat_ids = [int(chat_id), 0] if chat_id is not None and int(chat_id) != 0 else [0]
    with connect() as c:
        for scope in chat_ids:
            row = c.execute("SELECT * FROM media_filters_scoped WHERE chat_id=? AND media_key=?", (scope, exact_key)).fetchone()
            if row is None:
                row = c.execute("SELECT * FROM media_filters_scoped WHERE chat_id=? AND media_key=?", (scope, generic_key)).fetchone()
            if row:
                return dict(row)
        return None

def remove_media_filter(media_key, chat_id=0):
    with connect() as c:
        c.execute("DELETE FROM media_filters_scoped WHERE chat_id=? AND media_key=?", (int(chat_id or 0), media_key))

def list_users(limit=50):
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT user_id,username FROM users ORDER BY updated_at DESC LIMIT ?", (int(limit),)).fetchall()]

def list_logs(limit=30):
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT created_at,actor_id,action,target_id,details FROM logs ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()]

def get_settings():
    with connect() as c:
        return {r["key"]: r["value"] for r in c.execute("SELECT key,value FROM settings").fetchall()}

def set_setting(key, value):
    with connect() as c:
        c.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

def get_stats():
    with connect() as c:
        users = c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
        filters_count = c.execute("SELECT COUNT(*) n FROM filters").fetchone()["n"]
        media_count = c.execute("SELECT COUNT(*) n FROM media_filters").fetchone()["n"]
        logs = c.execute("SELECT COUNT(*) n FROM logs").fetchone()["n"]
        return {"users": users, "filters": filters_count + media_count, "media_filters": media_count, "logs": logs}


def mark_dm_started(user_id):
    """Record that the user explicitly opened the bot in a private chat."""
    with connect() as c:
        c.execute("UPDATE users SET dm_started=1 WHERE user_id=?", (int(user_id),))


def has_dm_started(user_id):
    with connect() as c:
        row = c.execute("SELECT dm_started FROM users WHERE user_id=?", (int(user_id),)).fetchone()
        return bool(row and row["dm_started"])


def ensure_score(chat_id, user_id, username=None, first_name=None):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as c:
        c.execute("""INSERT INTO group_scores(chat_id,user_id,username,first_name,updated_at) VALUES(?,?,?,?,?)
          ON CONFLICT(chat_id,user_id) DO UPDATE SET username=COALESCE(excluded.username,group_scores.username),
          first_name=COALESCE(excluded.first_name,group_scores.first_name), updated_at=excluded.updated_at""",
          (int(chat_id), int(user_id), username.lstrip("@") if username else None, first_name or "", now))

def adjust_score(chat_id, user_id, username, first_name, total_delta=0, aura_delta=0):
    ensure_score(chat_id, user_id, username, first_name)
    with connect() as c:
        row = c.execute("SELECT aura_protect_until FROM group_scores WHERE chat_id=? AND user_id=?", (int(chat_id), int(user_id))).fetchone()
        if aura_delta < 0 and row and float(row["aura_protect_until"] or 0) > __import__("time").time():
            aura_delta = 0
        c.execute("UPDATE group_scores SET total_points=MAX(0,total_points+?), aura_points=MAX(0,aura_points+?), updated_at=? WHERE chat_id=? AND user_id=?",
          (int(total_delta), int(aura_delta), datetime.now(timezone.utc).isoformat(timespec="seconds"), int(chat_id), int(user_id)))
    return get_score(chat_id, user_id)

def get_score(chat_id, user_id):
    with connect() as c:
        row = c.execute("SELECT * FROM group_scores WHERE chat_id=? AND user_id=?", (int(chat_id), int(user_id))).fetchone()
        return dict(row) if row else None

def leaderboard(chat_id, column="total_points", limit=10):
    if column not in ("total_points", "aura_points"):
        column = "total_points"
    with connect() as c:
        return [dict(r) for r in c.execute(f"SELECT * FROM group_scores WHERE chat_id=? ORDER BY {column} DESC, updated_at ASC LIMIT ?", (int(chat_id), int(limit))).fetchall()]

def worldwide_leaderboard(column="aura_points", limit=10):
    """Aggregate scores across every group, one row per Telegram user."""
    if column not in ("total_points", "aura_points"):
        column = "aura_points"
    with connect() as c:
        sql = f"SELECT user_id, MAX(username) AS username, MAX(first_name) AS first_name, SUM({column}) AS score FROM group_scores GROUP BY user_id ORDER BY score DESC, user_id ASC LIMIT ?"
        return [dict(r) for r in c.execute(sql, (int(limit),)).fetchall()]

def can_award_message_aura(chat_id, user_id, cooldown_seconds=60):
    """Limit sentiment Aura to one qualifying message per user per group per cooldown."""
    import time
    now = time.time()
    with connect() as c:
        row = c.execute("SELECT last_award FROM aura_message_cooldowns WHERE chat_id=? AND user_id=?", (int(chat_id), int(user_id))).fetchone()
        if row and now - float(row["last_award"]) < int(cooldown_seconds):
            return False
        c.execute("INSERT INTO aura_message_cooldowns(chat_id,user_id,last_award) VALUES(?,?,?) ON CONFLICT(chat_id,user_id) DO UPDATE SET last_award=excluded.last_award", (int(chat_id), int(user_id), now))
        return True

def buy_aura_protection(chat_id, user_id, username, first_name, days, cost):
    ensure_score(chat_id, user_id, username, first_name)
    import time
    now = time.time()
    with connect() as c:
        row = c.execute("SELECT total_points,aura_protect_until FROM group_scores WHERE chat_id=? AND user_id=?", (int(chat_id), int(user_id))).fetchone()
        if int(row["total_points"]) < int(cost):
            return False, dict(row)
        until = max(now, float(row["aura_protect_until"] or 0)) + int(days) * 86400
        c.execute("UPDATE group_scores SET total_points=total_points-?, aura_protect_until=?, updated_at=? WHERE chat_id=? AND user_id=?",
          (int(cost), until, datetime.now(timezone.utc).isoformat(timespec="seconds"), int(chat_id), int(user_id)))
        fresh = c.execute("SELECT * FROM group_scores WHERE chat_id=? AND user_id=?", (int(chat_id), int(user_id))).fetchone()
        return True, dict(fresh)


def set_free_member(chat_id, user_id, enabled=True):
    """Persist anti-spam exemption for a member in one group."""
    key = f"free:{int(chat_id)}:{int(user_id)}"
    if enabled:
        set_setting(key, "1")
    else:
        with connect() as c:
            c.execute("DELETE FROM settings WHERE key=?", (key,))

def is_free_member(chat_id, user_id):
    return get_settings().get(f"free:{int(chat_id)}:{int(user_id)}", "0") == "1"


def get_owner_dashboard_stats():
    """Return counts that the bot has actually observed and recorded."""
    with connect() as c:
        users = c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
        dm_started = c.execute("SELECT COUNT(*) n FROM users WHERE dm_started=1").fetchone()["n"]
        groups = c.execute("SELECT COUNT(*) n FROM known_groups").fetchone()["n"]
        group_members = c.execute("SELECT COUNT(DISTINCT user_id) n FROM group_users").fetchone()["n"]
        group_memberships = c.execute("SELECT COUNT(*) n FROM group_users").fetchone()["n"]
        return {"recorded_users": users, "dm_started": dm_started, "groups": groups,
                "unique_group_members": group_members, "group_memberships": group_memberships}
