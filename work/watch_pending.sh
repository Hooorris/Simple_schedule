#!/bin/bash
# iPhone 指令监控脚本 - 被 crontab 定期调用
PENDING_DIR="/Users/horris/Documents/Codex/2026-06-10/iphone/work/webhook_logs"
LOG_FILE="$PENDING_DIR/watcher.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log "Watcher running"

# 检查是否有 pending 文件
for f in "$PENDING_DIR"/pending_*.json; do
    [ -f "$f" ] || continue
    
    cmd_id=$(basename "$f" | sed 's/pending_//;s/\.json//')
    command=$(python3 -c "import json; print(json.load(open('$f'))['command'])")
    
    log "Processing [$cmd_id]: $command"
    
    # 用 codex exec 创建一个新会话执行指令
    output_file="$PENDING_DIR/output_${cmd_id}.txt"
    /opt/homebrew/bin/codex exec \
        -C /Users/horris/Documents/Codex/2026-06-10/iphone \
        --sandbox workspace-write \
        --dangerously-bypass-approvals-and-sandbox \
        -o "$output_file" \
        "$command" >> "$LOG_FILE" 2>&1
    
    # 移到 done
    mv "$f" "$PENDING_DIR/done_${cmd_id}.json"
    log "Completed [$cmd_id]: exit=$?"
done

log "Watcher finished"
