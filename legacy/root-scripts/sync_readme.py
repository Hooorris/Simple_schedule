#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINSH = ROOT / 'finsh.md'
TARGET = ROOT / 'schedule' / 'README.md'

MARK_START = '<!-- FINSH_START -->'
MARK_END = '<!-- FINSH_END -->'

def read(path):
    if not path.exists():
        return ''
    return path.read_text(encoding='utf-8')

def write(path, text):
    path.write_text(text, encoding='utf-8')

def main():
    finsh = read(FINSH).strip()
    if not finsh:
        print('finsh.md is empty or not found; nothing to sync')
        return 0

    target = read(TARGET)
    if not target:
        # create a basic README with markers
        new = f"# Schedule README\n\n{MARK_START}\n{finsh}\n{MARK_END}\n"
        write(TARGET, new)
        print('created schedule/README.md with finsh content')
        return 1

    if MARK_START in target and MARK_END in target:
        pre, rest = target.split(MARK_START, 1)
        _, post = rest.split(MARK_END, 1)
        new_target = pre + MARK_START + "\n" + finsh + "\n" + MARK_END + post
        if new_target != target:
            write(TARGET, new_target)
            print('updated schedule/README.md section between markers')
            return 1
        else:
            print('no changes to schedule/README.md')
            return 0
    else:
        # append section with markers
        new_target = target + "\n\n" + MARK_START + "\n" + finsh + "\n" + MARK_END + "\n"
        write(TARGET, new_target)
        print('appended finsh section to schedule/README.md')
        return 1

if __name__ == '__main__':
    rc = main()
    sys.exit(rc)
