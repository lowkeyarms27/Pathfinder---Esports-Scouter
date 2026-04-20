import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "pathfinder.db")


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS scouting_sessions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                vod_filename     TEXT,
                player_handle    TEXT,
                game             TEXT DEFAULT 'r6siege',
                team             TEXT,
                status           TEXT DEFAULT 'uploading',
                error_message    TEXT,
                agent_log_live   TEXT,
                full_result      TEXT,
                created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS player_profiles (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id       INTEGER,
                player_handle    TEXT,
                archetype        TEXT,
                style_vector     TEXT,
                pro_match_handle TEXT,
                pro_match_team   TEXT,
                similarity_score REAL,
                market_value     INTEGER,
                risk_tier        TEXT,
                summary          TEXT,
                FOREIGN KEY (session_id) REFERENCES scouting_sessions(id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pro_archetypes (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                handle           TEXT UNIQUE,
                team             TEXT,
                role             TEXT,
                nationality      TEXT,
                operators        TEXT,
                style_vector     TEXT,
                source_url       TEXT,
                events           INTEGER DEFAULT 0,
                scraped_at       DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Migration: add events column to existing tables that predate this schema
        try:
            conn.execute("ALTER TABLE pro_archetypes ADD COLUMN events INTEGER DEFAULT 0")
        except Exception:
            pass
        conn.commit()


def create_session(vod_filename: str, player_handle: str, game: str, team: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            '''INSERT INTO scouting_sessions (vod_filename, player_handle, game, team, status)
               VALUES (?, ?, ?, ?, ?)''',
            (vod_filename, player_handle, game, team, "uploading")
        )
        conn.commit()
        return cur.lastrowid


def update_session(session_id: int, **kwargs):
    if not kwargs:
        return
    with get_connection() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        conn.execute(
            f"UPDATE scouting_sessions SET {set_clause} WHERE id = ?",
            (*kwargs.values(), session_id)
        )
        conn.commit()


def append_agent_log_event(session_id: int, event: dict):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT agent_log_live FROM scouting_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not row:
            return
        existing = []
        try:
            existing = json.loads(row["agent_log_live"] or "[]")
        except Exception:
            pass
        existing.append(event)
        conn.execute(
            "UPDATE scouting_sessions SET agent_log_live = ? WHERE id = ?",
            (json.dumps(existing), session_id)
        )
        conn.commit()


def get_agent_log_live(session_id: int) -> list:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT agent_log_live FROM scouting_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not row or not row["agent_log_live"]:
            return []
        try:
            return json.loads(row["agent_log_live"])
        except Exception:
            return []


def save_player_profile(session_id: int, profile: dict):
    with get_connection() as conn:
        conn.execute(
            '''INSERT INTO player_profiles
               (session_id, player_handle, archetype, style_vector, pro_match_handle,
                pro_match_team, similarity_score, market_value, risk_tier, summary)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                session_id,
                profile.get("player_handle"),
                profile.get("archetype"),
                json.dumps(profile.get("style_vector", {})),
                profile.get("pro_match_handle"),
                profile.get("pro_match_team"),
                profile.get("similarity_score"),
                profile.get("market_value"),
                profile.get("risk_tier"),
                profile.get("summary"),
            )
        )
        conn.commit()


def get_session(session_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM scouting_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return dict(row) if row else None


def get_results(session_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM scouting_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        if data.get("full_result"):
            data["full_result"] = json.loads(data["full_result"])
        profile = conn.execute(
            "SELECT * FROM player_profiles WHERE session_id = ? ORDER BY id DESC LIMIT 1",
            (session_id,)
        ).fetchone()
        data["player_profile"] = dict(profile) if profile else None
        return data


def list_sessions(limit: int = 100) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            '''SELECT s.id, s.vod_filename, s.player_handle, s.game, s.team,
                      s.status, s.error_message, s.created_at,
                      p.archetype, p.pro_match_handle, p.similarity_score, p.market_value
               FROM scouting_sessions s
               LEFT JOIN player_profiles p ON p.session_id = s.id
               ORDER BY s.id DESC LIMIT ?''',
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def upsert_pro_archetype(handle: str, data: dict):
    with get_connection() as conn:
        conn.execute(
            '''INSERT INTO pro_archetypes (handle, team, role, nationality, operators, style_vector, source_url, events)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(handle) DO UPDATE SET
                 team=excluded.team, role=excluded.role, nationality=excluded.nationality,
                 operators=excluded.operators, style_vector=excluded.style_vector,
                 source_url=excluded.source_url, events=excluded.events,
                 scraped_at=CURRENT_TIMESTAMP''',
            (
                handle,
                data.get("team"),
                data.get("role"),
                data.get("nationality"),
                json.dumps(data.get("operators", [])),
                json.dumps(data.get("style_vector", {})),
                data.get("source_url"),
                data.get("events", 0),
            )
        )
        conn.commit()


def get_all_pro_archetypes() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM pro_archetypes ORDER BY role, handle").fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["operators"] = json.loads(d.get("operators") or "[]")
            d["style_vector"] = json.loads(d.get("style_vector") or "{}")
            result.append(d)
        return result
