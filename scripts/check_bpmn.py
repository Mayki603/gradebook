#!/usr/bin/env python3
"""Перевірка BPMN-процесу (Завдання 4): типові помилки §10.13, узгодженість з ER, UC і Sequence, шляхи сценаріїв.

Запуск з кореня репозиторію:  scripts/check_bpmn.py
Читає: process.bpmn, process.md, sequence-diagrams.md, use-cases.md, spec.md, er-diagram.mmd (або DEFENSE.md).
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

BPMN, PROC, SEQ, UC, SPEC = "process.bpmn", "process.md", "sequence-diagrams.md", "use-cases.md", "spec.md"
ER = "er-diagram.mmd" if os.path.exists("er-diagram.mmd") else "DEFENSE.md"
M = "http://www.omg.org/spec/BPMN/20100524/MODEL"
DI = "http://www.omg.org/spec/BPMN/20100524/DI"
XSI = "{http://www.w3.org/2001/XMLSchema-instance}type"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def local(tag):
    return tag.split("}")[1]


problems = []
def bad(msg):
    problems.append(msg)


root = ET.parse(BPMN).getroot()
proc_md, seq_md, uc_md, spec_md, er_src = read(PROC), read(SEQ), read(UC), read(SPEC), read(ER)

# ---------- модель BPMN ----------
participants = {p.get("id"): (p.get("name"), p.get("processRef")) for p in root.iter("{%s}participant" % M)}
messages = {m.get("id"): m.get("name") for m in root.iter("{%s}message" % M)}
data_objects = {d.get("id"): d.get("name") for d in root.iter("{%s}dataObject" % M)}
mflows = {f.get("id"): (f.get("sourceRef"), f.get("targetRef")) for f in root.iter("{%s}messageFlow" % M)}
lanes = {}
nodes, seq = {}, {}
proc_of = {}
for p in root.iter("{%s}process" % M):
    pid = p.get("id")
    for lane in p.iter("{%s}lane" % M):
        lanes[lane.get("id")] = (lane.get("name"), pid, {r.text for r in lane.findall("{%s}flowNodeRef" % M)})
    for e in p:
        t = local(e.tag)
        if t.endswith("Task") or t.endswith("Event") or t.endswith("Gateway"):
            defs = [local(c.tag) for c in e if c.tag.endswith("EventDefinition")]
            doc = e.findtext("{%s}documentation" % M) or ""
            nodes[e.get("id")] = dict(id=e.get("id"), tag=t, name=e.get("name") or "", proc=pid, defs=defs, doc=doc,
                                      default=e.get("default"), msgref=e.get("messageRef"), incoming=[], outgoing=[], el=e)
            proc_of[e.get("id")] = pid
        elif t == "sequenceFlow":
            has_cond = e.find("{%s}conditionExpression" % M) is not None
            seq[e.get("id")] = dict(src=e.get("sourceRef"), dst=e.get("targetRef"), cond=has_cond, name=e.get("name") or "")
for fid, f in seq.items():
    if f["src"] in nodes: nodes[f["src"]]["outgoing"].append(fid)
    if f["dst"] in nodes: nodes[f["dst"]]["incoming"].append(fid)
shapes = {s.get("bpmnElement") for s in root.iter("{%s}BPMNShape" % DI)}
edges_di = {e.get("bpmnElement"): len(e.findall("{http://www.omg.org/spec/DD/20100524/DI}waypoint")) for e in root.iter("{%s}BPMNEdge" % DI)}
mf_from, mf_to = {}, {}
for fid, (s, t) in mflows.items():
    mf_from.setdefault(s, []).append(fid)
    mf_to.setdefault(t, []).append(fid)

# ---------- цілісність XML ----------
from collections import Counter
all_ids = Counter(e.get("id") for e in root.iter() if e.get("id"))
for i, c in all_ids.items():
    if c > 1: bad("id %s повторюється %d разів" % (i, c))
ref_attrs = ("sourceRef", "targetRef", "default", "messageRef", "dataObjectRef", "processRef", "bpmnElement")
for e in root.iter():
    for a in ref_attrs:
        v = e.get(a)
        if v and v not in all_ids: bad("%s: посилання %s=%s не існує" % (e.get("id") or local(e.tag), a, v))
    if local(e.tag) in ("incoming", "outgoing", "flowNodeRef", "sourceRef", "targetRef") and e.text and e.text.strip() not in all_ids:
        bad("посилання <%s>%s</%s> не існує" % (local(e.tag), e.text.strip(), local(e.tag)))

# ---------- E: типові помилки §10.13 ----------
for fid, f in seq.items():                                           # sequence flow між пулами
    if proc_of.get(f["src"]) != proc_of.get(f["dst"]):
        bad("sequence flow %s між пулами: між пулами лише message flow" % fid)
in_lane = set().union(*[r for _, _, r in lanes.values()])
for nid in nodes:                                                    # активність поза лейном
    if nid not in in_lane: bad("%s: активність поза лейном" % nid)
types = {n["tag"] for n in nodes.values() if n["tag"].endswith("Task")}
for need in ("manualTask", "userTask", "serviceTask"):               # усі кроки одного типу
    if need not in types: bad("немає задач типу %s (manual / user / service розрізняються)" % need)
excl = [n for n in nodes.values() if n["tag"] == "exclusiveGateway" and len(n["outgoing"]) > 1]
par = [n for n in nodes.values() if n["tag"] == "parallelGateway" and len(n["outgoing"]) > 1]
if not excl: bad("немає Exclusive Gateway")
if not par: bad("немає Parallel Gateway")
for g in excl:                                                       # вичерпність умов
    outs = g["outgoing"]
    noncond = [f for f in outs if not seq[f]["cond"]]
    if len(noncond) != 1 or g["default"] != noncond[0]:
        bad("%s: умови не вичерпні (потрібні умови на всіх гілках, крім однієї default)" % g["id"])


def first_merge(start_flow):
    """йдемо за потоком до першого шлюзу з кількома вхідними"""
    seen, stack = set(), [seq[start_flow]["dst"]]
    while stack:
        n = stack.pop()
        if n in seen or n not in nodes: continue
        seen.add(n)
        if nodes[n]["tag"].endswith("Gateway") and len(nodes[n]["incoming"]) > 1: return n
        stack += [seq[f]["dst"] for f in nodes[n]["outgoing"]]
    return None


joins = set()
for g in par:                                                        # парність і злиття не тим шлюзом
    targets = {first_merge(f) for f in g["outgoing"]}
    if len(targets) != 1 or None in targets:
        bad("%s: гілки Parallel Gateway не сходяться в одному шлюзі" % g["id"])
    else:
        j = targets.pop(); joins.add(j)
        if nodes[j]["tag"] != "parallelGateway": bad("%s: гілки parallel зведено не parallel-шлюзом (%s)" % (g["id"], j))
for n in nodes.values():
    if n["tag"] == "parallelGateway" and len(n["incoming"]) > 1 and n["id"] not in joins:
        bad("%s: Parallel-злиття без відповідного split" % n["id"])
for n in nodes.values():                                             # подія замість дії
    if n["tag"].endswith("Event") and n["name"] and not n["defs"]:
        first = n["name"].split()[0].lower()
        if first.endswith(("ти", "ть")): bad("%s: подія названа дією «%s»" % (n["id"], n["name"]))
for fid, (s, t) in mflows.items():                                   # повідомлення без отримувача
    if proc_of.get(s) == proc_of.get(t): bad("message flow %s усередині одного пулу" % fid)
for n in nodes.values():
    throws = n["tag"] == "sendTask" or (n["tag"] == "endEvent" and "messageEventDefinition" in n["defs"])
    catches = "messageEventDefinition" in n["defs"] and n["tag"] in ("startEvent", "intermediateCatchEvent")
    if throws and n["id"] not in mf_from: bad("%s: повідомлення без отримувача (немає message flow)" % n["id"])
    if catches and n["id"] not in mf_to: bad("%s: catching-подія без відправника" % n["id"])
for n in nodes.values():                                             # signal замість message
    if "signalEventDefinition" in n["defs"]: bad("%s: signal замість message" % n["id"])


def cycles():
    res, color = [], {}
    def dfs(u, stack):
        color[u] = 1
        for f in nodes[u]["outgoing"]:
            v = seq[f]["dst"]
            if v not in nodes: continue
            if color.get(v) == 1: res.append((u, v))
            elif v not in color: dfs(v, stack)
        color[u] = 2
    for n in nodes:
        if n not in color: dfs(n, [])
    return res


def reach_from(s):
    seen, st = set(), [s]
    while st:
        n = st.pop()
        if n in seen or n not in nodes: continue
        seen.add(n); st += [seq[f]["dst"] for f in nodes[n]["outgoing"]]
    return seen


for u, v in cycles():                                                # повторна задача без змін
    loop = {x for x in reach_from(v) if u in reach_from(x)}
    if not any(nodes[x]["tag"] in ("userTask", "manualTask") for x in loop):
        bad("цикл %s→%s без задачі підготовки: переробка має повертатися до підготовки" % (u, v))
    if nodes[v]["tag"] == "sendTask": bad("цикл повертається прямо до надсилання (%s)" % v)
if "```mermaid" in proc_md: bad("process.md містить другу нотацію (mermaid): має бути одна точна форма")
for n in nodes.values():                                             # рівень коду
    if n["tag"].endswith("Task") or n["tag"].endswith("Gateway"):
        if re.search(r"\w+\(\)|[a-z]+[A-Z][a-z]+|\bAPI\b|\bnull\b|\bSELECT\b|\bHTTP\b", n["name"]):
            bad("%s: назва «%s» на рівні коду, потрібен рівень бізнес-процесу" % (n["id"], n["name"]))

# ---------- повнота, досяжність, діаграма ----------
for nid, n in nodes.items():
    if nid not in shapes: bad("%s: немає фігури на діаграмі" % nid)
    if n["tag"] != "endEvent" and not n["outgoing"] and not mf_from.get(nid) and n["tag"] != "intermediateCatchEvent":
        bad("%s: немає виходу (дірка в переходах)" % nid)
for fid in list(seq) + list(mflows):
    if edges_di.get(fid, 0) < 2: bad("%s: немає лінії на діаграмі" % fid)
starts = {pid: [n["id"] for n in nodes.values() if n["proc"] == pid and n["tag"] == "startEvent"] for pid in {n["proc"] for n in nodes.values()}}
for pid, ss in starts.items():
    seen = set()
    for s in ss: seen |= reach_from(s)
    for nid, n in nodes.items():
        if n["proc"] == pid and nid not in seen: bad("%s: недосяжний у процесі %s" % (nid, pid))

# ---------- узгодженість з ER, UC, Sequence ----------
er_text = er_src[er_src.index("erDiagram"):]
entities = set(re.findall(r"^\s*(\w+)\s*\{", er_text, re.M))
seq_blocks = "\n".join(re.findall(r"```mermaid\n(.*?)```", seq_md, re.S))
seq_labels = {x.strip() for x in re.findall(r"(?:actor|participant)\s+\w+\s+as\s+(.+)", seq_blocks)}
seq_calls = set(re.findall(r"\b([A-Za-z][A-Za-z0-9]*)\(", seq_blocks))
actors = set(re.findall(r"\(\[(.+?)\]\)", uc_md))
allowed_lanes = actors | {l for l in seq_labels if l not in entities}
for lid, (name, _, _) in lanes.items():
    if name not in allowed_lanes: bad("лейн «%s» не є актором (Завдання 2) чи учасником sequence (Завдання 3)" % name)
for did, name in data_objects.items():
    if name not in entities: bad("Data Object «%s» відсутній серед сутностей ER" % name)
for mid, name in messages.items():
    if name not in seq_md: bad("повідомлення %s немає в sequence-діаграмах" % name)
req_found = set()
for n in nodes.values():
    m = re.search(r"seq:\s*([^;]+)", n["doc"])
    if m:
        for tok in [t.strip().split()[0] for t in m.group(1).split(",") if t.strip()]:
            if tok == "par":
                if not re.search(r"^\s*par\b", seq_blocks, re.M): bad("%s: у sequence немає фрагмента par" % n["id"])
            elif tok not in seq_calls:
                bad("%s: виклику %s немає в sequence-діаграмах" % (n["id"], tok))
    req_found |= set(re.findall(r"REQ-\d", n["doc"]))
uc1 = uc_md.split("### UC «Переглянути успішність»")[0]
for r in sorted(set(re.findall(r"\*\*(REQ-\d):", uc1)) - {"REQ-7"}):
    if r not in req_found: bad("%s не відображено в процесі" % r)

# ---------- шляхи ----------
m = re.search(r"```json\n(.*?)```", proc_md, re.S)
if not m:
    bad("process.md: немає JSON-блоку зі шляхами сценаріїв")
    cfg = {"scenarios": {}, "justified": []}
else:
    cfg = json.loads(m.group(1))
gherkin_ids = re.findall(r"#\s*(S\d+):", uc1.split("```gherkin")[1].split("```")[0]) if "```gherkin" in uc1 else []
SM = {f for f in mflows}


def simulate(decisions, drop):
    reached, arrivals, delivered, looped = set(), {}, set(), False
    queue = [n["id"] for n in nodes.values() if n["tag"] == "startEvent" and not n["defs"] and not n["incoming"]]
    waiting, steps = [], 0
    while queue or waiting:
        steps += 1
        if steps > 5000: raise RuntimeError("симуляція зациклилась")
        if queue:
            nid = queue.pop(0); n = nodes[nid]
            if n["tag"] == "parallelGateway" and len(n["incoming"]) > 1:
                arrivals[nid] = arrivals.get(nid, 0) + 1
                if arrivals[nid] < len(n["incoming"]): continue
            elif nid in reached:
                looped = True; continue
            reached.add(nid)
            if n["tag"] == "eventBasedGateway": waiting.append(nid); continue
            outs = n["outgoing"]
            if n["tag"] == "exclusiveGateway" and len(outs) > 1:
                chosen = [f for f in outs if f in decisions]
                if not chosen: return ("need", nid, list(outs))
                outs = [chosen[0]]
            for mf in mf_from.get(nid, []):
                if n["tag"] == "sendTask" and drop: continue
                delivered.add(mf)
                tgt = mflows[mf][1]
                if nodes[tgt]["tag"] == "startEvent": queue.append(tgt)
            queue += [seq[f]["dst"] for f in outs]
        else:
            g = waiting.pop(0)
            got = [f for f in nodes[g]["outgoing"] if any(mf in delivered for mf in mf_to.get(seq[f]["dst"], []))]
            timers = [f for f in nodes[g]["outgoing"] if "timerEventDefinition" in nodes[seq[f]["dst"]]["defs"]]
            pick = got[0] if got else (timers[0] if timers else None)
            if pick: queue.append(seq[pick]["dst"])
    return ("done", reached, looped)


def enumerate_paths():
    out = []
    def rec(dec, drop):
        r = simulate(dec, drop)
        if r[0] == "need":
            for f in r[2]: rec(dec | {f}, drop)
        else:
            out.append((frozenset(dec) | (frozenset({"DROP"}) if drop else frozenset()), r[1], r[2]))
    rec(frozenset(), False); rec(frozenset(), True)
    return out


all_paths = enumerate_paths()
sigs = {s for s, _, _ in all_paths}
covered = {}
for sid in gherkin_ids:
    if sid not in cfg["scenarios"]: bad("Gherkin-сценарій %s не має шляху на моделі" % sid)
for sid, sc in cfg["scenarios"].items():
    dec = frozenset(sc["decisions"])
    if sid not in gherkin_ids: bad("шлях %s не відповідає жодному Gherkin-сценарію UC" % sid)
    if dec not in sigs:
        bad("шлях %s: набір рішень не є повним шляхом моделі" % sid); continue
    covered[dec] = sid
    r = simulate(dec - {"DROP"}, "DROP" in dec)
    if r[0] != "done": bad("шлях %s: немає рішення для шлюзу %s" % (sid, r[1])); continue
    for x in sc.get("reach", []):
        if x not in r[1]: bad("шлях %s має досягати %s, але не досягає" % (sid, x))
    for x in sc.get("avoid", []):
        if x in r[1]: bad("шлях %s не має досягати %s (за Gherkin), але досягає" % (sid, x))
for j in cfg.get("justified", []):
    dec = frozenset(j["decisions"])
    if dec not in sigs: bad("обґрунтований шлях %s не є повним шляхом моделі" % j.get("id")); continue
    covered.setdefault(dec, j["id"])
    a = j.get("assumption")
    if a and a not in spec_md: bad("обґрунтування %s посилається на припущення %s, якого немає в spec.md" % (j["id"], a))
uncovered = sorted(sigs - set(covered), key=lambda s: sorted(s))
for s in uncovered:
    bad("шлях {%s} не має ні Gherkin-сценарію, ні обґрунтування" % ", ".join(sorted(s)))
if any("timerEventDefinition" in n["defs"] for n in nodes.values()) and "A3" not in spec_md:
    bad("у моделі є таймер (відповіді немає), але припущення A3 не описане в spec.md")

print("Лейни: %s | Data Objects: %s | повідомлення: %s" % (", ".join(sorted(n for n, _, _ in lanes.values())), ", ".join(sorted(set(data_objects.values()))), ", ".join(sorted(messages.values()))))
print("Шляхів моделі: %d | Gherkin-сценаріїв UC: %d (%s) | обґрунтованих: %d" % (len(sigs), len(gherkin_ids), ", ".join(gherkin_ids), len(cfg.get("justified", []))))
if problems:
    print("ПРОБЛЕМИ (%d):" % len(problems))
    for p in problems: print(" -", p)
    sys.exit(1)
print("OK: розбіжностей не знайдено")