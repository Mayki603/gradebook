#!/usr/bin/env python3
"""Перевірка sequence-діаграм (Завдання 3) на узгодженість зі spec, ER і Gherkin.

Запуск з кореня репозиторію:  python scripts/check_sequence.py
Перевіряє: фрагменти alt/opt/loop/par, activation bars, учасників і поля проти ER,
кількість сценаріїв проти use-cases.md, тексти помилок, REQ у вступах діаграм,
та що все, чого немає в Завданні 2, оформлено як припущення в spec.md.
Код виходу 0 — проблем немає, 1 — є проблеми.
"""
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SEQ, UC, SPEC = "sequence-diagrams.md", "use-cases.md", "spec.md"
ER = "er-diagram.mmd" if os.path.exists("er-diagram.mmd") else "DEFENSE.md"
# те, що діаграми можуть вводити поза Завданням 2, лише як явне припущення в spec.md
ASSUMPTIONS = {"gradeTypeDefault": "A2", "currentScores": "A1"}
ERROR_TEXTS = ["Оцінка має бути від 0 до 100", "Немає доступу до цього заняття або студента", "403"]


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


seq, uc, spec, er_src = read(SEQ), read(UC), read(SPEC), read(ER)

# --- сутності й атрибути ER
er_text = er_src[er_src.index("erDiagram"):]
entities = {}
for m in re.finditer(r"^\s*(\w+)\s*\{\s*\n(.*?)^\s*\}", er_text, re.S | re.M):
    entities[m.group(1)] = set(re.findall(r"^\s*\w+\s+(\w+)", m.group(2), re.M))
all_attrs = set().union(*entities.values())

blocks = re.findall(r"```mermaid\n(.*?)```", seq, re.S)
titles = re.findall(r"^## (S\d+)\.", seq, re.M)
problems = []
all_kinds = set()

for i, block in enumerate(blocks):
    name = titles[i] if i < len(titles) else "#%d" % (i + 1)
    parts = dict(re.findall(r"(?:actor|participant)\s+(\w+)\s+as\s+(.+)", block))
    for label in parts.values():
        label = label.strip()
        if label.isupper() and label not in entities:
            problems.append("%s: учасник %s відсутній у ER" % (name, label))
    for ident in set(re.findall(r"\b([a-z]+_[a-z_]+)\b", block)):
        if ident not in all_attrs:
            problems.append("%s: поле %s відсутнє в ER" % (name, ident))

    stack, kinds, path, branch = [], set(), [], 0
    active, open_calls = {}, []
    for ln, raw in enumerate(block.split("\n"), 1):
        s = raw.strip()
        m = re.match(r"(alt|opt|loop|par|critical|break|rect)\b", s)
        if m:
            stack.append(m.group(1)); kinds.add(m.group(1)); branch += 1; path.append(branch); continue
        if re.match(r"(else|and)\b", s):
            branch += 1; path[-1] = branch; continue
        if s == "end":
            if stack:
                stack.pop(); path.pop()
            else:
                problems.append("%s: зайвий end (рядок %d)" % (name, ln))
            continue
        m = re.match(r"(activate|deactivate)\s+(\w+)", s)
        if m:
            kind, who = m.groups()
            if stack:
                problems.append("%s: %s %s всередині фрагмента %s (activation bar обривається в гілці)" % (name, kind, who, stack[-1]))
            active[who] = active.get(who, 0) + (1 if kind == "activate" else -1)
            if active[who] < 0:
                problems.append("%s: %s деактивовано без активації" % (name, who))
            continue
        m = re.match(r"(\w+)-{1,2}>>([+-]?)(\w+):", s)
        if m:
            src, flag, dst = m.groups()
            if flag == "+":
                open_calls.append((dst, tuple(path)))
            elif flag == "-":
                for j in range(len(open_calls) - 1, -1, -1):
                    if open_calls[j][0] == src:
                        if open_calls[j][1] != tuple(path):
                            problems.append("%s: виклик і return для %s у різних гілках (рядок %d)" % (name, src, ln))
                        open_calls.pop(j)
                        break
                else:
                    problems.append("%s: return від %s без виклику (рядок %d)" % (name, src, ln))
    if stack:
        problems.append("%s: незакритий фрагмент %s" % (name, stack))
    if any(v != 0 for v in active.values()):
        problems.append("%s: незбалансовані activate/deactivate %s" % (name, active))
    if open_calls:
        problems.append("%s: виклики з '+' без return" % name)
    if not kinds & {"alt", "opt", "loop"}:
        problems.append("%s: немає жодного фрагмента alt/opt/loop" % name)
    all_kinds |= kinds

for needed in ("alt", "opt", "loop", "par"):
    if needed not in all_kinds:
        problems.append("у наборі діаграм немає фрагмента %s" % needed)

scenarios = re.findall(r"^\s*Scenario(?: Outline)?:\s*(.+)$", uc, re.M)
if len(scenarios) != len(blocks):
    problems.append("сценаріїв у use-cases.md %d, діаграм %d" % (len(scenarios), len(blocks)))
for text in ERROR_TEXTS:
    if text not in seq:
        problems.append("у діаграмах немає тексту/коду із Завдання 2: %s" % text)

intro = "\n".join(re.findall(r"^Gherkin.*$", seq, re.M))
for req in sorted(set(re.findall(r"\*\*REQ-(\d+):", uc)), key=int):
    if "REQ-%s" % req not in intro:
        problems.append("REQ-%s не згадано у вступах діаграм" % req)

for token, aid in ASSUMPTIONS.items():
    if token in seq and aid not in spec:
        problems.append("діаграми містять %s, якого немає в Завданні 2, а припущення %s не описане в spec.md" % (token, aid))

print("ER: %s | діаграм: %d | сценаріїв: %d | фрагменти: %s" % (", ".join(sorted(entities)), len(blocks), len(scenarios), ", ".join(sorted(all_kinds))))
if problems:
    print("ПРОБЛЕМИ (%d):" % len(problems))
    for p in problems:
        print(" -", p)
    sys.exit(1)
print("OK: структурних розбіжностей не знайдено")