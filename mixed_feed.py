#!/usr/bin/env python3
"""Kombi-Feed: Hessen-News + Bremen-News (buten un binnen) + Hundebilder -> public/hessen_laura_hunde.xml"""
import sys, os, re, json, hashlib
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

OUTDIR, OUTFILE = "public", "hessen_laura_hunde.xml"
HESSEN  = "https://www.hessenschau.de/index.rss"
BREMEN  = "https://www.butenunbinnen.de/feed/rss/nachrichten/neuste-nachrichten100.xml"
DOG_API = "https://dog.ceo/api/breeds/image/random/6"
NEWS_MAX = 8
IMG_RE = re.compile(r'<img[^>]+src="([^"]+)"', re.I)

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

def data_news(url, label, emoji, quelle):
    raw = http_get(url)
    if not raw: return []
    try: root = ET.fromstring(raw)
    except ET.ParseError: return []
    out = []
    for it in root.findall(".//item")[:NEWS_MAX]:
        title = (it.findtext("title") or "Ohne Titel").strip()
        link = (it.findtext("link") or "").strip()
        desc = (it.findtext("description") or "").strip()
        desc = re.sub(r"<[^>]+>", "", desc).strip()
        if len(desc) > 300: desc = desc[:300].rsplit(" ", 1)[0] + " \u2026"
        guid = f"{label}-" + hashlib.md5((link or title).encode()).hexdigest()[:12]
        img = find_image(it, it.findtext("description") or "") or f"https://picsum.photos/seed/{guid}/800/450"
        body = (f'<p><img src="{escape(img)}" alt=""/></p><p>{escape(desc)}</p>'
                f'<p><a href="{escape(link)}">Weiterlesen bei {quelle}</a></p>')
        out.append({"title": f"{emoji} [{label}] {title}", "link": link, "guid": guid, "body": body})
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
    hessen = data_news(HESSEN, "Hessen", "\U0001F5DE\uFE0F", "hessenschau.de")
    bremen = data_news(BREMEN, "Bremen", "\u2693", "butenunbinnen.de")
    ordered = interleave(hessen, bremen, data_dogs())
    base = now_utc()
    items = [render(e, base - timedelta(minutes=i)) for i, e in enumerate(ordered)]
    head = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">', "  <channel>",
            "    <title>Hessen, Bremen &amp; Hunde</title>",
            "    <link>https://www.hessenschau.de</link>",
            "    <description>News aus Hessen und Bremen sowie suesse Hundebilder</description>",
            "    <language>de-DE</language>", f"    <lastBuildDate>{rfc822(base)}</lastBuildDate>",
            "    <ttl>360</ttl>"]
    xml = "\n".join(head) + "\n" + "\n".join(items) + "\n  </channel>\n</rss>\n"
    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, OUTFILE), "w", encoding="utf-8") as f: f.write(xml)
    print(f"Fertig: {len(items)} Eintraege")

if __name__ == "__main__":
    build()
