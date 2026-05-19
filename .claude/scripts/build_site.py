#!/usr/bin/env python3
"""
build_site.py — Read Moonlight project data and regenerate site/data.js

Usage:
  python3 .claude/scripts/build_site.py          # update data.js only
  python3 .claude/scripts/build_site.py --html   # also inject data into HTML pages

Reads:  missions/weight-loss.md, missions/skincare.md, missions/savings.md,
        missions/spine-rehab.md, projects/A1-body.md, projects/A2-grade-leader.md,
        projects/A3-finance.md, projects/A4-ai-capability.md, notes/today.md,
        moonlight/diary.md, moonlight/inner-monologue/highlights.md
Output: site/data.js
"""

import json
import re
import os
import sys
from datetime import date, datetime

MOONLIGHT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SITE_DATA_JS = os.path.join(MOONLIGHT, "site", "data.js")

def read_file(path):
    """Read file relative to Moonlight root."""
    full = os.path.join(MOONLIGHT, path)
    if not os.path.exists(full):
        return ""
    with open(full, "r") as f:
        return f.read()

def extract_regex(text, pattern, default=None, cast=int):
    """Extract first capture group from regex match."""
    m = re.search(pattern, text)
    if not m:
        return default
    val = m.group(1).strip()
    try:
        return cast(val)
    except (ValueError, TypeError):
        return val

def parse_weight_loss(text):
    """Extract weight data from missions/weight-loss.md."""
    table_weights = re.findall(r'\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(\d+(?:\.\d+)?)\s*\|', text)
    if table_weights:
        table_weights.sort(key=lambda x: x[0])
        latest_weight = float(table_weights[-1][1])
        phase1_current = max(0, min(47, round(213 - latest_weight)))
    else:
        latest_weight = extract_regex(text, r'当前\s*(\d+(?:\.\d+)?)\s*斤', default=None, cast=float)
        phase1_current = extract_regex(text, r'一阶.*?(\d+)/47', default=33)

    phase2_current = extract_regex(text, r'二阶.*?(\d+)/22', default=0)

    return {
        "phase1_current": phase1_current,
        "phase2_current": phase2_current,
        "latest_weight": latest_weight
    }

def parse_skincare(text):
    """Extract skincare streak from missions/skincare.md."""
    streak = extract_regex(text, r'streak[:\s]*(\d+)', default=0)
    return {"streak": streak}

def parse_savings(text):
    """Extract savings data from missions/savings.md."""
    pct = extract_regex(text, r'(\d+)%', default=20)
    emergency_pct = extract_regex(text, r'应急金[:\s]*(\d+)%', default=15)
    return {"savings_pct": pct, "emergency_pct": emergency_pct}

def parse_today(text):
    """Extract current context from notes/today.md."""
    weight = extract_regex(text, r'体重[:：]\s*(\d+(?:\.\d+)?)', default=None, cast=float)
    pullups = extract_regex(text, r'引体[向上]*[:：].*?(\d+)\s*个', default=4)
    gaokao_days = extract_regex(text, r'高考.*?(\d+)\s*天', default=26)
    phase = extract_regex(text, r'(P0\.[12])', default="P0.1", cast=str)

    return {
        "weight": weight,
        "pullups": pullups,
        "gaokao_days": gaokao_days,
        "phase": phase
    }

def parse_body_project(text):
    """Extract KPI data from projects/A1-body.md."""
    pullup_current = extract_regex(text, r'引体[:：]\s*(\d+)', default=4)
    return {"pullup_current": pullup_current}

def parse_moonlight_diary(text, n=3):
    """Extract last N diary entries from moonlight/diary.md."""
    entries = []
    pattern = r'##\s*(\d{4}-\d{2}-\d{2})\s*\n(.+?)(?=\n##\s*\d{4}-\d{2}-\d{2}|\Z)'
    for m in re.finditer(pattern, text, re.DOTALL):
        date_str = m.group(1)
        body = m.group(2).strip()
        body = re.sub(r'\s*月光\s*\d{2}:\d{2}\s*$', '', body).strip()
        body = re.sub(r'\n+', ' ', body).strip()
        if len(body) > 320:
            body = body[:317] + '...'
        entries.append({"date": date_str, "body": body})
    entries.sort(key=lambda x: x["date"], reverse=True)
    return entries[:n]

def parse_moonlight_monologue(text, n=6):
    """Extract last N monologue highlights."""
    entries = []
    pattern = r'-\s*\[([\d\-\s:]+)\]\s*(.+)'
    for m in re.finditer(pattern, text):
        time_str = m.group(1).strip()
        msg = m.group(2).strip()
        if len(msg) > 140:
            msg = msg[:137] + '...'
        entries.append({"time": time_str, "text": msg})
    return entries[-n:][::-1] if entries else []


# 4 工程卡白名单（顺序即 QUEST LOG 显示顺序）
ENGINEERING_CARDS = [
    ("projects/A1-body.md",          "A1", "身体重塑",   "💪", "red"),
    ("projects/A2-grade-leader.md",  "A2", "年级长立柱", "🏛️", "blue"),
    ("projects/A3-finance.md",       "A3", "财务筑基",   "🏦", "gold"),
    ("projects/A4-ai-capability.md", "A4", "AI 时代能力", "🤖", "green"),
]


def parse_engineering_progress(text, n=2):
    """Extract last N progress entries from 工程卡「最近 N 条推进」 节。
    匹配 `- [YYYY-MM-DD] body`，placeholder 自然跳过。"""
    section_match = re.search(r'##\s*最近[^\n]*推进\s*\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
    if not section_match:
        return []
    section = section_match.group(1)
    pattern = re.compile(r'-\s*\[?(\d{4}-\d{2}-\d{2})\]?\s*[:：]?\s*(.+)')
    entries = []
    for line in section.splitlines():
        m = pattern.match(line.strip())
        if m:
            body = m.group(2).strip()
            if len(body) > 110:
                body = body[:107] + '...'
            entries.append({"date": m.group(1), "body": body})
    entries.sort(key=lambda x: x["date"], reverse=True)
    return entries[:n]


def parse_frontmatter(text):
    """Extract simple YAML-ish frontmatter fields used by project cards."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    raw = text[3:end]
    data = {}
    current_map = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if not line.startswith(" ") and ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value:
                data[key] = value
                current_map = None
            else:
                data[key] = {}
                current_map = key
        elif current_map and ":" in line:
            key, value = line.split(":", 1)
            data[current_map][key.strip()] = value.strip()
    return data


def parse_next_steps(text, n=2):
    """Extract concrete bullets from 工程卡「下一步」节."""
    section = extract_section_from_text(text, "## 下一步", 900)
    steps = []
    for line in section.splitlines():
        item = line.strip()
        if not item.startswith("- "):
            continue
        body = item[2:].strip()
        if not body or body.startswith("_待"):
            continue
        if len(body) > 90:
            body = body[:87] + "..."
        steps.append(body)
    return steps[:n]


def extract_section_from_text(text, heading, limit=1600):
    idx = text.find(heading)
    if idx == -1:
        return ""
    next_idx = text.find("\n## ", idx + len(heading))
    section = text[idx:] if next_idx == -1 else text[idx:next_idx]
    return section[:limit]


def days_since(date_str):
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None
    return (date.today() - d).days


def priority_threshold(priority):
    return {
        "critical": 0,
        "high": 3,
        "medium": 7,
        "low": 14,
    }.get((priority or "").lower(), 7)


def live_status(priority, idle_days):
    if idle_days is None:
        return {"code": "UNKNOWN", "label": "UNKNOWN", "message": "没有最近推进日期"}
    threshold = priority_threshold(priority)
    if idle_days > threshold:
        return {"code": "PUSH", "label": "PUSH", "message": f"已 {idle_days} 天未推进，超过 {threshold} 天阈值"}
    if priority == "critical" and idle_days == 0:
        return {"code": "LIVE", "label": "LIVE", "message": "当前阶段主矛盾，今天已触碰"}
    if priority == "critical":
        return {"code": "PUSH", "label": "PUSH", "message": "critical 工程今天还没推进"}
    if idle_days == threshold:
        return {"code": "WATCH", "label": "WATCH", "message": f"已到 {threshold} 天提醒线"}
    return {"code": "LIVE", "label": "LIVE", "message": f"{idle_days} 天前有推进"}


def build_engineering_progress(n_per_card=2):
    """Aggregate 4 工程卡 recent progress for QUEST LOG."""
    current_phase = parse_today(read_file("notes/today.md")).get("phase", "P0.1")
    out = []
    for filepath, code, name, icon, color in ENGINEERING_CARDS:
        text = read_file(filepath)
        entries = parse_engineering_progress(text, n=n_per_card) if text else []
        frontmatter = parse_frontmatter(text) if text else {}
        priority_map = frontmatter.get("phase_priority", {}) if isinstance(frontmatter.get("phase_priority"), dict) else {}
        priority = priority_map.get(current_phase, "medium")
        last_progress_date = entries[0]["date"] if entries else frontmatter.get("last_updated")
        idle_days = days_since(last_progress_date)
        status = live_status(priority, idle_days)
        next_steps = parse_next_steps(text, n=2) if text else []
        out.append({
            "code": code,
            "name": name,
            "icon": icon,
            "color": color,
            "priority": priority,
            "phase": current_phase,
            "lastProgressDate": last_progress_date,
            "idleDays": idle_days,
            "liveStatus": status,
            "nextSteps": next_steps,
            "recent": entries,
        })
    return out


# ---- JS template helpers ----

def _js_obj(**kwargs):
    """Build a JS object literal string from kwargs.
    Values: str -> quoted, bool/int -> literal, dict -> recurse."""
    parts = []
    for k, v in kwargs.items():
        if isinstance(v, bool):
            parts.append(f'{k}: {str(v).lower()}')
        elif isinstance(v, int):
            parts.append(f'{k}: {v}')
        elif isinstance(v, dict):
            inner = _js_obj(**v)
            parts.append(f'{k}: {{ {inner} }}')
        else:
            parts.append(f'{k}: "{v}"')
    return ", ".join(parts)


def generate_data_js(data):
    """Generate site/data.js content from extracted data."""

    w = data.get("weight", {})
    s = data.get("skincare", {})
    sv = data.get("savings", {})
    t = data.get("today", {})
    b = data.get("body_project", {})
    m_diary = data.get("moonlight_diary", [])
    m_mono = data.get("moonlight_monologue", [])
    eng_progress = data.get("engineering_progress", [])

    phase1_cur = w.get("phase1_current", 33)
    phase1_pct = round(phase1_cur / 47 * 100)
    phase2_cur = w.get("phase2_current", 0)
    pullup_cur = t.get("pullups", b.get("pullup_current", 4))
    pullup_pct = round(pullup_cur / 15 * 100)
    skincare_streak = s.get("streak", 0)
    skincare_pct = min(round(skincare_streak / 30 * 100), 100)
    savings_pct = sv.get("savings_pct", 20)
    emergency_pct = sv.get("emergency_pct", 15)
    gaokao_days = t.get("gaokao_days", 26)
    phase = t.get("phase", "P0.1")

    # Dynamic reward unlock based on current weight
    latest_w = w.get("latest_weight", 180.6) or 180.6
    reward_gates = [
        ("HAIRSTYLE UPGRADE", 178),
        ("BROW SHAPING", 175),
        ("NEW WARDROBE", 170),
        ("SKINCARE PRO", 166),
        ("★ ZHOU HEI YA ★", 160),
        ("📷 NIKON Z SERIES", 155),
        ("🎿 HOKKAIDO", 144),
    ]
    reward_parts = []
    for name, gate in reward_gates:
        unlocked = "true" if latest_w <= gate else "false"
        reward_parts.append(f'      {{ name: "{name}", gate: "{gate}", unlocked: {unlocked} }}')
    rewards_block = "[\n" + ",\n".join(reward_parts) + "\n    ]"

    phase_labels = {
        "P0.1": "高考冲刺尾段",
        "P0.2": "学期收尾",
        "P1": "第一暑假核心窗口",
        "P2": "第一上学期",
        "P3": "第一寒假",
        "P4": "第一下学期",
        "P5": "第二暑假",
        "P6": "第二学年",
        "P7": "第三学年",
    }
    phase_label = phase_labels.get(phase, phase)

    today_str = date.today().isoformat()

    moonlight_char_json = json.dumps(
        {"diary": m_diary, "monologue": m_mono}, ensure_ascii=False, indent=4
    )
    moonlight_char_json = moonlight_char_json.replace("\n", "\n  ")

    engineering_progress_json = json.dumps(eng_progress, ensure_ascii=False, indent=4)
    engineering_progress_json = engineering_progress_json.replace("\n", "\n  ")

    # Engine area cards — live data injected directly
    body_extra = ""
    body_extra += f"    weight: {latest_w},\n"
    body_extra += f"    pullups: {pullup_cur},\n"

    js = (
        "// ============================================================\n"
        "// Moonlight Project Data · Auto-generated by build_site.py\n"
        f"// Last updated: {today_str}\n"
        "// ============================================================\n"
        "\n"
        "const SITE_DATA = {\n"
        f'  phase: {{ current: "{phase}", label: "{phase_label}", gaokaoDays: {gaokao_days} }},\n'
        "\n"
        "  body: {\n"
        f"    latestWeight: {latest_w},\n"
        f"    phase1Target: 166,\n"
        f"    phase2Target: 155,\n"
        f"    finalTarget: 144,\n"
        f"    weightPhase1: {{ current: {phase1_cur}, total: 47, pct: {phase1_pct} }},\n"
        f"    weightPhase2: {{ current: {phase2_cur}, total: 22, pct: 0 }},\n"
        f"    pullups: {{ current: {pullup_cur}, goal: 15, pct: {pullup_pct} }},\n"
        f"    skincare: {{ streak: {skincare_streak}, target: 30, pct: {skincare_pct} }},\n"
        f'    spine: {{ status: "ACTIVE", pct: 65 }},\n'
        f'    backShoulder: {{ status: "P0.2 START", pct: 10 }},\n'
        f'    appearance: {{ status: "SOON", pct: 8 }},\n'
        f"    rewards: {rewards_block}\n"
        "  },\n"
        "\n"
        "  career: {\n"
        '    gaokaoDate: "2026-06-07",\n'
        '    targetRole: "Head Teacher",\n'
        '    targetYear: "2027.7",\n'
        '    englishTeaching: { status: "ACTIVE", next: "语法填空→应用文" },\n'
        '    gradeManager: { status: "v4.11", note: "P1 暑假重启" }\n'
        "  },\n"
        "\n"
        "  finance: {\n"
        f"    savings: {{ pct: {savings_pct} }},\n"
        '    monthlyRate: { active: true, note: "7,000/月" },\n'
        f'    emergencyFund: {{ pct: {emergency_pct}, target: "6 months expenses" }},\n'
        '    cameraFund: { current: 0, goal: 7000, perMilestone: 1000, nextTrigger: 178 }\n'
        "  },\n"
        "\n"
        "  ai: {\n"
        '    gradeManager: { status: "v4.11 READY", note: "P1 暑假重启 (=AFM 2.0)" },\n'
        '    englishTeaching: { status: "ACTIVE", note: "语法填空试课中" },\n'
        '    moonlight: { status: "ONLINE", version: "v2.3" },\n'
        '    workCapability: { status: "P1 START", note: "5 files, 待启动" }\n'
        "  },\n"
        "\n"
        f"  moonlightChar: {moonlight_char_json},\n"
        "\n"
        f"  engineeringProgress: {engineering_progress_json},\n"
        "\n"
        "  meta: {\n"
        f'    lastUpdated: "{today_str}",\n'
        '    threeYearPlan: "v2.3",\n'
        "    level: 27\n"
        "  }\n"
        "};\n"
        "\n"
        "window.SITE_DATA = SITE_DATA;\n"
    )

    return js


def main():
    print("[build_site] Reading Moonlight project data...")

    weight_text = read_file("missions/weight-loss.md")
    skincare_text = read_file("missions/skincare.md")
    savings_text = read_file("missions/savings.md")
    today_text = read_file("notes/today.md")
    body_project_text = read_file("projects/A1-body.md")
    diary_text = read_file("moonlight/diary.md")
    mono_text = read_file("moonlight/inner-monologue/highlights.md")

    weight_data = parse_weight_loss(weight_text)
    skincare_data = parse_skincare(skincare_text)
    savings_data = parse_savings(savings_text)
    today_data = parse_today(today_text)
    body_data = parse_body_project(body_project_text)
    diary_data = parse_moonlight_diary(diary_text, n=3)
    mono_data = parse_moonlight_monologue(mono_text, n=6)
    eng_progress = build_engineering_progress(n_per_card=2)

    data = {
        "weight": weight_data,
        "skincare": skincare_data,
        "savings": savings_data,
        "today": today_data,
        "body_project": body_data,
        "moonlight_diary": diary_data,
        "moonlight_monologue": mono_data,
        "engineering_progress": eng_progress,
    }

    print(f"  Weight Phase I: {weight_data['phase1_current']}/47")
    print(f"  Weight Phase II: {weight_data['phase2_current']}/22")
    print(f"  Latest weight: {weight_data['latest_weight']}")
    print(f"  Skincare streak: {skincare_data['streak']}")
    print(f"  Savings: {savings_data['savings_pct']}%")
    print(f"  Pull-ups: {today_data['pullups']}")
    print(f"  Gaokao days: {today_data['gaokao_days']}")
    print(f"  Phase: {today_data['phase']}")
    print(f"  Moonlight diary entries: {len(diary_data)}")
    print(f"  Moonlight monologue highlights: {len(mono_data)}")
    eng_total = sum(len(e["recent"]) for e in eng_progress)
    print(f"  Engineering progress entries: {eng_total} across {len(eng_progress)} cards")

    js_content = generate_data_js(data)

    with open(SITE_DATA_JS, "w") as f:
        f.write(js_content)

    print(f"\n[build_site] Wrote {SITE_DATA_JS}")

    if "--html" in sys.argv:
        inject_into_html(data)

    print("[build_site] Done.")


def inject_into_html(data):
    """Update static values in HTML files with current data."""
    index_html = os.path.join(MOONLIGHT, "site", "index.html")

    w = data.get("weight", {})
    t = data.get("today", {})
    sv = data.get("savings", {})

    phase1_pct = round(w.get("phase1_current", 33) / 47 * 100)
    savings_pct = sv.get("savings_pct", 20)
    gaokao_days = t.get("gaokao_days", 26)

    if os.path.exists(index_html):
        with open(index_html, "r") as f:
            html = f.read()

        html = re.sub(
            r'(card-bar-fill"\s+style="width:)\d+%(;background:var\(--red\))',
            f'\\g<1>{phase1_pct}%\\g<2>', html,
        )
        html = re.sub(
            r'(card-bar-fill"\s+style="width:)\d+%(;background:var\(--gold\))',
            f'\\g<1>{savings_pct}%\\g<2>', html,
        )
        ai_pct = 25
        html = re.sub(
            r'(card-bar-fill"\s+style="width:)\d+%(;background:var\(--green\))',
            f'\\g<1>{ai_pct}%\\g<2>', html,
        )
        html = re.sub(r"Level \d+", "Level 27", html)
        html = re.sub(r"P0\.\d", t.get("phase", "P0.1"), html)

        with open(index_html, "w") as f:
            f.write(html)

        print("  Injected data into index.html")


if __name__ == "__main__":
    main()
