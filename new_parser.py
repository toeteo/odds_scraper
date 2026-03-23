import json
import time
import sqlite3
import pandas as pd
from settings import *


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;
        PRAGMA cache_size = -32000;
        PRAGMA temp_store = MEMORY;

        CREATE TABLE IF NOT EXISTS events (
            event_id   INTEGER PRIMARY KEY,
            match      TEXT,
            date       TEXT,
            league     TEXT,
            sport      TEXT,
            country    TEXT,
            is_live    BOOLEAN,
            home_team  TEXT,
            away_team  TEXT,
            scraped_at INTEGER
        );

        CREATE TABLE IF NOT EXISTS odds (
            event_id     INTEGER REFERENCES events(event_id),
            market       TEXT,
            is_spread    BOOLEAN,
            default_line REAL,
            line         REAL,
            selection    TEXT,
            odd          REAL,
            UNIQUE(event_id, market, line, selection)
        );

        CREATE INDEX IF NOT EXISTS idx_odds_event ON odds(event_id);
    """)
    return conn


def insert_odds(conn: sqlite3.Connection, df: pd.DataFrame):
    scraped_at = int(time.time())

    # Upsert events
    df_events = df[["event_id", "match", "date", "league", "sport",
                    "country", "is_live", "home_team", "away_team"]].drop_duplicates()
    for _, row in df_events.iterrows():
        conn.execute("""
            INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(event_id) DO UPDATE SET scraped_at=excluded.scraped_at
        """, (*row, scraped_at))

    # Upsert odds — always keep latest value
    df_odds = df[["event_id", "market", "is_spread", "default_line",
                  "line", "selection", "odd"]]
    for _, row in df_odds.iterrows():
        conn.execute("""
            INSERT INTO odds VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(event_id, market, line, selection)
            DO UPDATE SET odd=excluded.odd, is_spread=excluded.is_spread
        """, tuple(row))

    conn.commit()
    print(f"[db] upserted {len(df_events)} events, {len(df_odds)} odds rows")


def parse_odds(data: dict) -> tuple[list[dict], pd.DataFrame]:
    """
    Returns:
        structured: clean list of dicts (one per event) with nested markets
        df:         flat DataFrame (one row per selection)
    """
    events = data["leo"]
    structured = []
    rows = []

    for event in events:
        event_info = {
            "event_id":  event["ei"],
            "match":     event["en"],
            "date":      event["ed"],
            "league":    event["td"],
            "sport":     event["sn"],
            "country":   event["cd"],
            "is_live":   event["ia"],
            "home_team": event["teams"][0]["nm"] if len(event.get("teams", [])) > 0 else None,
            "away_team": event["teams"][1]["nm"] if len(event.get("teams", [])) > 1 else None,
        }

        markets_clean = {}
        for _, market in event.get("mmkW", {}).items():
            market_name = market["mn"].strip()
            lines = {}

            for line_val, line_data in market["spd"].items():
                active = [
                    {"selection": s["sn"], "odd": s["ov"]}
                    for s in line_data["asl"]
                    if not (s["si"] == 0 and s["ov"] == 0.0 and s["cls"] == 0)
                ]
                if active:
                    lines[line_val] = active
                    for sel in active:
                        rows.append({
                            **event_info,
                            "market":       market_name,
                            "is_spread":    market["smk"],
                            "default_line": market["ds"],
                            "line":         float(line_val),
                            "selection":    sel["selection"],
                            "odd":          sel["odd"],
                        })

            if lines:
                markets_clean[market_name] = {
                    "is_spread":    market["smk"],
                    "default_line": market["ds"],
                    "lines":        lines,
                }

        structured.append({**event_info, "markets": markets_clean})

    return structured, pd.DataFrame(rows)


def parse_and_store(data: dict, conn: sqlite3.Connection):
    """Main entry point — parse API response and insert into DB."""
    _, df = parse_odds(data)
    if not df.empty:
        insert_odds(conn, df)
    return df


if __name__ == "__main__":
    import os
    file_path = os.path.join(RESPONSES_PATH, "match_detail.json")
    with open(file_path) as f:
        data = json.load(f)

    conn = get_connection()
    parse_and_store(data, conn)