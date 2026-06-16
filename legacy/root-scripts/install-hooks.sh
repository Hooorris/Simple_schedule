#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOKS_DIR="$ROOT/.git/hooks"
POST_COMMIT="$HOOKS_DIR/post-commit"

echo "Installing post-commit hook to sync schedule/README.md from finsh.md..."

mkdir -p "$HOOKS_DIR"
cat > "$POST_COMMIT" <<'HOOK'
#!/usr/bin/env bash
set -e
# avoid recursive hook-trigger commits
MSG=$(git log -1 --pretty=%B)
if echo "$MSG" | grep -q "sync schedule/README.md from finsh.md"; then
  exit 0
fi

python3 scripts/sync_readme.py
if git diff --quiet -- schedule/README.md; then
  exit 0
fi

git add schedule/README.md
git commit -m "sync schedule/README.md from finsh.md" || true
HOOK

chmod +x "$POST_COMMIT"
echo "post-commit hook installed at $POST_COMMIT"
