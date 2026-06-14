#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
from datetime import datetime


ROOT = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, "backend", "schedule.db")


def valid_date(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD") from exc
    return value


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS events ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 100),"
        "date TEXT NOT NULL,"
        "priority INTEGER DEFAULT 0,"
        "completed INTEGER DEFAULT 0,"
        "note TEXT DEFAULT '' CHECK(length(note) <= 500),"
        "created_at TEXT DEFAULT (datetime('now')),"
        "updated_at TEXT DEFAULT (datetime('now'))"
        ")"
    )
    cols = [row[1] for row in conn.execute("PRAGMA table_info(events)").fetchall()]
    if "date" not in cols:
        conn.execute("ALTER TABLE events ADD COLUMN date TEXT")
        if "start_time" in cols:
            conn.execute(
                "UPDATE events SET date = substr(start_time,1,10) "
                "WHERE date IS NULL OR date = ''"
            )
    if "priority" not in cols:
        conn.execute("ALTER TABLE events ADD COLUMN priority INTEGER DEFAULT 0")
    if "completed" not in cols:
        conn.execute("ALTER TABLE events ADD COLUMN completed INTEGER DEFAULT 0")
    conn.commit()
    return conn


def add_reminder(title, date, priority, note):
    title = title.strip()
    note = note.strip()
    if not 1 <= len(title) <= 100:
        raise ValueError("title length must be between 1 and 100")
    if len(note) > 500:
        raise ValueError("note length must be <= 500")

    conn = get_db()
    cols = [row[1] for row in conn.execute("PRAGMA table_info(events)").fetchall()]
    completed = 0

    if "start_time" in cols:
        start_time = f"{date}T00:00:00"
        cur = conn.execute(
            "INSERT INTO events (title, date, priority, completed, note, start_time) "
            "VALUES (?,?,?,?,?,?)",
            (title, date, priority, completed, note, start_time),
        )
    else:
        cur = conn.execute(
            "INSERT INTO events (title, date, priority, completed, note) "
            "VALUES (?,?,?,?,?)",
            (title, date, priority, completed, note),
        )
    conn.commit()
    row = conn.execute("SELECT * FROM events WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)


def main():
    parser = argparse.ArgumentParser(
        description="Add a Schedule reminder/task from WeChat or local automation."
    )
    parser.add_argument("--title", required=True, help="Reminder title, 1-100 chars")
    parser.add_argument("--date", required=True, type=valid_date, help="YYYY-MM-DD")
    parser.add_argument("--priority", type=int, default=0, help="Higher comes first")
    parser.add_argument("--note", default="", help="Optional note, max 500 chars")
    args = parser.parse_args()

    try:
        row = add_reminder(args.title, args.date, args.priority, args.note)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)

    print(json.dumps({"ok": True, "event": row}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
