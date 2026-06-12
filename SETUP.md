# iPhone → Codex 工作流（多线程版）

## 核心原理

```
iCloud Drive/Codex/
  ├── threads.json         ← 文件夹 → 线程 ID 映射
  ├── default/             ← 默认线程（当前对话）
  │   ├── commands/
  │   └── results/
  ├── dev/                 ← 开发线程
  │   ├── commands/
  │   └── results/
  ├── research/            ← 调研线程
  │   ├── commands/
  │   └── results/
  └── personal/            ← 私人事务线程
      ├── commands/
      └── results/
```

每个文件夹对应一个独立的 Codex 线程，指令和结果各归各，互不干扰。

---

## threads.json 配置

```json
{
  "default":  "019eb17d-...",   // 已有线程
  "dev":      "",                // 空 = 未激活
  "research": ""
}
```

- 文件夹存在 + thread_id 非空 = 收到指令会自动处理
- 线程 ID 为空 = watcher 会跳过该文件夹

---

## 如何增加新文件夹

告诉 Codex 你想加什么，例如 "帮我建一个 blog 线程"。

Codex 会：
1. 调用 `create_thread` 创建新线程
2. 记下返回的 thread ID
3. 更新 `threads.json`
4. 创建对应的文件夹结构

之后 iPhone 往 `blog/commands/` 放指令，就自动走 blog 线程。

---

## iPhone 快捷指令设置

打开「快捷指令」App，新建：

**动作 1：要求输入**
- 提示：`输入你的指令`
- 输入类型：文本

**动作 2：文本**
- 内容：
```
{"command": "输入"}
```

**动作 3：存储文件**
- 位置：iCloud Drive > Codex > default > commands
- 文件名：`pending_「当前日期」.json`
  - 格式：`yyyyMMdd_HHmmss`
- 覆盖：如果文件已存在，询问

**动作 4：显示通知**
- 标题：已发送
- 正文：`输入`

**动作 5：打开文件**
- 位置：iCloud Drive > Codex > default > results

如果要用其他文件夹，把"存储文件"的位置改到对应子文件夹就行。

---

## 状态查看

```bash
# watcher 日志
tail -f /tmp/codex_icloud_watcher.log

# 重启 watcher
launchctl kickstart gui/$(id -u)/com.codex.icloud-watcher
```
