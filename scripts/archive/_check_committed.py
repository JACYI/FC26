# -*- coding: utf-8 -*-
"""Check brace balance of committed version."""
import subprocess

result = subprocess.run(['git', 'show', 'HEAD:fc26_fsu_mod/【FSU】EAFC FUT WEB 增强器-26.09.yyh.js'],
    capture_output=True, text=True, encoding='utf-8', errors='replace')
content = result.stdout

idx = content.find('(function')
if idx >= 0:
    body = content[idx:]

    balance = 0
    in_str = False
    str_char = None
    in_template = False
    in_block_comment = False
    in_line_comment = False

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
            balance += 1
        if ch == '}':
            balance -= 1
        i += 1

    print(f'Committed brace balance: {balance}')
else:
    print('Could not find IIFE')
