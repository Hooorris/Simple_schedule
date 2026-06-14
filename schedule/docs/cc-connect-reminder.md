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
