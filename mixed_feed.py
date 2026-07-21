#!/usr/bin/env python3
"""Kombi-Feed: Hessen-News + Laura-Fun-Facts + suesse Hundebilder -> public/hessen_laura_hunde.xml"""
import sys, os, json, hashlib
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

OUTDIR, OUTFILE = "public", "hessen_laura_hunde.xml"
HESSEN  = "https://www.hessenschau.de/index.rss"
DOG_API = "https://dog.ceo/api/breeds/image/random/6"
NEWS_MAX = 8

LAURA_FACTS = [
    "Der Name Laura kommt vom lateinischen \u201elaurus\u201c \u2013 dem Lorbeer.",
    "Ein Lorbeerkranz stand in der Antike f\u00fcr Sieg, Ruhm und Ehre \u2013 Laura tr\u00e4gt das bis heute in sich.",
    "Sinngem\u00e4\u00df bedeutet Laura \u201edie Lorbeerbekr\u00e4nzte\u201c oder \u201edie Siegreiche\u201c.",
    "Laura ist die weibliche Form zu Namen wie Laurus und Laurentius.",
    "Ber\u00fchmt wurde der Name durch Petrarcas Laura, der er im 14. Jahrhundert \u00fcber 300 Gedichte widmete.",
    "Die heilige Laura von C\u00f3rdoba gab dem Namen einen Gedenktag: den 19. Oktober.",
    "In Deutschland war Laura besonders in den 1990er- und 2000er-Jahren sehr beliebt.",
    "Laura ist international: In Deutsch, Englisch, Italienisch und Spanisch fast identisch geschrieben.",
    "Beliebte Koseformen sind Lara, Lauri, Laurita und Lore.",
    "In der griechischen Mythologie war der Lorbeer dem Gott Apollon geweiht (Daphne-Mythos).",
    "Vom Lorbeer (bacca lauri) leitet sich der akademische Grad \u201eBakkalaureus\u201c ab.",
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
        with urlopen(req, timeout=30) as r:
            raw = r.read()
        return json.loads(raw) if as_json else raw
    except (HTTPError, URLError, json.JSONDecodeError) as e:
        print(f"  ! Fehler ({url}): {e}", file=sys.stderr)
        return None

def make_item(title, link, guid, body, pub_dt):
    lines = ["    <item>", f"      <title>{escape(title)}</title>"]
    if link: lines.append(f"      <link>{escape(link)}</link>")
    lines += [f'      <guid isPermaLink="false">{escape(guid)}</guid>',
              f"      <description><![CDATA[{cdata(body)}]]></description>",
              f"      <pubDate>{rfc822(pub_dt)}</pubDate>", "    </item>"]
    return "\n".join(lines)

def items_hessen():
    raw = http_get(HESSEN)
    if not raw: return []
    try: root = ET.fromstring(raw)
    except ET.ParseError: return []
    out = []
    from email.utils import parsedate_to_datetime
    for it in root.findall(".//item")[:NEWS_MAX]:
        title = (it.findtext("title") or "Ohne Titel").strip()
        link = (it.findtext("link") or "").strip()
        desc = (it.findtext("description") or "").strip()
        if len(desc) > 300: desc = desc[:300].rsplit(" ", 1)[0] + " \u2026"
        pub = it.findtext("pubDate")
        try:
            pub_dt = parsedate_to_datetime(pub) if pub else now_utc()
            if pub_dt.tzinfo is None: pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError): pub_dt = now_utc()
        body = f'<p>{escape(desc)}</p><p><a href="{escape(link)}">Weiterlesen bei hessenschau.de</a></p>'
        guid = "hessen-" + hashlib.md5((link or title).encode()).hexdigest()[:12]
        out.append(make_item(f"\U0001F5DE\uFE0F [Hessen] {title}", link, guid, body, pub_dt))
    return out

def items_laura():
    seed = int(now_utc().strftime("%Y%m%d")); n = len(LAURA_FACTS)
    seen, chosen = set(), []
    for i in range(LAURA_PER_DAY):
        p = (seed + i * 7) % n
        while p in seen: p = (p + 1) % n
        seen.add(p); chosen.append(LAURA_FACTS[p])
    today = now_utc().strftime("%Y%m%d")
    return [make_item(f"\u2728 [Laura] Fun Fact #{i}", None, f"laura-{today}-{i}",
                      f"<p>{escape(f)}</p>", now_utc()) for i, f in enumerate(chosen, 1)]

def items_dogs():
    data = http_get(DOG_API, as_json=True)
    if not data or data.get("status") != "success": return []
    out = []
    for i, url in enumerate(data.get("message", []), 1):
        body = f'<p><img src="{escape(url)}" alt="Suesser Hund"/></p>'
        guid = "dog-" + hashlib.md5(url.encode()).hexdigest()[:12]
        out.append(make_item(f"\U0001F436 S\u00fc\u00dfer Hund #{i}", url, guid, body, now_utc()))
    return out

def build():
    items = items_hessen() + items_laura() + items_dogs()
    head = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">', "  <channel>",
            "    <title>Hessen, Laura &amp; Hunde</title>",
            "    <link>https://www.hessenschau.de</link>",
            "    <description>Hessen-News, Fun Facts zu Laura und suesse Hundebilder</description>",
            "    <language>de-DE</language>", f"    <lastBuildDate>{rfc822(now_utc())}</lastBuildDate>",
            "    <ttl>360</ttl>"]
    xml = "\n".join(head) + "\n" + "\n".join(items) + "\n  </channel>\n</rss>\n"
    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, OUTFILE), "w", encoding="utf-8") as f: f.write(xml)
    print(f"Fertig: {len(items)} Eintraege")

if __name__ == "__main__":
    build()
