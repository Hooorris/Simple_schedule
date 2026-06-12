#!/usr/bin/env python3
import sqlite3, os
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DB_PATH = os.path.join(os.path.dirname(__file__), "schedule.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE IF NOT EXISTS events ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 100),"
        "start_time TEXT NOT NULL,"
        "end_time TEXT,"
        "note TEXT DEFAULT '' CHECK(length(note) <= 500),"
        "cost_factor REAL DEFAULT 0.0,"
        "created_at TEXT DEFAULT (datetime('now')),"
        "updated_at TEXT DEFAULT (datetime('now'))"
    ")")
    return conn

def validate_no_cross_day(start: str, end: Optional[str]):
    if not end: return
    if start[:10] != end[:10]:
        raise HTTPException(422, "start and end must be on the same day")

class EventCreate(BaseModel):
    title: str
    start_time: str
    end_time: Optional[str] = None
    note: Optional[str] = ""

class EventUpdate(BaseModel):
    title: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    note: Optional[str] = None

class BatchDelete(BaseModel):
    ids: list[int]

app = FastAPI(title="Schedule", version="1.0.0", docs_url="/api/docs")

@app.get("/api/v1/db-events")
def db_events_direct(start: str = "", end: str = ""):
    conn = get_db()
    if start and end:
        rows = conn.execute("SELECT * FROM events WHERE date(start_time) BETWEEN ? AND ? ORDER BY start_time", (start, end)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM events ORDER BY start_time").fetchall()
    return [dict(r) for r in rows]

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/v1/events")
def list_events(start: str = Query(""), end: str = Query("")):
    conn = get_db()
    if start and end:
        rows = conn.execute("SELECT * FROM events WHERE date(start_time) BETWEEN ? AND ? ORDER BY start_time", (start, end)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM events ORDER BY start_time").fetchall()
    return [dict(r) for r in rows]

@app.get("/api/v1/events/{eid}")
def get_event(eid: int):
    row = get_db().execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()
    if not row: raise HTTPException(404)
    return dict(row)

@app.post("/api/v1/events", status_code=201)
def create_event(ev: EventCreate):
    validate_no_cross_day(ev.start_time, ev.end_time)
    conn = get_db()
    cur = conn.execute("INSERT INTO events (title, start_time, end_time, note, cost_factor) VALUES (?,?,?,?,?)",
        (ev.title, ev.start_time, ev.end_time or "", ev.note or "", ev.cost_factor))
    conn.commit()
    return dict(conn.execute("SELECT * FROM events WHERE id=?", (cur.lastrowid,)).fetchone())

@app.put("/api/v1/events/{eid}")
def update_event(eid: int, ev: EventUpdate):
    conn = get_db()
    row = conn.execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()
    if not row: raise HTTPException(404)
    data = dict(row)
    if ev.title is not None: data["title"] = ev.title
    if ev.start_time is not None: data["start_time"] = ev.start_time
    if ev.end_time is not None: data["end_time"] = ev.end_time
    if ev.note is not None: data["note"] = ev.note
    if ev.cost_factor is not None: data["cost_factor"] = ev.cost_factor
    validate_no_cross_day(data["start_time"], data["end_time"])
    conn.execute("UPDATE events SET title=?, start_time=?, end_time=?, note=?, cost_factor=?, updated_at=datetime('now') WHERE id=?",
        (data["title"], data["start_time"], data["end_time"], data["note"], data["cost_factor"], eid))
    conn.commit()
    return dict(conn.execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone())

@app.delete("/api/v1/events/{eid}")
def delete_event(eid: int):
    conn = get_db()
    conn.execute("DELETE FROM events WHERE id=?", (eid,))
    conn.commit()
    return {"ok": True}

@app.delete("/api/v1/events")
def batch_delete(body: BatchDelete):
    conn = get_db()
    placeholders = ",".join("?" for _ in body.ids)
    conn.execute(f"DELETE FROM events WHERE id IN ({placeholders})", body.ids)
    conn.commit()
    return {"ok": True, "deleted": len(body.ids)}

if __name__ == "__main__":
    import uvicorn, sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    uvicorn.run(app, host="0.0.0.0", port=port)
