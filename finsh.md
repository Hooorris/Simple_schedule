# 完成记录 (finsh)

## 任务 1：日历显示每日前三条缩略
- 版本：d3b39f5
- 修改文件：
  - schedule/frontend/src/components/Calendar.jsx
  - schedule/frontend/src/App.jsx
- 实现内容：在日历单元格中显示按 `priority` 排序的前 3 条事件缩略，单行显示并超出省略。
- 自查：在本地创建了测试事件（V-A/V-B/V-C）并验证：
  - 日历已渲染事件缩略（显示标题的单行省略）
  - 事件按优先级排序，显示前三条
- 状态：已完成并推送到 `origin/main`（commit d3b39f5）

## 后续任务
- 任务 2：增加提醒功能（每天/每周/每月/单次） — 未开始

## 修订：日历当天高亮颜色
- 版本：b7aeb64
- 修改文件：
  - schedule/frontend/src/components/Calendar.jsx
- 实现内容：将当天单元格背景从蓝色改为绿色以提高可见性
- 自查：在浏览器中验证当天单元格为绿色显示，且事件缩略正常渲染
- 状态：已完成并推送到 `origin/main`（commit b7aeb64）

### 修正：确保当天背景为绿色（文本与白点颜色正确）
- 版本：94609d3
- 修改文件：
  - schedule/frontend/src/components/Calendar.jsx
- 实现内容：明确分离背景与文字颜色，确保当天单元格背景为绿色，日期文字与忙碌指示点为白色
- 自查：在浏览器中验证当天单元格背景为绿色，日期为白色，白点为白色
- 状态：已完成并推送到 `origin/main`（commit 94609d3）

## 任务 3：日历显示每日待办/已完成计数
- 版本：7a13f1e
- 修改文件：
  - schedule/frontend/src/components/Calendar.jsx
- 实现内容：将日历单元格内的前三条标题缩略替换为当天的“待办：X / 已完成：Y”计数，便于快速查看当天任务状态
- 自查：通过本地创建测试事件并在浏览器验证：日期格显示待办与已完成计数，且与后端 `/api/v1/events` 返回结果一致
- 状态：已完成并推送到 `origin/main`（commit 7a13f1e）

## 任务 2：提醒功能（初版）
- 版本：90d7cf8
- 修改文件：
  - schedule/backend/main.py
  - schedule/frontend/src/components/EventModal.jsx
  - schedule/frontend/src/App.jsx
- 实现内容：
  - 在后端新增 `reminders` 表并提供 API：`POST/GET/PUT/DELETE /api/v1/reminders` 以及 `POST /api/v1/reminders/{id}/trigger`。
  - 后端启动时运行后台线程，按规则（once/daily/weekly/monthly）轮询并触发提醒，支持可选 `webhook` 推送（POST JSON payload）。
  - 前端在 `EventModal` 中新增提醒设置 UI（启用、类型、时间、单次日期或周/月选项、可选 webhook），保存事件时同步创建 reminder。
- 自查：已在本地创建含提醒的事件，并观察到 reminders 表记录；手动触发 `/api/v1/reminders/{id}/trigger` 返回 payload 并可将 `enabled` 置为 false（单次提醒）。
- 状态：已完成并推送到 `origin/main`（commit 90d7cf8）


