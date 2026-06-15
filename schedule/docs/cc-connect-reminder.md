# cc-connect Cron 日程提醒

本项目推荐使用 cc-connect Cron 负责定时触发和手机消息发送，Schedule 后端只提供当天未完成任务 API。

## 1. 启动 Schedule

在项目根目录启动后端和前端：

```bash
./start.sh
```

默认后端地址：

```text
http://localhost:3000
```

## 2. 验证待提醒任务 API

查询指定日期的未完成任务：

```bash
curl "http://localhost:3000/api/v1/tasks/pending?date=2026-06-13"
```

接口只返回 `completed = 0` 的任务，并按 `priority` 从高到低排序。

返回字段：

```json
[
  {
    "id": 2,
    "title": "测试验证2",
    "date": "2026-06-13",
    "priority": 7,
    "completed": 0,
    "note": "自动化验证2"
  }
]
```

## 3. 配置 cc-connect Cron

在 cc-connect 中添加每日提醒任务，例如每天 09:00：

```bash
cc-connect cron add --cron "0 9 * * *" --prompt "每天提醒我今天未完成的任务。请请求 http://localhost:3000/api/v1/tasks/pending?date=今天日期，按 priority 从高到低整理。如果没有任务，回复“今天没有未完成任务”。如果有任务，用简洁列表发给我。"
```

推荐消息格式：

```text
今日未完成任务 2 项

1. [P7] 测试验证2
   自动化验证2

2. [P0] 看床
   去看床
```

没有未完成任务时发送：

```text
今天没有未完成任务。
```

## 4. 注意事项

- Schedule 后端和 cc-connect 都需要保持运行。
- 手机接收通道由 cc-connect 当前绑定的平台决定，例如微信、飞书、Telegram 或企业微信。
- 第一版只做“当天未完成任务汇总提醒”，不做每条任务独立提醒。
- 如果 cc-connect 对“今天日期”的解析不稳定，可以改成由外部脚本生成 `YYYY-MM-DD` 后再请求 API。
- Schedule 后端启动后，会在每天本地时间 23:59 自动把当天未完成任务延期到第二天。

## 5. 通过微信新增提醒

cc-connect 已连接到本项目后，可以在微信里用自然语言要求新增提醒。Codex 应将用户意图解析成日期、标题、优先级和备注，然后调用本地脚本写入数据库：

```bash
python3 scripts/add_reminder.py --title "写周报" --date 2026-06-15 --priority 5 --note "下班前完成"
```

默认规则：

- 未说明日期时，默认使用当前日期。
- 未说明优先级时，默认 `priority=0`。
- 未说明备注时，默认 `note=""`。
- 日期含糊且会影响结果时，先向用户追问一次。

## 6. 添加定时汇总规则

如果希望系统在固定时间主动把当天未完成任务发到微信，可以新增 `reminder_rules` 规则。规则到点后会查询当天未完成任务，按优先级降序整理，并执行：

```bash
cc-connect send -p my-project -m "<提醒文本>"
```

新增每日 09:00 汇总提醒：

```bash
python3 scripts/add_reminder_rule.py --name "每日待办提醒" --kind daily --time 09:00
```

新增单次提醒：

```bash
python3 scripts/add_reminder_rule.py --name "今天晚间提醒" --kind once --date 2026-06-14 --time 21:30
```

规则说明：

- `daily`：每天指定时间提醒。
- `once`：指定日期和时间提醒，触发后自动禁用。
- `weekly`：每周指定星期提醒，`--day` 为 `0-6`，其中 `0` 表示周一。
- `monthly`：每月指定日期提醒，`--day` 为 `1-31`。
- 如果微信里只说“提醒我未完成任务”但没有时间，必须先追问。

## 7. 延期未完成任务

当用户在微信里说“延期今天未完成任务”“把今天未完成工作延期到明天”或“顺延未完成任务”时，调用本地脚本：

```bash
python3 scripts/postpone_unfinished.py --date 2026-06-15
```

默认规则：

- 未说明日期时，默认使用当前日期。
- 当前项目没有工作分类字段，“工作”按全部未完成任务理解。
- 脚本会把指定日期 `completed=0` 的任务移动到第二天，已完成任务不移动。
