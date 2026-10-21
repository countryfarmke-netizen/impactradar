"""Impact Radar v2: active opportunities only, contacts, Google Sheet push. Stdlib only."""
import json, os, re, hashlib, datetime as dt, urllib.request, xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import urljoin, unquote

CFG = json.load(open("config.json")); OUT = "docs/data/opportunities.json"
UA = {"User-Agent": "ImpactRadar/2.0 (internal funding research; low-volume)"}
ATOM = "{http://www.w3.org/2005/Atom}"; TODAY = dt.date.today()
CALL = re.compile(r"call for (proposals?|applications?|expressions?)|expressions? of interest|request for (proposals?|applications?|quotations?)|\b(rfp|rfq|eoi)\b|tender|invitation to bid|apply (now|by|before)|applications? (are )?(open|invited)|(grant|funding) opportunit|deadline|closing date", re.I)
NEWS = re.compile(r"\b(helped|success stor\w*|stor(y|ies)|awarded|winners?|celebrat\w*|interview|case study|supports?|empower(s|ed)|transform(s|ed))\b", re.I)
MON = {m[:3]: i for i, m in enumerate("january february march april may june july august september october november december".split(), 1)}

def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25).read().decode("utf-8", "ignore")
def clean(s): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()
def mk(y, m, d):
    try: return dt.date(int(y), int(m), int(d))
    except (ValueError, TypeError): return None
def dates(t):
    o = [mk(y, MON.get(m[:3].lower()), d) for d, m, y in re.findall(r"(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?([A-Za-z]{3,9})\.?,?\s+(20\d\d)", t)]
    o += [mk(y, MON.get(m[:3].lower()), d) for m, d, y in re.findall(r"([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d\d)", t)]
    o += [mk(y, m, d) for y, m, d in re.findall(r"(20\d\d)-(\d\d)-(\d\d)", t)]
    o += [mk(y, m, d) for d, m, y in re.findall(r"(\d{1,2})[./](\d{1,2})[./](20\d\d)", t)]
    return [x for x in o if x]
def deadline(t):
    for m in re.finditer(r"(deadline|closing date|closes?|apply (?:by|before)|submission|due (?:date|on|by)|no later than|until)", t, re.I):
        ds = dates(t[m.end():m.end() + 90])
        if ds: return ds[0]
def emails(t):
    e = [x.strip(".").lower() for x in re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", t) if not re.search(r"noreply|no-reply|example\.|\.(png|jpe?g|gif|webp)$", x, re.I)]
    return list(dict.fromkeys(e))[:3]
def kind(t):
    t = t.lower()
    return "RFP" if re.search(r"tender|rfp|rfq|invitation to bid", t) else "EOI" if "expression" in t else "Grant"

def from_rss(src):
    root, out = ET.fromstring(get(src["url"])), []
    for it in list(root.iter("item")) + list(root.iter(ATOM + "entry")):
        title = clean(it.findtext("title") or it.findtext(ATOM + "title") or "")
        l = it.find("link") if it.find("link") is not None else it.find(ATOM + "link")
        link = ((l.get("href") or l.text or "").strip()) if l is not None else ""
        if "google.com/url" in link:
            m = re.search(r"[?&]url=([^&]+)", link); link = unquote(m.group(1)) if m else link
        out.append((title, link, clean(it.findtext("description") or it.findtext(ATOM + "summary") or it.findtext(ATOM + "content") or "")))
    return out
class Links(HTMLParser):
    def __init__(self, base): super().__init__(); self.base, self.cur, self.out = base, None, []
    def handle_starttag(self, t, a):
        if t == "a" and dict(a).get("href"): self.cur = [urljoin(self.base, dict(a)["href"]), ""]
    def handle_data(self, d):
        if self.cur: self.cur[1] += " " + d
    def handle_endtag(self, t):
        if t == "a" and self.cur:
            if len(clean(self.cur[1]).split()) >= 6: self.out.append((clean(self.cur[1]), self.cur[0], ""))
            self.cur = None
def from_page(src): p = Links(src["url"]); p.feed(get(src["url"])); return p.out
def from_wb(src):
    out, pn = [], json.loads(get(src["url"])).get("procnotices") or []
    for k, v in (pn.items() if isinstance(pn, dict) else enumerate(pn)):
        out.append((clean(v.get("bid_description") or v.get("project_name") or ""), "https://projects.worldbank.org/en/projects-operations/procurement-detail/" + str(v.get("id", k)),
                    clean(f'tender {v.get("notice_type","")} deadline {v.get("submission_deadline_date","")}')))
    return out
def score(t):
    t = t.lower(); s = sum(w for k, w in CFG["themes"].items() if k in t)
    return s + sum(w for k, w in CFG["geo_bonus"].items() if k in t) if s else 0

try: prev = json.load(open(OUT))
except Exception: prev = {}
old = {i["id"]: i for i in prev.get("items", []) if i.get("v") == 2}
LANES = CFG["lanes"]
def lanes_of(t): t = t.lower(); return [n for n, l in LANES.items() if any(k in t for k in l["keywords"])]
def funders_in(t): t = t.lower(); return [f for f in CFG["funders"] if f.lower() in t]
sigs = {s["id"]: s for s in prev.get("signals", [])}
def signal(i, title, link, summ, src):  # news, awards, announcements: early hints of where money is moving
    ln = lanes_of(title + " " + summ)
    if ln and i not in sigs: sigs[i] = {"id": i, "date": TODAY.isoformat(), "title": title, "link": link, "source": src["name"], "lanes": ln, "funders": funders_in(title + " " + summ) or ([src["name"]] if src["name"] in CFG["funders"] else [])}
def trends(items):
    age = lambda s: (TODAY - dt.date.fromisoformat(s["date"])).days
    keep = sorted((s for s in sigs.values() if age(s) <= 120), key=lambda s: s["date"], reverse=True)[:1500]; out = []
    for n, l in LANES.items():
        a = [s for s in keep if n in s["lanes"] and age(s) <= 30]; b = [s for s in keep if n in s["lanes"] and 30 < age(s) <= 60]
        calls = sum(1 for x in items if n in x.get("lanes", [])); fc = {}
        for s in a + b:
            for f in s["funders"]: fc[f] = fc.get(f, 0) + 1
        out.append({"lane": n, "signals_30d": len(a), "signals_prev30d": len(b), "open_calls": calls, "top_funders": sorted(fc, key=fc.get, reverse=True)[:3],
                    "pitch": len(a) >= CFG.get("pitch_min_signals", 3) and calls <= 1, "asset": l["asset"]})
    return keep, out
log, fresh, budget = [], [], CFG.get("max_detail_fetch", 40)
for src in CFG["sources"]:
    if not src.get("enabled") or src["url"].startswith("PASTE"): continue
    try:
        rows = {"rss": from_rss, "page": from_page, "wb": from_wb}[src["type"]](src); n = 0
        for title, link, summ in rows:
            title = re.sub(r"(.{30,}?)\s+\1", r"\1", title)[:200]
            sc = score(title + " " + summ); i = hashlib.md5(link.encode()).hexdigest()[:12]
            if not link or sc < CFG["min_score"] or i in old or budget <= 0: continue
            if NEWS.search(title) and not CALL.search(title): signal(i, title, link, summ, src); continue
            text = ""
            try: text = "" if link.lower().endswith(".pdf") else clean(get(link))[:60000]
            except Exception: pass
            budget -= 1; blob = f"{title} {summ} {text}"
            if not CALL.search(blob): signal(i, title, link, summ, src); continue
            dl = deadline(blob)
            if dl and dl < TODAY: continue
            old[i] = {"id": i, "v": 2, "first_seen": TODAY.isoformat(), "title": title, "link": link, "source": src["name"], "score": sc,
                      "deadline": dl.isoformat() if dl else "", "contacts": emails(text), "kind": kind(blob), "lanes": lanes_of(blob), "funders": funders_in(blob)}
            fresh.append(old[i]); n += 1
        log.append(f'{src["name"]}: {len(rows)} read, {n} new active')
    except Exception as e: log.append(f'{src["name"]}: FAILED ({type(e).__name__}: {e})')

def active(x):
    if x["deadline"]: return dt.date.fromisoformat(x["deadline"]) >= TODAY
    return (TODAY - dt.date.fromisoformat(x["first_seen"])).days <= CFG.get("stale_days", 45)
items = sorted((x for x in old.values() if active(x)), key=lambda x: (x["deadline"] or "9999", -x["score"]))[:600]
hook = os.environ.get("SHEET_WEBHOOK")
push = [x for x in fresh if x["score"] >= CFG.get("push_min_score", 8)]
if hook and push:
    try:
        body = json.dumps({"token": os.environ.get("SHEET_TOKEN", ""), "items": push}).encode()
        log.append("Sheet: " + urllib.request.urlopen(urllib.request.Request(hook, body, {"Content-Type": "application/json"}), timeout=30).read().decode()[:120])
    except Exception as e: log.append(f"Sheet push FAILED ({e})")
keep, tr = trends(items)
json.dump({"updated": dt.datetime.utcnow().isoformat(timespec="minutes") + "Z", "log": log, "items": items, "signals": keep, "trends": tr}, open(OUT, "w"), indent=1)
print("\n".join(log))
