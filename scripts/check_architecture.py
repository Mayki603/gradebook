#!/usr/bin/env python3
"""Перевірка діаграми компонентів (Завдання 5): діаграма ↔ модель, межа, шари, інтерфейси, порти,
трасування до ER, вимог, Sequence і BPMN.

Запуск з кореня репозиторію:  python scripts/check_architecture.py
Читає: architecture.md, sequence-diagrams.md, process.bpmn, use-cases.md, spec.md, er-diagram.mmd (або DEFENSE.md).
Код виходу 0 — проблем немає, 1 — є проблеми.
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ARCH, SEQ, BPMN, UC, SPEC = "architecture.md", "sequence-diagrams.md", "process.bpmn", "use-cases.md", "spec.md"
ER = "er-diagram.mmd" if os.path.exists("er-diagram.mmd") else "DEFENSE.md"
WRITE_PREFIX = ("create", "update", "delete", "insert", "save")


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


problems = []
def bad(msg): problems.append(msg)


arch, seq_md, uc_md, spec_md, er_src = read(ARCH), read(SEQ), read(UC), read(SPEC), read(ER)
model = json.loads(re.search(r"```json\n(.*?)```", arch, re.S).group(1))
mermaid = re.search(r"```mermaid\n(.*?)```", arch, re.S).group(1)
comp = {c["id"]: c for c in model["components"]}
ports = {p["id"]: p for p in model["ports"]}
ifaces = {i["id"]: i for i in model["interfaces"]}
LAYERS = model["layers"]

# ---------- розбір діаграми ----------
nodes, edges, stack, member = {}, [], [], {}
for raw in mermaid.split("\n"):
    s = raw.strip()
    if not s or s.startswith("%%") or s.startswith("classDef") or s.startswith("flowchart"): continue
    m = re.match(r'subgraph\s+(\w+)\["(.*?)"\]$', s)
    if m: stack.append(m.group(1)); nodes[m.group(1)] = dict(kind="subgraph", title=m.group(2)); continue
    if s == "end": stack.pop(); continue
    m = re.match(r'(\w+)(\[\(|\(\(|\[)"(.*?)"(\)\]|\)\)|\]):::(\w+)$', s)
    if m:
        nodes[m.group(1)] = dict(kind=m.group(5), text=m.group(3)); member[m.group(1)] = list(stack); continue
    m = re.match(r'(\w+)\s+(-\.->|---|~~~)(?:\|(.+?)\|)?\s+(\w+)$', s)
    if m: edges.append((m.group(1), m.group(2), m.group(3), m.group(4))); continue
    bad("діаграма: не розпізнано рядок «%s»" % s)
if any(e[1] == "~~~" for e in edges):
    bad("діаграма: приховані зв'язки (~~~) змінюють шари й роблять розкладку нестабільною")

model_nodes = set(comp) | set(ports) | set(ifaces)
diagram_nodes = {k for k, v in nodes.items() if v["kind"] != "subgraph"}
for x in sorted(diagram_nodes - model_nodes): bad("на діаграмі є елемент %s, якого немає в моделі" % x)
for x in sorted(model_nodes - diagram_nodes): bad("елемент моделі %s відсутній на діаграмі" % x)
d_req = {(a, b) for a, t, l, b in edges if t == "-.->" and l == "requires"}
d_use = {(a, b) for a, t, l, b in edges if t == "-.->" and not l}
d_line = {(a, b) for a, t, l, b in edges if t == "---"}
m_req, m_use = {tuple(x) for x in model["requires"]}, {tuple(x) for x in model["uses"]}
m_line = {tuple(x) for x in model["provides"]} | {tuple(x) for x in model["delegations"]}
for name, d, mm in (("requires", d_req, m_req), ("uses", d_use, m_use), ("provided/delegation", d_line, m_line)):
    for e in sorted(d - mm): bad("на діаграмі є зв'язок %s %s→%s, якого немає в моделі" % (name, *e))
    for e in sorted(mm - d): bad("зв'язок моделі %s %s→%s відсутній на діаграмі" % (name, *e))

# ---------- межа системи і шари ----------
for cid, c in comp.items():
    path = member.get(cid, [])
    inside = "SYS" in path
    if c["layer"] == "external" and inside: bad("%s: зовнішня система всередині межі" % cid)
    if c["layer"] != "external" and not inside: bad("%s: внутрішній компонент поза межею системи" % cid)
    if c["container"] == "BE" and "BE" not in path: bad("%s: має бути всередині Gradebook Backend" % cid)
    if c["container"] == "BE":
        want = "шар " + c["layer"]
        if not any(nodes[g]["title"] == want for g in path if g in nodes and nodes[g]["kind"] == "subgraph"):
            bad("%s: не в підграфі «%s»" % (cid, want))
for iid, i in ifaces.items():
    inside = "SYS" in member.get(iid, [])
    ext = comp[i["provider_component"]]["layer"] == "external"
    if ext and inside: bad("%s: інтерфейс зовнішньої системи всередині межі" % iid)
    if not ext and not inside: bad("%s: інтерфейс внутрішнього компонента поза межею" % iid)
for pid in ports:
    if "BE" not in member.get(pid, []): bad("порт %s не належить Gradebook Backend" % pid)
for a, b in model["uses"]:
    if a in comp and b in comp:
        da, db = LAYERS.index(comp[a]["layer"]), LAYERS.index(comp[b]["layer"])
        if db - da != 1: bad("залежність %s→%s між нечільними шарами (%s→%s): змішаний варіант архітектури" % (a, b, comp[a]["layer"], comp[b]["layer"]))

# ---------- інтерфейси і порти ----------
def components_behind(src):
    if src in comp: return {src}
    out = {a for a, b in model["uses"] if b == src and a in comp}
    out |= {a for a, b in model["delegations"] if b == src and a in comp}
    out |= {b for a, b in model["delegations"] if a == src and b in comp}
    return out


for iid, i in ifaces.items():
    provs = [a for a, b in model["provides"] if a == iid]
    if len(provs) != 1: bad("%s: має бути один постачальник" % iid)
    reqs = [a for a, b in model["requires"] if b == iid]
    if not reqs: bad("%s: немає споживача (required)" % iid)
    consumers = set().union(*[components_behind(r) for r in reqs]) if reqs else set()
    if consumers != set(i["consumers"]): bad("%s: споживачі на діаграмі %s ≠ у моделі %s" % (iid, sorted(consumers), sorted(i["consumers"])))
    if not i["ops"]: bad("%s: не визначено операції інтерфейсу" % iid)
    pc = comp[i["provider_component"]]
    for c in i["consumers"]:
        if comp[c]["container"] == pc["container"] and pc["layer"] != "external" and pc["container"] is not None:
            bad("%s: lollipop усередині одного модуля (%s і %s): має бути звичайна залежність" % (iid, pc["id"], c))
for pid, p in ports.items():
    touching = [i for i in ifaces if (i, pid) in m_line or (pid, i) in m_req]
    if len(touching) != 1: bad("порт %s: має з'єднуватися рівно з одним зовнішнім інтерфейсом" % pid)
    if not components_behind(pid): bad("порт %s: немає внутрішнього компонента за портом" % pid)

# ---------- трасування ----------
er_text = er_src[er_src.index("erDiagram"):]
entities = set(re.findall(r"^\s*(\w+)\s*\{", er_text, re.M))
seq_blocks = "\n".join(re.findall(r"```mermaid\n(.*?)```", seq_md, re.S))
alias = {a: l.strip() for a, l in re.findall(r"(?:actor|participant)\s+(\w+)\s+as\s+(.+)", seq_blocks)}
seq_labels = set(alias.values())
root = ET.parse(BPMN).getroot()
M = "http://www.omg.org/spec/BPMN/20100524/MODEL"
bpmn_names = {e.get("name") for e in root.iter("{%s}lane" % M)} | {e.get("name") for e in root.iter("{%s}dataObject" % M)}
bpmn_msgs = {e.get("name") for e in root.iter("{%s}message" % M)}
reqs_defined = set(re.findall(r"\b((?:REQ|NFR)-\d+)", uc_md))
req_traced = set()
for cid, c in comp.items():
    t = c["trace"]
    if not any(t.values()): bad("%s: немає трасування до попередніх моделей" % cid)
    for e in t["er"]:
        if e not in entities: bad("%s: сутності %s немає в ER" % (cid, e))
    for r in t["req"]:
        req_traced.add(r)
        if r not in reqs_defined: bad("%s: вимоги %s немає в use-cases.md" % (cid, r))
    for u in t["uc"]:
        if u not in uc_md: bad("%s: UC «%s» немає в use-cases.md" % (cid, u))
    for sname in t["sequence"]:
        if sname not in seq_labels: bad("%s: учасника sequence %s немає в sequence-diagrams.md" % (cid, sname))
    for bname in t["bpmn"]:
        if bname not in bpmn_names: bad("%s: «%s» немає в process.bpmn" % (cid, bname))
    for a in t["assumptions"]:
        if not re.search(r"\b%s\b" % a, spec_md): bad("%s: припущення %s не описане в spec.md" % (cid, a))
    for a in t["adr"]:
        if a.replace(" п. ", ", п. ") not in uc_md and a not in spec_md: bad("%s: посилання %s не знайдено" % (cid, a))
for r in sorted(reqs_defined - req_traced): bad("вимога %s не покрита жодним компонентом" % r)
for lbl in sorted(seq_labels):
    if lbl in ("Викладач", "Студент"): continue
    if not any(lbl in c["trace"]["sequence"] for c in comp.values()): bad("учасник sequence %s не відображений компонентом" % lbl)
lanes = {e.get("name") for e in root.iter("{%s}lane" % M)}
actors = set(re.findall(r"\(\[(.+?)\]\)", uc_md))      # люди: лейн актора лишається поза системою
for l in sorted(lanes):
    if l not in {c["name"] for c in comp.values()} and l not in actors: bad("лейн BPMN %s не є ні компонентом, ні актором" % l)
for mname in sorted(bpmn_msgs):
    if mname not in arch.split("## 7.")[1].split("## 8.")[0]: bad("повідомлення BPMN %s не відображено в architecture.md (розділ 7)" % mname)

# ---------- виклики Sequence і BPMN ↔ операції ----------
alias_comp = {"GradebookUI": "UI", "GradeService": "GS", "LESSON": "LR", "STUDENT": "SR", "GRADE": "GR"}
for a, b, op in re.findall(r"^\s*(\w+)->>[+-]?(\w+):\s*(\w+)\(", seq_blocks, re.M):
    la, lb = alias.get(a), alias.get(b)
    if la is None or lb is None: continue
    if la in ("Викладач", "Студент"):
        if op not in comp["UI"]["ops"]: bad("виклик %s (актор → UI) відсутній серед операцій GradebookUI" % op)
    else:
        c = comp.get(alias_comp.get(lb))
        if not c or op not in c["ops"]: bad("виклик %s→%s: операції %s немає в компоненті %s" % (la, lb, op, lb))
pub = set(comp["GS"]["ops"]) | set(comp["IA"]["ops"])
for op in ifaces["IApi"]["ops"]:
    if op not in pub: bad("операції %s інтерфейсу IGradebookApi немає в компонентах-реалізаторах" % op)
all_ops = set().union(*[set(c["ops"]) for c in comp.values()])
for e in root.iter("{%s}serviceTask" % M):
    d = e.findtext("{%s}documentation" % M) or ""
    m = re.search(r"seq:\s*([^;]+)", d)
    if m:
        for tok in [t.strip().split()[0] for t in m.group(1).split(",") if t.strip()]:
            if tok != "par" and tok not in all_ops: bad("BPMN %s: операції %s немає в компонентах" % (e.get("id"), tok))
if "UI->>GS" in seq_md and any(c["layer"] == "API" for c in comp.values()) and not re.search(r"\bA5\b", spec_md):
    bad("між UI і GradeService є API Gateway, а Sequence викликає GradeService напряму (UI->>GS), і припущення A5 не описане в spec.md")
if "IA" in comp and "відомий із сесії" in seq_md and not re.search(r"\bA6\b", spec_md):
    bad("IdentityAdapter забезпечує «відомий із сесії» (Sequence, BPMN), але припущення A6 не описане в spec.md")

# ---------- дані ----------
if set(comp["DB"]["trace"]["er"]) != entities: bad("Gradebook DB має містити всі сутності ER: %s" % ", ".join(sorted(entities - set(comp["DB"]["trace"]["er"]))))
writers = set()
for c in comp.values():
    if c["layer"] == "Data Access" and any(o.startswith(WRITE_PREFIX) for o in c["ops"]): writers |= set(c["trace"]["er"])
ref = {r["entity"]: r for r in model.get("reference_data", [])}
nowriter = sorted(entities - writers)
missing = [e for e in nowriter if e not in ref]
if missing: bad("сутності %s система не записує, а джерело їхніх даних не визначено (потрібні довідкові дані з обґрунтуванням)" % ", ".join(missing))
for e, r in ref.items():
    if e in writers: bad("довідкова сутність %s має операцію запису" % e)
    if not re.search(r"\b%s\b" % r["assumption"], spec_md): bad("довідкові дані %s: припущення %s не описане в spec.md" % (e, r["assumption"]))
for ex in model["excluded"]:
    if ex["name"] not in uc_md: bad("явно виключена система %s не згадана в use-cases.md" % ex["name"])
if "Email" in uc_md and not any("Email" in ex["name"] for ex in model["excluded"]): bad("Email-сервіс із Завдання 2 не показано ні як інтеграцію, ні як виключений")
for e in model["external"]:
    if e["id"] not in comp or comp[e["id"]]["layer"] != "external": bad("зовнішня інтеграція %s не позначена як external" % e["id"])
mq = model.get("message_queue")
if not mq or "needed" not in mq or not mq.get("why"): bad("не прийнято явного рішення про чергу повідомлень")

print("Компонентів: %d | портів: %d | інтерфейсів: %d | залежностей: %d | сутностей ER: %d | операцій у Sequence перевірено" % (len(comp), len(ports), len(ifaces), len(model["uses"]), len(entities)))
if problems:
    print("ПРОБЛЕМИ (%d):" % len(problems))
    for p in problems: print(" -", p)
    sys.exit(1)
print("OK: розбіжностей не знайдено")