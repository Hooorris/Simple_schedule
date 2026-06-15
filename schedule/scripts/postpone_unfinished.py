#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
from datetime import date as date_cls, datetime, timedelta


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


def pending_tasks(conn, source_date):
    rows = conn.execute(
        "SELECT id, title, date, priority, completed, note "
        "FROM events "
        "WHERE date=? AND (completed IS NULL OR completed=0) "
        "ORDER BY priority DESC, id ASC",
        (source_date,),
    ).fetchall()
    return [dict(row) for row in rows]


def postpone_unfinished(source_date):
    target_date = (
        datetime.strptime(source_date, "%Y-%m-%d") + timedelta(days=1)
    ).strftime("%Y-%m-%d")
    conn = get_db()
    tasks = pending_tasks(conn, source_date)
    if tasks:
        ids = [task["id"] for task in tasks]
        placeholders = ",".join("?" for _ in ids)
        cols = [row[1] for row in conn.execute("PRAGMA table_info(events)").fetchall()]
        params = [target_date]
        if "start_time" in cols:
            set_clause = "date=?, start_time=?, updated_at=datetime('now')"
            params.append(f"{target_date}T00:00:00")
        else:
            set_clause = "date=?, updated_at=datetime('now')"
        params.extend(ids)
        conn.execute(
            f"UPDATE events SET {set_clause} WHERE id IN ({placeholders})",
            params,
        )
    conn.commit()
    conn.close()
    return {
        "ok": True,
        "from_date": source_date,
        "to_date": target_date,
        "moved": len(tasks),
        "tasks": tasks,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Postpone unfinished Schedule tasks from a date to the next day."
    )
    parser.add_argument(
        "--date",
        type=valid_date,
        default=date_cls.today().strftime("%Y-%m-%d"),
        help="Source date in YYYY-MM-DD, defaults to today.",
    )
    args = parser.parse_args()

    try:
        result = postpone_unfinished(args.date)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
