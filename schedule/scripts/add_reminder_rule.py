#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
from datetime import datetime


ROOT = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, "backend", "schedule.db")


def parse_hm(value):
    parts = value.split(":")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("time must use HH:MM")
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError("time must use HH:MM") from exc
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise argparse.ArgumentTypeError("time must use HH:MM")
    return f"{hour:02d}:{minute:02d}"


def parse_date(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD") from exc
    return value


def ensure_schema(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS reminder_rules ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "name TEXT NOT NULL,"
        "kind TEXT NOT NULL,"
        "time TEXT NOT NULL,"
        "date TEXT,"
        "day INTEGER,"
        "enabled INTEGER DEFAULT 1,"
        "last_triggered TEXT,"
        "created_at TEXT DEFAULT (datetime('now'))"
        ")"
    )
    conn.commit()


def validate_rule(kind, date, day):
    if kind not in {"once", "daily", "weekly", "monthly"}:
        raise ValueError("kind must be one of once,daily,weekly,monthly")
    if kind == "once" and not date:
        raise ValueError("date is required for once rules")
    if kind == "weekly" and (day is None or not 0 <= day <= 6):
        raise ValueError("day must be 0-6 for weekly rules")
    if kind == "monthly" and (day is None or not 1 <= day <= 31):
        raise ValueError("day must be 1-31 for monthly rules")


def add_rule(name, kind, time_text, date, day, enabled):
    validate_rule(kind, date, day)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    cur = conn.execute(
        "INSERT INTO reminder_rules (name, kind, time, date, day, enabled) "
        "VALUES (?,?,?,?,?,?)",
        (name, kind, time_text, date, day, 1 if enabled else 0),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM reminder_rules WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)


def main():
    parser = argparse.ArgumentParser(
        description="Add a scheduled rule that sends pending Schedule tasks through cc-connect."
    )
    parser.add_argument("--name", required=True)
    parser.add_argument("--kind", required=True, choices=["once", "daily", "weekly", "monthly"])
    parser.add_argument("--time", required=True, type=parse_hm, help="HH:MM")
    parser.add_argument("--date", type=parse_date, help="YYYY-MM-DD, required for once")
    parser.add_argument("--day", type=int, help="0-6 for weekly, 1-31 for monthly")
    parser.add_argument("--disabled", action="store_true")
    args = parser.parse_args()

    try:
        row = add_rule(args.name, args.kind, args.time, args.date, args.day, not args.disabled)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)

    print(json.dumps({"ok": True, "rule": row}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
