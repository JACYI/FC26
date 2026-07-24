# -*- coding: utf-8 -*-
import subprocess, re, os

def get_code(commit):
    result = subprocess.run(['git', 'show', commit + ':fc26_fsu_mod/【FSU】EAFC FUT WEB 增强器-26.09.yyh.js'],
                          capture_output=True, text=True, encoding='utf-8', errors='replace')
    return result.stdout

def count_braces(code_section):
    """Count net braces outside strings/comments."""
    balance = 0
    in_str = False
    str_char = None
    i = 0
    while i < len(code_section):
        ch = code_section[i]
        if in_str:
            if ch == '\\' and i+1 < len(code_section):
                i += 2
                continue
            if ch == str_char:
                in_str = False
            i += 1
            continue
        if ch == '/' and i+1 < len(code_section):
            if code_section[i+1] == '/':
                while i < len(code_section) and code_section[i] != '\n':
                    i += 1
                continue
            if code_section[i+1] == '*':
                i += 2
                while i < len(code_section) and not (code_section[i] == '*' and code_section[i+1] == '/'):
                    i += 1
                i += 2
                continue
        if ch in '"\'':
            in_str = True
            str_char = ch
            i += 1
            continue
        if ch == '{':
            balance += 1
        elif ch == '}':
            balance -= 1
        i += 1
    return balance

orig = get_code('fac9dd2')
new = get_code('6ccf70a')

orig_lines = orig.split('\n')
new_lines = new.split('\n')

# Section 1: old 3571-3608 (38 lines), new 3573-3645 (73 lines)
sec1_old = '\n'.join(orig_lines[3570:3570+38])
sec1_new = '\n'.join(new_lines[3572:3572+73])
print(f'Sec1 old: {count_braces(sec1_old)}')
print(f'Sec1 new: {count_braces(sec1_new)}')
print(f'Sec1 delta: {count_braces(sec1_new) - count_braces(sec1_old)}')

# Section 23: old 5482-5520 (39 lines), new 5586-5659 (74 lines)
sec23_old = '\n'.join(orig_lines[5481:5481+39])
sec23_new = '\n'.join(new_lines[5585:5585+74])
print(f'\nSec23 old: {count_braces(sec23_old)}')
print(f'Sec23 new: {count_braces(sec23_new)}')
print(f'Sec23 delta: {count_braces(sec23_new) - count_braces(sec23_old)}')

# Section 4: old 14070-14108 (39 lines), new 14195-14269 (75 lines)
sec4_old = '\n'.join(orig_lines[14069:14069+39])
sec4_new = '\n'.join(new_lines[14194:14194+75])
print(f'\nSec4 old: {count_braces(sec4_old)}')
print(f'Sec4 new: {count_braces(sec4_new)}')
print(f'Sec4 delta: {count_braces(sec4_new) - count_braces(sec4_old)}')
