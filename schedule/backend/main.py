#!/usr/bin/env python3
import sqlite3, os, threading, time, json
from typing import Optional
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError
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
        if 'end_time' not in cols:
            # 保留 end_time 以便在标记完成时记录结束时间
            conn.execute("ALTER TABLE events ADD COLUMN end_time TEXT")
        # reminders 表：用于注册事件的提醒（支持 once/daily/weekly/monthly）
        conn.execute("CREATE TABLE IF NOT EXISTS reminders ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "event_id INTEGER NOT NULL,"
            "kind TEXT NOT NULL,"
            "time TEXT NOT NULL,"
            "date TEXT,"
            "day INTEGER,"
            "enabled INTEGER DEFAULT 1,"
            "webhook TEXT,"
            "last_triggered TEXT,"
            "created_at TEXT DEFAULT (datetime('now'))"
            ")")
    except Exception:
        pass
    # 确保 DDL/迁移已提交
    try:
        conn.commit()
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


class ReminderCreate(BaseModel):
    event_id: int
    kind: str  # once,daily,weekly,monthly
    time: str  # HH:MM
    date: Optional[str] = None  # for once
    day: Optional[int] = None  # for weekly (0-6) or monthly (1-31)
    enabled: Optional[bool] = True
    webhook: Optional[str] = None


class ReminderUpdate(BaseModel):
    kind: Optional[str] = None
    time: Optional[str] = None
    date: Optional[str] = None
    day: Optional[int] = None
    enabled: Optional[bool] = None
    webhook: Optional[str] = None


def notify_payload(reminder, event):
    return {
        'reminder_id': reminder['id'],
        'event_id': reminder['event_id'],
        'event_title': event.get('title'),
        'date': event.get('date'),
        'priority': event.get('priority'),
        'note': event.get('note'),
        'kind': reminder.get('kind'),
        'time': reminder.get('time')
    }


def try_post_webhook(webhook, payload):
    if not webhook:
        return False
    try:
        req = Request(webhook, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        with urlopen(req, timeout=5) as resp:
            return resp.getcode() < 400
    except URLError:
        return False

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
    # 优先把未完成项放前面（completed ASC），已完成项靠后；若无 completed 列则按 priority 排序
    if 'completed' in cols and 'priority' in cols:
        order_clause = "ORDER BY completed ASC, priority DESC, date"
    elif 'priority' in cols:
        order_clause = "ORDER BY priority DESC, date"
    else:
        order_clause = "ORDER BY date"
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


@app.post('/api/v1/reminders', status_code=201)
def create_reminder(r: ReminderCreate):
    conn = get_db()
    cur = conn.execute("INSERT INTO reminders (event_id, kind, time, date, day, enabled, webhook) VALUES (?,?,?,?,?,?,?)",
                       (r.event_id, r.kind, r.time, r.date, r.day, 1 if r.enabled else 0, r.webhook))
    conn.commit()
    return dict(conn.execute("SELECT * FROM reminders WHERE id=?", (cur.lastrowid,)).fetchone())


@app.get('/api/v1/reminders')
def list_reminders(event_id: int = Query(None)):
    conn = get_db()
    if event_id:
        rows = conn.execute('SELECT * FROM reminders WHERE event_id=?', (event_id,)).fetchall()
    else:
        rows = conn.execute('SELECT * FROM reminders').fetchall()
    return [dict(r) for r in rows]


@app.put('/api/v1/reminders/{rid}')
def update_reminder(rid: int, body: ReminderUpdate):
    conn = get_db()
    row = conn.execute('SELECT * FROM reminders WHERE id=?', (rid,)).fetchone()
    if not row: raise HTTPException(404)
    data = dict(row)
    if body.kind is not None: data['kind'] = body.kind
    if body.time is not None: data['time'] = body.time
    if body.date is not None: data['date'] = body.date
    if body.day is not None: data['day'] = body.day
    if body.enabled is not None: data['enabled'] = 1 if body.enabled else 0
    if body.webhook is not None: data['webhook'] = body.webhook
    conn.execute('UPDATE reminders SET kind=?, time=?, date=?, day=?, enabled=?, webhook=? WHERE id=?',
                 (data['kind'], data['time'], data['date'], data['day'], data['enabled'], data['webhook'], rid))
    conn.commit()
    return dict(conn.execute('SELECT * FROM reminders WHERE id=?', (rid,)).fetchone())


@app.delete('/api/v1/reminders/{rid}')
def delete_reminder(rid: int):
    conn = get_db()
    conn.execute('DELETE FROM reminders WHERE id=?', (rid,))
    conn.commit()
    return {'ok': True}


@app.post('/api/v1/reminders/{rid}/trigger')
def trigger_reminder(rid: int):
    conn = get_db()
    r = conn.execute('SELECT * FROM reminders WHERE id=?', (rid,)).fetchone()
    if not r: raise HTTPException(404)
    rem = dict(r)
    ev = conn.execute('SELECT * FROM events WHERE id=?', (rem['event_id'],)).fetchone()
    evd = dict(ev) if ev else {}
    payload = notify_payload(rem, evd)
    ok = try_post_webhook(rem.get('webhook'), payload) if rem.get('webhook') else False
    # update last_triggered and disable if once
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute('UPDATE reminders SET last_triggered=? WHERE id=?', (now, rid))
    if rem.get('kind') == 'once':
        conn.execute('UPDATE reminders SET enabled=0 WHERE id=?', (rid,))
    conn.commit()
    return {'ok': True, 'webhook_called': ok, 'payload': payload}


def parse_hm(s: str):
    try:
        parts = s.split(':')
        return int(parts[0]), int(parts[1])
    except Exception:
        return None


def check_and_fire_once(conn, rem, now_dt):
    # rem['date'] expected YYYY-MM-DD, rem['time'] HH:MM
    if not rem.get('date'): return False
    try:
        scheduled = datetime.strptime(rem['date'] + ' ' + rem['time'], '%Y-%m-%d %H:%M')
    except Exception:
        return False
    last = rem.get('last_triggered')
    if scheduled <= now_dt and (not last):
        # trigger
        conn.execute('UPDATE reminders SET last_triggered=? WHERE id=?', (now_dt.strftime('%Y-%m-%d %H:%M:%S'), rem['id']))
        conn.execute('UPDATE reminders SET enabled=0 WHERE id=?', (rem['id'],))
        ev = conn.execute('SELECT * FROM events WHERE id=?', (rem['event_id'],)).fetchone()
        try_post_webhook(rem.get('webhook'), notify_payload(rem, dict(ev) if ev else {}))
        return True
    return False


def check_and_fire_recurring(conn, rem, now_dt):
    # daily/weekly/monthly recurring checks
    kind = rem.get('kind')
    hour_min = parse_hm(rem.get('time','00:00'))
    if not hour_min: return False
    scheduled_dt = datetime(now_dt.year, now_dt.month, now_dt.day, hour_min[0], hour_min[1])
    last = rem.get('last_triggered')
    if kind == 'daily':
        if scheduled_dt <= now_dt:
            if not last or datetime.strptime(last, '%Y-%m-%d %H:%M:%S') < scheduled_dt:
                conn.execute('UPDATE reminders SET last_triggered=? WHERE id=?', (now_dt.strftime('%Y-%m-%d %H:%M:%S'), rem['id']))
                ev = conn.execute('SELECT * FROM events WHERE id=?', (rem['event_id'],)).fetchone()
                try_post_webhook(rem.get('webhook'), notify_payload(rem, dict(ev) if ev else {}))
                return True
    elif kind == 'weekly':
        # rem['day'] holds weekday 0-6
        if rem.get('day') is None: return False
        if now_dt.weekday() == int(rem.get('day')) and scheduled_dt <= now_dt:
            if not last or datetime.strptime(last, '%Y-%m-%d %H:%M:%S') < scheduled_dt:
                conn.execute('UPDATE reminders SET last_triggered=? WHERE id=?', (now_dt.strftime('%Y-%m-%d %H:%M:%S'), rem['id']))
                ev = conn.execute('SELECT * FROM events WHERE id=?', (rem['event_id'],)).fetchone()
                try_post_webhook(rem.get('webhook'), notify_payload(rem, dict(ev) if ev else {}))
                return True
    elif kind == 'monthly':
        if rem.get('day') is None: return False
        if now_dt.day == int(rem.get('day')) and scheduled_dt <= now_dt:
            if not last or datetime.strptime(last, '%Y-%m-%d %H:%M:%S') < scheduled_dt:
                conn.execute('UPDATE reminders SET last_triggered=? WHERE id=?', (now_dt.strftime('%Y-%m-%d %H:%M:%S'), rem['id']))
                ev = conn.execute('SELECT * FROM events WHERE id=?', (rem['event_id'],)).fetchone()
                try_post_webhook(rem.get('webhook'), notify_payload(rem, dict(ev) if ev else {}))
                return True
    return False


def reminder_worker():
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            now_dt = datetime.utcnow()
            rows = conn.execute('SELECT * FROM reminders WHERE enabled=1').fetchall()
            for r in rows:
                rem = dict(r)
                if rem.get('kind') == 'once':
                    check_and_fire_once(conn, rem, now_dt)
                else:
                    check_and_fire_recurring(conn, rem, now_dt)
            conn.commit()
            conn.close()
        except Exception:
            pass
        time.sleep(30)


def start_reminder_thread():
    t = threading.Thread(target=reminder_worker, daemon=True)
    t.start()

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
    cols = [r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()]
    if ev.completed is not None:
        new_completed = 1 if ev.completed else 0
        # 如果从未完成变为已完成，记录 end_time；如果从已完成变为未完成，清除 end_time（若列存在）
        if 'end_time' in cols:
            if new_completed == 1 and (not data.get('completed')):
                data['end_time'] = conn.execute("SELECT datetime('now')").fetchone()[0]
            elif new_completed == 0:
                data['end_time'] = None
        data["completed"] = new_completed
    if ev.note is not None: data["note"] = ev.note
    # 构建更新语句，包含 end_time 如果存在
    if 'end_time' in cols:
        conn.execute("UPDATE events SET title=?, date=?, priority=?, completed=?, note=?, end_time=?, updated_at=datetime('now') WHERE id=?",
            (data["title"], data["date"], data["priority"], data["completed"], data["note"], data.get('end_time'), eid))
    else:
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
    # 启动提醒后台线程
    try:
        start_reminder_thread()
    except Exception:
        pass
    uvicorn.run(app, host="0.0.0.0", port=port)
