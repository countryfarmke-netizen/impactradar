"""Impact Radar scraper. Standard library only. Run: python scrape.py"""
import json, re, hashlib, datetime as dt, urllib.request, xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import urljoin

CFG = json.load(open("config.json"))
OUT = "docs/data/opportunities.json"
UA = {"User-Agent": "ImpactRadar/1.0 (internal funding research; low-volume)"}
ATOM = "{http://www.w3.org/2005/Atom}"

def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25).read().decode("utf-8", "ignore")

def clean(s): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()

def from_rss(src):
    root, out = ET.fromstring(get(src["url"])), []
    for it in list(root.iter("item")) + list(root.iter(ATOM + "entry")):
        title = clean((it.findtext("title") or it.findtext(ATOM + "title") or ""))
        l = it.find("link") if it.find("link") is not None else it.find(ATOM + "link")
        link = (l.get("href") or l.text or "").strip() if l is not None else ""
        if "google.com/url" in link:  # unwrap Google Alerts redirect
            m = re.search(r"[?&]url=([^&]+)", link)
            link = urllib.request.unquote(m.group(1)) if m else link
        summ = clean(it.findtext("description") or it.findtext(ATOM + "summary") or it.findtext(ATOM + "content") or "")
        out.append((title, link, summ))
    return out

class Links(HTMLParser):
    def __init__(self, base): super().__init__(); self.base, self.cur, self.out = base, None, []
    def handle_starttag(self, t, a):
        if t == "a" and dict(a).get("href"): self.cur = [urljoin(self.base, dict(a)["href"]), ""]
    def handle_data(self, d):
        if self.cur: self.cur[1] += d
    def handle_endtag(self, t):
        if t == "a" and self.cur:
            if len(clean(self.cur[1])) > 25: self.out.append((clean(self.cur[1]), self.cur[0], ""))
            self.cur = None

def from_page(src):
    p = Links(src["url"]); p.feed(get(src["url"])); return p.out

def from_wb(src):
    data, out = json.loads(get(src["url"])), []
    for k, v in (data.get("procnotices") or {}).items():
        title = clean(v.get("bid_description") or v.get("project_name") or "")
        link = "https://projects.worldbank.org/en/projects-operations/procurement-detail/" + str(v.get("id", k))
        out.append((title, link, clean(f'{v.get("notice_type","")} deadline {v.get("submission_deadline_date","")}')))
    return out

def score(text):
    t = text.lower(); s = sum(w for k, w in CFG["themes"].items() if k in t)
    g = sum(w for k, w in CFG["geo_bonus"].items() if k in t)
    c = 2 if any(w in t for w in CFG["call_words"]) else 0
    return s + g + c if s else 0

try: old = {i["id"]: i for i in json.load(open(OUT))["items"]}
except Exception: old = {}
today, log = dt.date.today().isoformat(), []
for src in CFG["sources"]:
    if not src.get("enabled") or src["url"].startswith("PASTE"): continue
    try:
        rows = {"rss": from_rss, "page": from_page, "wb": from_wb}[src["type"]](src)
        n = 0
        for title, link, summ in rows:
            sc = score(title + " " + summ)
            if sc < CFG["min_score"] or not link: continue
            i = hashlib.md5(link.encode()).hexdigest()[:12]
            if i not in old: old[i] = {"id": i, "first_seen": today}; n += 1
            old[i].update(title=title[:200], link=link, source=src["name"], score=sc, summary=summ[:300])
        log.append(f'{src["name"]}: {len(rows)} read, {n} new')
    except Exception as e:
        log.append(f'{src["name"]}: FAILED ({type(e).__name__}: {e})')
items = sorted(old.values(), key=lambda x: (x["first_seen"], x["score"]), reverse=True)[:600]
json.dump({"updated": dt.datetime.utcnow().isoformat(timespec="minutes") + "Z", "log": log, "items": items}, open(OUT, "w"), indent=1)
print("\n".join(log))
