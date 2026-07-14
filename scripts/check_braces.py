# -*- coding: utf-8 -*-
"""Check brace balance with string awareness."""
import subprocess, re, sys

def count_braces(content):
    """Count brace balance, ignoring braces inside strings."""
    balance = 0
    in_string = False
    in_template = False
    string_char = None
    i = 0
    while i < len(content):
        ch = content[i]
        if in_string:
            if ch == '\\':
                i += 2  # skip escaped char
                continue
            elif ch == string_char:
                in_string = False
        elif in_template:
            if ch == '`':
                in_template = False
            elif ch == '${':
                i += 2
                balance += 1  # brace inside template
                continue
        else:
            if ch == '"' or ch == "'":
                in_string = True
                string_char = ch
            elif ch == '`':
                in_template = True
            elif ch == '{':
                balance += 1
            elif ch == '}':
                balance -= 1
        i += 1
    return balance

# Original file
result = subprocess.run(['git', 'show', 'fac9dd2:fc26_fsu_mod/【FSU】EAFC FUT WEB 增强器-26.09.yyh.js'],
    capture_output=True, text=True, encoding='utf-8', errors='replace')
orig = result.stdout

# Current file
with open('fc26_fsu_mod/【FSU】EAFC FUT WEB 增强器-26.09.yyh.js', 'r', encoding='utf-8') as f:
    current = f.read()

# Extract body after IIFE
for marker in ['(function () {', '(function(){']:
    idx = orig.find(marker)
    if idx >= 0:
        orig_body = orig[idx:]
        break
for marker in ['(function () {', '(function(){']:
    idx = current.find(marker)
    if idx >= 0:
        curr_body = current[idx:]
        break

orig_balance = count_braces(orig_body)
curr_balance = count_braces(curr_body)

print(f"Original body brace balance (string-aware): {orig_balance}")
print(f"Current body brace balance (string-aware): {curr_balance}")
print(f"Delta: {curr_balance - orig_balance}")
