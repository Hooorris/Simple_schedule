#!/usr/bin/env python3
import sqlite3, os, threading, time, json, subprocess
from typing import Optional
from datetime import datetime, date as date_cls, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DB_PATH = os.path.join(os.path.dirname(__file__), "schedule.db")
CC_CONNECT_PROJECT = os.environ.get("CC_CONNECT_PROJECT", "my-project")
AUTO_POSTPONE_TIME = os.environ.get("AUTO_POSTPONE_TIME", "23:59")
AUTO_POSTPONE_STATE_KEY = "auto_postpone_unfinished_last_date"

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
            ")"
        )
        conn.execute("CREATE TABLE IF NOT EXISTS reminder_rules ("
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
        conn.execute("CREATE TABLE IF NOT EXISTS app_state ("
            "key TEXT PRIMARY KEY,"
            "value TEXT NOT NULL,"
            "updated_at TEXT DEFAULT (datetime('now'))"
            ")"
        )
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


class PostponeUnfinishedRequest(BaseModel):
    date: Optional[str] = None


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


class ReminderRuleCreate(BaseModel):
    name: str
    kind: str
    time: str
    date: Optional[str] = None
    day: Optional[int] = None
    enabled: Optional[bool] = True


class ReminderRuleUpdate(BaseModel):
    name: Optional[str] = None
    kind: Optional[str] = None
    time: Optional[str] = None
    date: Optional[str] = None
    day: Optional[int] = None
    enabled: Optional[bool] = None


def validate_rule(kind: str, time_text: str, rule_date: Optional[str] = None, day: Optional[int] = None):
    if kind not in {"once", "daily", "weekly", "monthly"}:
        raise HTTPException(400, "kind must be one of once,daily,weekly,monthly")
    if parse_hm(time_text) is None:
        raise HTTPException(400, "time must use HH:MM")
    if kind == "once":
        if not rule_date:
            raise HTTPException(400, "date is required for once rules")
        try:
            datetime.strptime(rule_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(400, "date must use YYYY-MM-DD")
    if kind == "weekly" and (day is None or not 0 <= int(day) <= 6):
        raise HTTPException(400, "day must be 0-6 for weekly rules")
    if kind == "monthly" and (day is None or not 1 <= int(day) <= 31):
        raise HTTPException(400, "day must be 1-31 for monthly rules")


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


def get_pending_tasks_for_date(conn, target_date: str):
    rows = conn.execute(
        "SELECT id, title, date, priority, completed, note "
        "FROM events "
        "WHERE date<=? AND (completed IS NULL OR completed=0) "
        "ORDER BY priority DESC, id ASC",
        (target_date,),
    ).fetchall()
    tasks = []
    for row in rows:
        task = dict(row)
        task["display_date"] = target_date
        tasks.append(task)
    return tasks


def row_with_display_date(row, target_date: str):
    item = dict(row)
    if not item.get("completed") and item.get("date") and item["date"] <= target_date:
        item["display_date"] = target_date
    else:
        item["display_date"] = item.get("date")
    return item


def list_events_for_display(conn, start: str = "", end: str = ""):
    today = date_cls.today().strftime("%Y-%m-%d")
    display_date = today
    if start and end:
        rows = conn.execute(
            "SELECT * FROM events "
            "WHERE (completed=1 AND date BETWEEN ? AND ?) "
            "   OR ((completed IS NULL OR completed=0) AND date<=?) "
            "ORDER BY completed ASC, priority DESC, date, id",
            (start, end, display_date),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM events ORDER BY completed ASC, priority DESC, date, id"
        ).fetchall()
    return [row_with_display_date(row, display_date) for row in rows]


def validate_date_text(value: str):
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "date must use YYYY-MM-DD")


def postpone_unfinished_tasks(conn, source_date: str):
    validate_date_text(source_date)
    target_date = (
        datetime.strptime(source_date, "%Y-%m-%d") + timedelta(days=1)
    ).strftime("%Y-%m-%d")
    tasks = get_pending_tasks_for_date(conn, source_date)
    if not tasks:
        return {
            "ok": True,
            "from_date": source_date,
            "to_date": target_date,
            "moved": 0,
            "tasks": [],
        }

    ids = [task["id"] for task in tasks]
    placeholders = ",".join("?" for _ in ids)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()]
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
    return {
        "ok": True,
        "from_date": source_date,
        "to_date": target_date,
        "moved": len(tasks),
        "tasks": tasks,
    }


def format_pending_message(tasks, target_date: str):
    today = date_cls.today().strftime("%Y-%m-%d")
    title = "今日未完成任务" if target_date == today else f"{target_date} 未完成任务"
    if not tasks:
        return "今天没有未完成任务。" if target_date == today else f"{target_date} 没有未完成任务。"
    lines = [f"{title} {len(tasks)} 项", ""]
    for idx, task in enumerate(tasks, 1):
        lines.append(f"{idx}. [P{task.get('priority') or 0}] {task.get('title')}")
        note = (task.get("note") or "").strip()
        if note:
            lines.append(f"   {note}")
        if idx != len(tasks):
            lines.append("")
    return "\n".join(lines)


def send_cc_connect_message(message: str):
    try:
        result = subprocess.run(
            ["cc-connect", "send", "-p", CC_CONNECT_PROJECT, "-m", message],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except Exception as exc:
        return {"ok": False, "stdout": "", "stderr": str(exc)}

app = FastAPI(title="Schedule", version="1.0.0", docs_url="/api/docs")

@app.get("/api/v1/db-events")
def db_events_direct(start: str = "", end: str = ""):
    conn = get_db()
    return list_events_for_display(conn, start, end)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/v1/events")
def list_events(start: str = Query(""), end: str = Query("")):
    conn = get_db()
    return list_events_for_display(conn, start, end)

@app.get("/api/v1/tasks/pending")
def list_pending_tasks(date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$")):
    conn = get_db()
    return get_pending_tasks_for_date(conn, date)


@app.post("/api/v1/tasks/postpone-unfinished")
def postpone_unfinished(body: Optional[PostponeUnfinishedRequest] = None):
    target_date = (body.date if body else None) or date_cls.today().strftime("%Y-%m-%d")
    conn = get_db()
    result = postpone_unfinished_tasks(conn, target_date)
    conn.commit()
    return result

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


@app.post("/api/v1/reminder-rules", status_code=201)
def create_reminder_rule(rule: ReminderRuleCreate):
    validate_rule(rule.kind, rule.time, rule.date, rule.day)
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO reminder_rules (name, kind, time, date, day, enabled) VALUES (?,?,?,?,?,?)",
        (rule.name, rule.kind, rule.time, rule.date, rule.day, 1 if rule.enabled else 0),
    )
    conn.commit()
    return dict(conn.execute("SELECT * FROM reminder_rules WHERE id=?", (cur.lastrowid,)).fetchone())


@app.get("/api/v1/reminder-rules")
def list_reminder_rules():
    rows = get_db().execute("SELECT * FROM reminder_rules ORDER BY enabled DESC, time, id").fetchall()
    return [dict(r) for r in rows]


@app.put("/api/v1/reminder-rules/{rid}")
def update_reminder_rule(rid: int, body: ReminderRuleUpdate):
    conn = get_db()
    row = conn.execute("SELECT * FROM reminder_rules WHERE id=?", (rid,)).fetchone()
    if not row:
        raise HTTPException(404)
    data = dict(row)
    if body.name is not None: data["name"] = body.name
    if body.kind is not None: data["kind"] = body.kind
    if body.time is not None: data["time"] = body.time
    if body.date is not None: data["date"] = body.date
    if body.day is not None: data["day"] = body.day
    if body.enabled is not None: data["enabled"] = 1 if body.enabled else 0
    validate_rule(data["kind"], data["time"], data.get("date"), data.get("day"))
    conn.execute(
        "UPDATE reminder_rules SET name=?, kind=?, time=?, date=?, day=?, enabled=? WHERE id=?",
        (data["name"], data["kind"], data["time"], data.get("date"), data.get("day"), data["enabled"], rid),
    )
    conn.commit()
    return dict(conn.execute("SELECT * FROM reminder_rules WHERE id=?", (rid,)).fetchone())


@app.delete("/api/v1/reminder-rules/{rid}")
def delete_reminder_rule(rid: int):
    conn = get_db()
    conn.execute("DELETE FROM reminder_rules WHERE id=?", (rid,))
    conn.commit()
    return {"ok": True}


@app.post("/api/v1/reminder-rules/{rid}/trigger")
def trigger_reminder_rule(rid: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM reminder_rules WHERE id=?", (rid,)).fetchone()
    if not row:
        raise HTTPException(404)
    rule = dict(row)
    target_date = date_cls.today().strftime("%Y-%m-%d")
    tasks = get_pending_tasks_for_date(conn, target_date)
    message = format_pending_message(tasks, target_date)
    sent = send_cc_connect_message(message)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE reminder_rules SET last_triggered=? WHERE id=?", (now, rid))
    if rule.get("kind") == "once":
        conn.execute("UPDATE reminder_rules SET enabled=0 WHERE id=?", (rid,))
    conn.commit()
    return {"ok": True, "sent": sent, "message": message}


def parse_hm(s: str):
    try:
        parts = s.split(':')
        hour, minute = int(parts[0]), int(parts[1])
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
        return None
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


def rule_should_fire(rule, now_dt):
    hour_min = parse_hm(rule.get("time", "00:00"))
    if not hour_min:
        return False
    kind = rule.get("kind")
    scheduled_dt = datetime(now_dt.year, now_dt.month, now_dt.day, hour_min[0], hour_min[1])
    last = rule.get("last_triggered")
    if last and datetime.strptime(last, "%Y-%m-%d %H:%M:%S") >= scheduled_dt:
        return False
    if scheduled_dt > now_dt:
        return False
    if kind == "daily":
        return True
    if kind == "once":
        if not rule.get("date"):
            return False
        try:
            return datetime.strptime(rule["date"] + " " + rule["time"], "%Y-%m-%d %H:%M") <= now_dt and not last
        except ValueError:
            return False
    if kind == "weekly":
        return rule.get("day") is not None and now_dt.weekday() == int(rule["day"])
    if kind == "monthly":
        return rule.get("day") is not None and now_dt.day == int(rule["day"])
    return False


def fire_reminder_rule(conn, rule, now_dt):
    target_date = date_cls.today().strftime("%Y-%m-%d")
    tasks = get_pending_tasks_for_date(conn, target_date)
    message = format_pending_message(tasks, target_date)
    sent = send_cc_connect_message(message)
    conn.execute("UPDATE reminder_rules SET last_triggered=? WHERE id=?",
        (now_dt.strftime("%Y-%m-%d %H:%M:%S"), rule["id"]))
    if rule.get("kind") == "once":
        conn.execute("UPDATE reminder_rules SET enabled=0 WHERE id=?", (rule["id"],))
    return sent


def auto_postpone_should_fire(conn, now_dt):
    hour_min = parse_hm(AUTO_POSTPONE_TIME)
    if not hour_min:
        return False
    scheduled_dt = datetime(now_dt.year, now_dt.month, now_dt.day, hour_min[0], hour_min[1])
    if scheduled_dt > now_dt:
        return False
    today = now_dt.strftime("%Y-%m-%d")
    row = conn.execute(
        "SELECT value FROM app_state WHERE key=?",
        (AUTO_POSTPONE_STATE_KEY,),
    ).fetchone()
    return not row or row["value"] != today


def fire_auto_postpone(conn, now_dt):
    today = now_dt.strftime("%Y-%m-%d")
    result = postpone_unfinished_tasks(conn, today)
    conn.execute(
        "INSERT INTO app_state (key, value, updated_at) VALUES (?,?,datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')",
        (AUTO_POSTPONE_STATE_KEY, today),
    )
    return result


def reminder_worker():
    while True:
        try:
            conn = get_db()
            now_dt = datetime.now()
            rows = conn.execute('SELECT * FROM reminders WHERE enabled=1').fetchall()
            for r in rows:
                rem = dict(r)
                if rem.get('kind') == 'once':
                    check_and_fire_once(conn, rem, now_dt)
                else:
                    check_and_fire_recurring(conn, rem, now_dt)
            rule_rows = conn.execute("SELECT * FROM reminder_rules WHERE enabled=1").fetchall()
            for r in rule_rows:
                rule = dict(r)
                if rule_should_fire(rule, now_dt):
                    fire_reminder_rule(conn, rule, now_dt)
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
                completed_date = date_cls.today().strftime("%Y-%m-%d")
                data['date'] = completed_date
                if 'start_time' in cols:
                    data['start_time'] = f"{completed_date}T00:00:00"
                data['end_time'] = conn.execute("SELECT datetime('now')").fetchone()[0]
            elif new_completed == 0:
                data['end_time'] = None
        data["completed"] = new_completed
    if ev.note is not None: data["note"] = ev.note
    # 构建更新语句，包含 end_time 如果存在
    if 'end_time' in cols and 'start_time' in cols:
        conn.execute("UPDATE events SET title=?, date=?, priority=?, completed=?, note=?, start_time=?, end_time=?, updated_at=datetime('now') WHERE id=?",
            (data["title"], data["date"], data["priority"], data["completed"], data["note"], data.get('start_time'), data.get('end_time'), eid))
    elif 'end_time' in cols:
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
