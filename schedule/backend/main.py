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
    # 新的 events 结构：使用 `date` 字段（YYYY-MM-DD），并增加 `priority` 与 `completed`
    conn.execute("CREATE TABLE IF NOT EXISTS events ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 100),"
        "date TEXT NOT NULL,"
        "priority INTEGER DEFAULT 0,"
        "completed INTEGER DEFAULT 0,"
        "note TEXT DEFAULT '' CHECK(length(note) <= 500),"
        "created_at TEXT DEFAULT (datetime('now')),"
        "updated_at TEXT DEFAULT (datetime('now'))"
    ")")
    # 兼容迁移：如果旧表存在但缺少新字段，尝试添加列并填充 date（从 start_time 截取日期）
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()]
        if 'date' not in cols:
            conn.execute("ALTER TABLE events ADD COLUMN date TEXT")
            # 如果存在 start_time 列，则尝试从中填充 date
            if 'start_time' in cols:
                conn.execute("UPDATE events SET date = substr(start_time,1,10) WHERE date IS NULL OR date = ''")
        if 'priority' not in cols:
            conn.execute("ALTER TABLE events ADD COLUMN priority INTEGER DEFAULT 0")
        if 'completed' not in cols:
            conn.execute("ALTER TABLE events ADD COLUMN completed INTEGER DEFAULT 0")
    except Exception:
        pass
    return conn

def validate_no_cross_day(start: str, end: Optional[str]):
    # 时间相关校验已废弃（项目改为按日期记录），保留空实现以兼容调用。
    return

class EventCreate(BaseModel):
    title: str
    date: str
    priority: int = 0
    completed: bool = False
    note: Optional[str] = ""

class EventUpdate(BaseModel):
    title: Optional[str] = None
    date: Optional[str] = None
    priority: Optional[int] = None
    completed: Optional[bool] = None
    note: Optional[str] = None

class BatchDelete(BaseModel):
    ids: list[int]

app = FastAPI(title="Schedule", version="1.0.0", docs_url="/api/docs")

@app.get("/api/v1/db-events")
def db_events_direct(start: str = "", end: str = ""):
    conn = get_db()
    if start and end:
        rows = conn.execute("SELECT * FROM events WHERE date BETWEEN ? AND ? ORDER BY priority DESC, date", (start, end)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM events ORDER BY priority DESC, date").fetchall()
    return [dict(r) for r in rows]

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/v1/events")
def list_events(start: str = Query(""), end: str = Query("")):
    conn = get_db()
    # 动态检测列以兼容老 schema（避免 ORDER BY 缺失列时报错）
    cols = [r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()]
    order_clause = "ORDER BY priority DESC, date" if 'priority' in cols else "ORDER BY date"
    if start and end:
        rows = conn.execute(f"SELECT * FROM events WHERE date BETWEEN ? AND ? {order_clause}", (start, end)).fetchall()
    else:
        rows = conn.execute(f"SELECT * FROM events {order_clause}").fetchall()
    return [dict(r) for r in rows]

@app.get("/api/v1/events/{eid}")
def get_event(eid: int):
    row = get_db().execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()
    if not row: raise HTTPException(404)
    return dict(row)

@app.post("/api/v1/events", status_code=201)
def create_event(ev: EventCreate):
    conn = get_db()
    # 兼容旧表：如果存在 `start_time` 且为 NOT NULL，需要提供默认值以避免约束错误
    cols = [r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()]
    values = (ev.title, ev.date, ev.priority, 1 if ev.completed else 0, ev.note or "")
    if 'start_time' in cols:
        # 填充一个合理的 start_time（使用 date 的午夜时间）以满足旧表的 NOT NULL 约束
        start_time_val = f"{ev.date}T00:00:00"
        cur = conn.execute("INSERT INTO events (title, date, priority, completed, note, start_time) VALUES (?,?,?,?,?,?)",
            (ev.title, ev.date, ev.priority, 1 if ev.completed else 0, ev.note or "", start_time_val))
    else:
        cur = conn.execute("INSERT INTO events (title, date, priority, completed, note) VALUES (?,?,?,?,?)",
            values)
    conn.commit()
    return dict(conn.execute("SELECT * FROM events WHERE id=?", (cur.lastrowid,)).fetchone())

@app.put("/api/v1/events/{eid}")
def update_event(eid: int, ev: EventUpdate):
    conn = get_db()
    row = conn.execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()
    if not row: raise HTTPException(404)
    data = dict(row)
    if ev.title is not None: data["title"] = ev.title
    if ev.date is not None: data["date"] = ev.date
    if ev.priority is not None: data["priority"] = ev.priority
    if ev.completed is not None: data["completed"] = 1 if ev.completed else 0
    if ev.note is not None: data["note"] = ev.note
    conn.execute("UPDATE events SET title=?, date=?, priority=?, completed=?, note=?, updated_at=datetime('now') WHERE id=?",
        (data["title"], data["date"], data["priority"], data["completed"], data["note"], eid))
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
