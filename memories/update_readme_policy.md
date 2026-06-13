全局记忆：自动同步 README

- 目的：当项目完成或更新功能时，保持 `schedule/README.md` 中的“完成记录/变更摘要”与仓库根目录下的 `finsh.md` 同步，便于快速查看项目历史。
- 触发方式：手动运行同步脚本或在本地安装的 git hook（post-commit）自动触发。
- 同步规则：脚本会把 `finsh.md` 的完整内容替换或写入 `schedule/README.md` 中标记的区段（由 <!-- FINSH_START --> 和 <!-- FINSH_END --> 包围）。
- 文件位置：
  - 同步脚本： `scripts/sync_readme.py`
  - 安装 hook： `scripts/install-hooks.sh`
- 使用建议：
  1. 每次完成一个功能后，按流程更新 `finsh.md`（已在项目中使用）。
  2. 运行 `scripts/sync_readme.py` 手动同步，或运行 `scripts/install-hooks.sh` 在本地启用 `post-commit` 钩子实现自动同步。
  3. 钩子在检测到 `schedule/README.md` 内容变化时，会自动暂存并提交带信息的变更（提交信息包含 `sync schedule/README.md from finsh.md` 用于避免循环提交）。

记忆创建时间：2026-06-13
