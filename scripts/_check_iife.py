# -*- coding: utf-8 -*-
"""Check IIFE structure."""
import re

with open('fc26_fsu_mod/【FSU】EAFC FUT WEB 增强器-26.09.yyh.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find IIFE
match = re.search(r'\(function\s*\(\)\s*\{', content)
if match:
    start = match.start()
    body = content[start:]

    depth = 0
    in_str = False
    str_char = None
    in_line_comment = False
    in_block_comment = False
    in_template = False
    iife_end = -1

    i = 0
    while i < len(body):
        ch = body[i]

        if in_line_comment:
            if ch == '\n':
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == '*' and i+1 < len(body) and body[i+1] == '/':
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue
        if in_str:
            if ch == '\\' and i+1 < len(body):
                i += 2
                continue
            if ch == str_char:
                in_str = False
            i += 1
            continue
        if in_template:
            if ch == '\\' and i+1 < len(body):
                i += 2
                continue
            if ch == '`':
                in_template = False
            elif ch == '$' and i+1 < len(body) and body[i+1] == '{':
                # Script expression inside template
                depth += 1
                i += 2
                continue
            i += 1
            continue

        if ch == '/' and i+1 < len(body):
            if body[i+1] == '/':
                in_line_comment = True
                i += 2
                continue
            if body[i+1] == '*':
                in_block_comment = True
                i += 2
                continue

        if ch == '"' or ch == "'":
            in_str = True
            str_char = ch
            i += 1
            continue

        if ch == '`':
            in_template = True
            i += 1
            continue

        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1

        if depth == 0 and ch == ')':
            # Check if this is the closing of the IIFE
            remaining = body[i:]
            if remaining.startswith(')();'):
                iife_end = i + 4
                break

        i += 1

    if iife_end > 0:
        print(f'IIFE body found, depth={depth}')
        print(f'IIFE end at file offset: {start + iife_end}')
        # Show a line number approximation
        lines_before = content[:start].count('\n') + 1
        lines_after = content[start:iife_end+start].count('\n') + lines_before - 1
        print(f'IIFE starts at line ~{lines_before}, ends at line ~{lines_after}')
        print(f'Last chars: ...{body[max(0,iife_end-15):iife_end+5]}')
    else:
        print(f'Could not find IIFE end. Final depth: {depth}')
        print(f'Last 100 chars of body: ...{body[-100:]}')
else:
    print('Could not find IIFE start')
