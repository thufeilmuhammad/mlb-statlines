import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'statlines.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Player game logs — one row per player per game
    c.execute('''
        CREATE TABLE IF NOT EXISTS game_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id TEXT,
            player_name TEXT,
            team TEXT,
            game_date TEXT,
            game_pk TEXT,
            pa INTEGER,
            ab INTEGER,
            hits INTEGER,
            doubles INTEGER,
            triples INTEGER,
            hr INTEGER,
            rbi INTEGER,
            bb INTEGER,
            k INTEGER,
            hbp INTEGER,
            reached_base INTEGER,
            obp REAL,
            avg REAL,
            slg REAL,
            ops REAL,
            UNIQUE(player_id, game_date)
        )
    ''')

    # Pitcher game logs
    c.execute('''
        CREATE TABLE IF NOT EXISTS pitcher_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id TEXT,
            player_name TEXT,
            team TEXT,
            game_date TEXT,
            game_pk TEXT,
            ip REAL,
            hits_allowed INTEGER,
            runs INTEGER,
            er INTEGER,
            bb INTEGER,
            k INTEGER,
            hr_allowed INTEGER,
            pitch_count INTEGER,
            era REAL,
            whip REAL,
            UNIQUE(player_id, game_date)
        )
    ''')

    # Season stats — refreshed daily
    c.execute('''
        CREATE TABLE IF NOT EXISTS season_batting (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id TEXT,
            player_name TEXT,
            team TEXT,
            season INTEGER,
            g INTEGER,
            pa INTEGER,
            ab INTEGER,
            hits INTEGER,
            hr INTEGER,
            rbi INTEGER,
            sb INTEGER,
            avg REAL,
            obp REAL,
            slg REAL,
            ops REAL,
            woba REAL,
            war REAL,
            pulled_date TEXT,
            UNIQUE(player_id, season)
        )
    ''')

    # Season pitching stats
    c.execute('''
        CREATE TABLE IF NOT EXISTS season_pitching (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id TEXT,
            player_name TEXT,
            team TEXT,
            season INTEGER,
            g INTEGER,
            gs INTEGER,
            ip REAL,
            w INTEGER,
            l INTEGER,
            sv INTEGER,
            k INTEGER,
            bb INTEGER,
            hr INTEGER,
            era REAL,
            whip REAL,
            k9 REAL,
            bb9 REAL,
            fip REAL,
            war REAL,
            pulled_date TEXT,
            UNIQUE(player_id, season)
        )
    ''')

    # Standings
    c.execute('''
        CREATE TABLE IF NOT EXISTS standings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team TEXT,
            division TEXT,
            w INTEGER,
            l INTEGER,
            pct REAL,
            gb TEXT,
            pulled_date TEXT,
            UNIQUE(team, pulled_date)
        )
    ''')

    # Story candidates log — tracks what we've posted
    c.execute('''
        CREATE TABLE IF NOT EXISTS story_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_type TEXT,
            entity_id TEXT,
            entity_name TEXT,
            score REAL,
            headline TEXT,
            posted INTEGER DEFAULT 0,
            posted_date TEXT,
            created_date TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == '__main__':
    init_db()