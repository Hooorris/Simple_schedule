#!/usr/bin/env python3
import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path("/Users/horris/Documents/LittleAssistant/.venv/bin/python")
LABEL = "com.horris.schedule.backend"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
LOG_DIR = Path.home() / "Library" / "Logs" / "schedule"


def plist_content() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{PYTHON}</string>
    <string>{PROJECT_ROOT / "backend" / "main.py"}</string>
    <string>3000</string>
  </array>
  <key>WorkingDirectory</key>
  <string>{PROJECT_ROOT}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/Applications/Codex.app/Contents/Resources:/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>CC_CONNECT_PROJECT</key>
    <string>my-project</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <dict>
    <key>SuccessfulExit</key>
    <false/>
  </dict>
  <key>StandardOutPath</key>
  <string>{LOG_DIR / "backend.out.log"}</string>
  <key>StandardErrorPath</key>
  <string>{LOG_DIR / "backend.err.log"}</string>
</dict>
</plist>
"""


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def print_result(result: subprocess.CompletedProcess[str]) -> None:
    output = (result.stdout + result.stderr).strip()
    if output:
        print(output)


def write_plist() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.write_text(plist_content(), encoding="utf-8")
    print(f"wrote {PLIST_PATH}")


def bootout() -> None:
    result = run(["launchctl", "bootout", f"gui/{subprocess.getoutput('id -u')}", str(PLIST_PATH)])
    if result.returncode not in (0, 3):
        print_result(result)


def bootstrap() -> int:
    result = run(["launchctl", "bootstrap", f"gui/{subprocess.getoutput('id -u')}", str(PLIST_PATH)])
    print_result(result)
    return result.returncode


def kickstart() -> int:
    result = run(["launchctl", "kickstart", "-k", f"gui/{subprocess.getoutput('id -u')}/{LABEL}"])
    print_result(result)
    return result.returncode


def status() -> int:
    result = run(["launchctl", "print", f"gui/{subprocess.getoutput('id -u')}/{LABEL}"])
    if result.returncode == 0:
        print(f"{LABEL}: loaded")
    else:
        print(f"{LABEL}: not loaded")
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage the Schedule backend LaunchAgent.")
    parser.add_argument("command", choices=("write", "install", "uninstall", "restart", "status"))
    args = parser.parse_args()

    if args.command == "write":
        write_plist()
        return 0
    if args.command == "install":
        write_plist()
        bootout()
        code = bootstrap()
        if code == 0:
            kickstart()
        return code
    if args.command == "uninstall":
        bootout()
        return 0
    if args.command == "restart":
        bootout()
        code = bootstrap()
        if code == 0:
            kickstart()
        return code
    return status()


if __name__ == "__main__":
    raise SystemExit(main())
