# Schedule — 极简日程表

这是一个极简的日程表示例项目，包含后端（FastAPI + SQLite）与前端（React + Vite）。

目录结构（相关）:

- `backend/` — FastAPI 后端，入口 `main.py`，数据库文件 `schedule.db`。
- `frontend/` — React 前端，使用 Vite 开发服务器。
- `start.sh` — 简单脚本同时启动后端与前端（开发模式）。

主要特性：

- 基于 SQLite 的轻量持久化（events 表）
- 提供 CRUD REST API：`/api/v1/events`
- 前端按月拉取并显示事件，支持添加、编辑、删除、多选删除
- 提供 cc-connect Cron 可调用的未完成任务 API，用于手机提醒
- 每天 23:59 自动将当天未完成任务延期到第二天

快速开始：

1. 安装后端依赖（建议在虚拟环境中运行）：

```bash
cd schedule/backend
pip install -r requirements.txt
```

2. 在项目根运行启动脚本（同时启动后端和前端）:

```bash
chmod +x start.sh
./start.sh
```

3. 打开浏览器：

- 前端: `http://localhost:5173/`
- 后端（API 文档）: `http://localhost:3000/api/docs`

常见 API:

- `GET /api/v1/events?start=YYYY-MM-DD&end=YYYY-MM-DD` — 列出指定范围内事件
- `GET /api/v1/tasks/pending?date=YYYY-MM-DD` — 列出指定日期未完成任务，按优先级降序
- `POST /api/v1/tasks/postpone-unfinished` — 将指定日期未完成任务延期到第二天，body 可选：`{ "date": "YYYY-MM-DD" }`
- `GET /api/v1/events/{id}` — 获取事件
- `POST /api/v1/events` — 创建事件，JSON body 包含 `title`, `start_time`, `end_time?(optional)`, `note?(optional)`
- `PUT /api/v1/events/{id}` — 更新事件（部分字段可选）
- `DELETE /api/v1/events/{id}` — 删除事件
- `DELETE /api/v1/events` — 批量删除，JSON body: `{ "ids": [1,2,3] }`

说明与注意事项:

- 数据库文件 `backend/schedule.db` 会在第一次启动时自动创建。
- 时间字符串使用 ISO 格式（含时区偏移，如 `2026-06-13T10:00:00+08:00`）。
- 后端在插入/更新时会校验 `start_time` 与 `end_time` 是否同一天（若提供 `end_time`）。
 - 事件模型已调整：不再记录开始/结束时间；改为使用 `date`（YYYY-MM-DD）、`priority`（整数，越大优先级越高）和 `completed`（布尔）。
 - `POST /api/v1/events` 的 body 示例：
	 `{ "title": "任务", "date": "2026-06-13", "priority": 5, "completed": false, "note": "可选" }`
 - 手机提醒推荐使用 cc-connect Cron 调用 `/api/v1/tasks/pending`，配置说明见 `docs/cc-connect-reminder.md`。
 - 通过微信/cc-connect 新增提醒时，可使用本地脚本；带具体提醒时间时传入 `--time HH:MM`，脚本会同步创建一次性提醒：
	 `python3 scripts/add_reminder.py --title "写周报" --date 2026-06-15 --time 17:30 --priority 5 --note "下班前完成"`
 - 添加定时汇总提醒规则时，可使用：
	 `python3 scripts/add_reminder_rule.py --name "每日待办提醒" --kind daily --time 09:00`
 - 手动延期某天未完成任务到第二天时，可使用：
	 `python3 scripts/postpone_unfinished.py --date 2026-06-15`
 - 后端启动后会在每天本地时间 23:59 自动延期当天未完成任务；如需调整时间，可设置环境变量 `AUTO_POSTPONE_TIME=HH:MM`。

如需进一步改进：

- 增加用户认证和多用户支持
- 更健壮的时间/时区处理（使用 `pytz` / `zoneinfo`）
- 将 SQLite 替换为 PostgreSQL 等生产级数据库
