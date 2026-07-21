#!/usr/bin/env python3
"""Kombi-Feed mit Hintergrundbildern, abwechselnd sortiert -> public/hessen_laura_hunde.xml"""
import sys, os, re, json, hashlib
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

OUTDIR, OUTFILE = "public", "hessen_laura_hunde.xml"
HESSEN  = "https://www.hessenschau.de/index.rss"
DOG_API = "https://dog.ceo/api/breeds/image/random/6"
NEWS_MAX = 8
IMG_RE = re.compile(r'<img[^>]+src="([^"]+)"', re.I)

LAURA_FACTS = [
    "Der Name Laura kommt vom lateinischen \u201elaurus\u201c \u2013 dem Lorbeer.",
    "Ein Lorbeerkranz stand in der Antike f\u00fcr Sieg, Ruhm und Ehre.",
    "Sinngem\u00e4\u00df bedeutet Laura \u201edie Lorbeerbekr\u00e4nzte\u201c oder \u201edie Siegreiche\u201c.",
    "Laura ist die weibliche Form zu Namen wie Laurus und Laurentius.",
    "Ber\u00fchmt wurde der Name durch Petrarcas Laura, der er \u00fcber 300 Gedichte widmete.",
    "Die heilige Laura von C\u00f3rdoba gab dem Namen einen Gedenktag: den 19. Oktober.",
    "In Deutschland war Laura in den 1990er- und 2000er-Jahren sehr beliebt.",
    "Laura ist international fast \u00fcberall gleich geschrieben.",
    "Beliebte Koseformen sind Lara, Lauri, Laurita und Lore.",
    "Der Lorbeer war dem Gott Apollon geweiht (Daphne-Mythos).",
    "Vom Lorbeer (bacca lauri) leitet sich der Grad \u201eBakkalaureus\u201c ab.",
    "Ein \u201ePoeta laureatus\u201c war ein lorbeergekr\u00f6nter Dichter \u2013 dieselbe Wurzel wie Laura.",
    "Betont wird Laura fast \u00fcberall auf der ersten Silbe: LAU-ra.",
    "Weil Lorbeer immergr\u00fcn ist, galt er als Zeichen f\u00fcr Best\u00e4ndigkeit.",
    "Der Name gilt als zeitlos \u2013 klassisch, aber nie altmodisch.",
]
LAURA_PER_DAY = 5

def now_utc(): return datetime.now(timezone.utc)
def rfc822(dt): return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
def cdata(t): return t.replace("]]>", "]]&gt;")

def http_get(url, as_json=False):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (RSS-Builder)"})
    try:
        with urlopen(req, timeout=30) as r: raw = r.read()
        return json.loads(raw) if as_json else raw
    except (HTTPError, URLError, json.JSONDecodeError) as e:
        print(f"  ! Fehler ({url}): {e}", file=sys.stderr); return None

def find_image(item, desc):
    cands = [(e.get("url",""), (e.get("type") or "").lower()) for e in item.findall("enclosure")]
    for el in item.iter():
        tag = el.tag.split("}")[-1].lower()
        if tag in ("content","thumbnail","image") and el.get("url"):
            cands.append((el.get("url"), (el.get("type") or "").lower()))
    for url, typ in cands:
        u = url.lower().split("?")[0]
        if "image" in typ or u.endswith((".jpg",".jpeg",".png",".webp",".gif")):
            return url
    m = IMG_RE.search(desc or "")
    return m.group(1) if m else None

def data_hessen():
    raw = http_get(HESSEN)
    if not raw: return []
    try: root = ET.fromstring(raw)
    except ET.ParseError: return []
    out = []
    for it in root.findall(".//item")[:NEWS_MAX]:
        title = (it.findtext("title") or "Ohne Titel").strip()
        link = (it.findtext("link") or "").strip()
        desc = (it.findtext("description") or "").strip()
        if len(desc) > 300: desc = desc[:300].rsplit(" ", 1)[0] + " \u2026"
        guid = "hessen-" + hashlib.md5((link or title).encode()).hexdigest()[:12]
        img = find_image(it, desc) or f"https://picsum.photos/seed/{guid}/800/450"
        body = (f'<p><img src="{escape(img)}" alt=""/></p><p>{escape(desc)}</p>'
                f'<p><a href="{escape(link)}">Weiterlesen bei hessenschau.de</a></p>')
        out.append({"title": f"\U0001F5DE\uFE0F [Hessen] {title}", "link": link, "guid": guid, "body": body})
    return out

def data_laura():
    seed = int(now_utc().strftime("%Y%m%d")); n = len(LAURA_FACTS)
    seen, chosen = set(), []
    for i in range(LAURA_PER_DAY):
        p = (seed + i * 7) % n
        while p in seen: p = (p + 1) % n
        seen.add(p); chosen.append(LAURA_FACTS[p])
    today = now_utc().strftime("%Y%m%d"); out = []
    for i, f in enumerate(chosen, 1):
        img = f"https://picsum.photos/seed/laura{today}{i}/800/450"
        body = f'<p><img src="{escape(img)}" alt=""/></p><p>{escape(f)}</p>'
        out.append({"title": f"\u2728 Laura: {f}", "link": None, "guid": f"laura-{today}-{i}", "body": body})
    return out

def data_dogs():
    data = http_get(DOG_API, as_json=True)
    if not data or data.get("status") != "success": return []
    out = []
    for i, url in enumerate(data.get("message", []), 1):
        out.append({"title": f"\U0001F436 S\u00fc\u00dfer Hund #{i}", "link": url,
                    "guid": "dog-" + hashlib.md5(url.encode()).hexdigest()[:12],
                    "body": f'<p><img src="{escape(url)}" alt="Suesser Hund"/></p>'})
    return out

def interleave(*lists):
    pools, result, i = [list(l) for l in lists], [], 0
    while any(pools):
        pool = pools[i % len(pools)]
        if pool: result.append(pool.pop(0))
        i += 1
    return result

def render(e, pub_dt):
    lines = ["    <item>", f"      <title>{escape(e['title'])}</title>"]
    if e["link"]: lines.append(f"      <link>{escape(e['link'])}</link>")
    lines += [f'      <guid isPermaLink="false">{escape(e["guid"])}</guid>',
              f"      <description><![CDATA[{cdata(e['body'])}]]></description>",
              f"      <pubDate>{rfc822(pub_dt)}</pubDate>", "    </item>"]
    return "\n".join(lines)

def build():
    ordered = interleave(data_hessen(), data_laura(), data_dogs())
    base = now_utc()
    items = [render(e, base - timedelta(minutes=i)) for i, e in enumerate(ordered)]
    head = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">', "  <channel>",
            "    <title>Hessen, Laura &amp; Hunde</title>",
            "    <link>https://www.hessenschau.de</link>",
            "    <description>Hessen-News, Fun Facts zu Laura und suesse Hundebilder</description>",
            "    <language>de-DE</language>", f"    <lastBuildDate>{rfc822(base)}</lastBuildDate>",
            "    <ttl>360</ttl>"]
    xml = "\n".join(head) + "\n" + "\n".join(items) + "\n  </channel>\n</rss>\n"
    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, OUTFILE), "w", encoding="utf-8") as f: f.write(xml)
    print(f"Fertig: {len(items)} Eintraege")

if __name__ == "__main__":
    build()
