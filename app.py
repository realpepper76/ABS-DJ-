from flask import Flask, render_template, request, redirect, url_for
import os
import json
import random
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)

DATA_DIR = 'data'
NAMES_FILE = os.path.join(DATA_DIR, 'names.json')
FIXED_FILE = os.path.join(DATA_DIR, 'fixed_assignments.json')

DAYS = ["월", "화", "수", "목", "금"]
TIMES = ["아침", "점심", "저녁"]

os.makedirs(DATA_DIR, exist_ok=True)

if not os.path.exists(NAMES_FILE):
    with open(NAMES_FILE, 'w', encoding='utf-8') as f:
        json.dump(["이승민", "정솔미", "이승헌", "문창균", "박순후", "이준호", "박신재"], f, ensure_ascii=False)

if not os.path.exists(FIXED_FILE):
    with open(FIXED_FILE, 'w', encoding='utf-8') as f:
        json.dump({}, f, ensure_ascii=False)

def load_names():
    try:
        with open(NAMES_FILE, 'r', encoding='utf-8') as f:
            data = f.read()
            return json.loads(data) if data.strip() else []
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_names(names):
    with open(NAMES_FILE, 'w', encoding='utf-8') as f:
        json.dump(names, f, ensure_ascii=False)

def load_fixed():
    try:
        with open(FIXED_FILE, 'r', encoding='utf-8') as f:
            data = f.read()
            raw = json.loads(data) if data.strip() else {}
            return {tuple(k.split('_')): v for k, v in raw.items()}
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_fixed(fixed):
    with open(FIXED_FILE, 'w', encoding='utf-8') as f:
        raw = {f"{k[0]}_{k[1]}": v for k, v in fixed.items()}
        json.dump(raw, f, ensure_ascii=False)

@app.route('/', methods=['GET', 'POST'])
def index():
    names = load_names()
    fixed = load_fixed()
    schedule = []
    assigned_at = None
    summary = {}

    if request.method == 'POST':
        if 'new_name' in request.form:
            new_name = request.form.get("new_name").strip()
            if new_name and new_name not in names:
                names.append(new_name)
                save_names(names)

        elif 'delete' in request.form:
            to_delete = request.form.get("delete")
            names = [n for n in names if n != to_delete]
            save_names(names)
            new_fixed = {}
            for key, val in fixed.items():
                updated = [v for v in val if v != to_delete]
                if updated:
                    new_fixed[key] = updated
            save_fixed(new_fixed)
            fixed = new_fixed

        elif 'save_fixed' in request.form:
            new_fixed = {}
            for day in DAYS:
                for time in TIMES:
                    k = f"{day}_{time}"
                    v1 = request.form.get(f"{k}_1")
                    v2 = request.form.get(f"{k}_2")
                    selected = [v for v in [v1, v2] if v]
                    if selected:
                        new_fixed[(day, time)] = selected
            save_fixed(new_fixed)
            fixed = new_fixed

        elif 'assign' in request.form:
            assigned_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            all_slots = [(d, t) for d in DAYS for t in TIMES]
            total_assignments = len(all_slots) * 2

            # 고정 배정 횟수 계산
            fixed_counts = defaultdict(int)
            for people in fixed.values():
                for name in people:
                    if name in names:
                        fixed_counts[name] += 1

            # 목표 배정 횟수 계산
            base, rem = divmod(total_assignments, len(names))
            targets = {name: base + (1 if i < rem else 0) for i, name in enumerate(names)}
            for name in names:
                targets[name] = max(0, targets[name] - fixed_counts.get(name, 0))

            max_attempts = 1000
            for attempt in range(max_attempts):
                temp_schedule = []
                temp_counts = defaultdict(int)
                success = True

                for day, time in all_slots:
                    key = (day, time)
                    fixed_names = [n for n in fixed.get(key, []) if n in names]
                    if len(fixed_names) > 2:
                        success = False
                        break

                    available = [n for n in names if n not in fixed_names and temp_counts[n] < targets[n]]
                    if len(available) < (2 - len(fixed_names)):
                        success = False
                        break

                    try:
                        random_part = random.sample(available, 2 - len(fixed_names))
                    except:
                        success = False
                        break

                    pair = fixed_names + random_part
                    for name in random_part:
                        temp_counts[name] += 1

                    temp_schedule.append({"day": day, "time": time, "names": pair})

                if success:
                    schedule = temp_schedule
                    break

            summary = {name: [] for name in names}
            for entry in schedule:
                for name in entry["names"]:
                    summary[name].append(f"{entry['day']} {entry['time']}")

    return render_template("index.html", schedule=schedule, assigned_at=assigned_at, summary=summary,
                           names=names, days=DAYS, times=TIMES, fixed_assignments=fixed)

if __name__ == '__main__':
    app.run(debug=True)
