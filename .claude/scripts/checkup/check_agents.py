#!/usr/bin/env python3
"""
检查所有 moonlight launchd agents 状态，写入 notes/system-status.md
每 2 小时跑一次（见 com.moonlight.agents.plist）
"""
import os
import subprocess
import json
from pathlib import Path
from datetime import datetime

VAULT = Path(os.environ.get('MOONLIGHT_VAULT', '/Users/zhenliu/Moonlight'))
STATUS_FILE = VAULT / 'notes/system-status.md'

AGENTS = [
    'com.moonlight.health',
    'com.moonlight.material',
    'com.moonlight.think',
    'com.moonlight.diary',
    'com.moonlight.morning',
    'com.moonlight.weekly',
    'com.moonlight.rss',
    'com.moonlight.skincare',
    'com.moonlight.monthly',
    'com.moonlight.memory',
]

def check_agent(label: str) -> dict:
    try:
        r = subprocess.run(['launchctl', 'list', label],
                           capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            return {'status': 'not_loaded', 'exit': None}
        info = {}
        for line in r.stdout.splitlines():
            line = line.strip().strip(';').strip('"')
            if '=' in line:
                k, _, v = line.partition(' = ')
                info[k.strip().strip('"')] = v.strip().strip('"').strip(';')
        exit_code = info.get('LastExitStatus', '?')
        pid = info.get('PID') or info.get('pid')
        return {
            'status': 'running' if pid and pid != '0' else 'idle',
            'exit': exit_code,
            'pid': pid,
        }
    except Exception as e:
        return {'status': 'error', 'exit': None, 'err': str(e)}

def main():
    now = datetime.now()
    results = {}
    warnings = []

    for agent in AGENTS:
        info = check_agent(agent)
        results[agent] = info
        exit_code = str(info.get('exit', ''))
        if info['status'] == 'not_loaded':
            warnings.append(f'{agent} 未加载')
        elif exit_code not in ('0', '?', '', 'None'):
            warnings.append(f'{agent} 最后退出码 {exit_code}')

    lines = [f'# 系统状态 · {now.strftime("%Y-%m-%d %H:%M")} 自动更新\n']
    if warnings:
        lines.append('## ⚠ 异常')
        for w in warnings:
            lines.append(f'- {w}')
        lines.append('')
    else:
        lines.append('## ✅ 所有 agent 正常\n')

    lines.append('## 详情')
    for agent, info in results.items():
        name = agent.replace('com.moonlight.', '')
        status_icon = '🟢' if info['status'] in ('running', 'idle') and str(info.get('exit','0')) == '0' else '🔴'
        lines.append(f'- {status_icon} **{name}**: {info["status"]} · 退出码 {info.get("exit","?")}')

    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'✅ 写入 {STATUS_FILE.name} · {len(warnings)} 个异常')
    if warnings:
        for w in warnings:
            print(f'  ⚠ {w}')

if __name__ == '__main__':
    main()
