#!/usr/bin/env python3
"""
TMDB -> RSS Feed Generator (GitHub-Pages-Variante)
==================================================
Erzeugt drei RSS-2.0-Feeds im Ordner ./public/ :

  public/kino_demnaechst.xml  - Demnaechst erscheinende Kinofilme  (/movie/upcoming)
  public/neue_serien.xml      - Neue Serien der letzten ~90 Tage   (/discover/tv)
  public/film_news.xml        - Trending diese Woche (News-Ersatz)  (/trending/all/week)

Der TMDB-API-Key wird AUSSCHLIESSLICH aus der Umgebungsvariable
TMDB_API_KEY gelesen - niemals hier eintragen. In GitHub liegt er
als "Repository Secret".
"""

import os
import sys
import json
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode
from xml.sax.saxutils import escape

API_KEY = os.environ.get("TMDB_API_KEY")
BASE    = "https://api.themoviedb.org/3"
IMG     = "https://image.tmdb.org/t/p/w500"
SITE    = "https://www.themoviedb.org"
LANG    = "de-DE"
REGION  = "DE"
OUTDIR  = "public"

if not API_KEY:
    sys.exit("Fehler: Umgebungsvariable TMDB_API_KEY ist nicht gesetzt.")


# --------------------------------------------------------------------------- #
def tmdb_get(path, params=None):
    p = dict(params or {})
    p.setdefault("language", LANG)
    p["api_key"] = API_KEY
    url = f"{BASE}{path}?{urlencode(p)}"
    req = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=30) as r:
            return json.load(r)
    except (HTTPError, URLError) as e:
        print(f"  ! Abruf fehlgeschlagen ({path}): {e}", file=sys.stderr)
        return {"results": []}


def rfc822(dt):
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def parse_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def cdata(text):
    return text.replace("]]>", "]]&gt;")


def make_item(title, link, guid, overview, poster_path, pub_dt, extra_html=""):
    body = []
    if poster_path:
        body.append(f'<img src="{IMG}{poster_path}" alt="{escape(title)}"/>')
    if overview:
        body.append(f"<p>{overview}</p>")
    if extra_html:
        body.append(extra_html)
    description = cdata("".join(body) or "Keine Beschreibung verfuegbar.")

    lines = [
        "    <item>",
        f"      <title>{escape(title)}</title>",
        f"      <link>{escape(link)}</link>",
        f'      <guid isPermaLink="false">{escape(guid)}</guid>',
        f"      <description><![CDATA[{description}]]></description>",
    ]
    if pub_dt:
        lines.append(f"      <pubDate>{rfc822(pub_dt)}</pubDate>")
    lines.append("    </item>")
    return "\n".join(lines)


def build_feed(filename, title, link, description, items):
    now = rfc822(datetime.now(timezone.utc))
    head = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "  <channel>",
        f"    <title>{escape(title)}</title>",
        f"    <link>{escape(link)}</link>",
        f"    <description>{escape(description)}</description>",
        "    <language>de-DE</language>",
        f"    <lastBuildDate>{now}</lastBuildDate>",
        "    <ttl>360</ttl>",
    ]
    xml = "\n".join(head) + "\n" + "\n".join(items) + "\n  </channel>\n</rss>\n"
    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(OUTDIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"  -> {path} ({len(items)} Eintraege)")


# --------------------------------------------------------------------------- #
def feed_upcoming():
    data = tmdb_get("/movie/upcoming", {"region": REGION, "page": 1})
    results = sorted(data.get("results", []), key=lambda m: m.get("release_date") or "9999")
    items = []
    for m in results:
        title = m.get("title") or m.get("original_title") or "Unbenannt"
        rd = m.get("release_date")
        extra = f"<p><strong>Kinostart:</strong> {rd}</p>" if rd else ""
        items.append(make_item(title, f"{SITE}/movie/{m['id']}", f"tmdb-movie-{m['id']}",
                                m.get("overview", ""), m.get("poster_path"), parse_date(rd), extra))
    build_feed("kino_demnaechst.xml", "Demnaechst im Kino", f"{SITE}/movie/upcoming",
               "Demnaechst erscheinende Kinofilme - Daten von TMDB", items)


def feed_new_series():
    today = datetime.now(timezone.utc)
    since = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    data = tmdb_get("/discover/tv", {
        "sort_by": "popularity.desc",
        "first_air_date.gte": since,
        "first_air_date.lte": today.strftime("%Y-%m-%d"),
        "vote_count.gte": 5,
        "page": 1,
    })
    items = []
    for s in data.get("results", []):
        title = s.get("name") or s.get("original_name") or "Unbenannt"
        fad = s.get("first_air_date")
        extra = f"<p><strong>Erstausstrahlung:</strong> {fad}</p>" if fad else ""
        items.append(make_item(title, f"{SITE}/tv/{s['id']}", f"tmdb-tv-{s['id']}",
                                s.get("overview", ""), s.get("poster_path"), parse_date(fad), extra))
    build_feed("neue_serien.xml", "Neue Serien", f"{SITE}/tv",
               "Neu gestartete Serien der letzten Wochen - Daten von TMDB", items)


def feed_news():
    data = tmdb_get("/trending/all/week")
    now = datetime.now(timezone.utc)
    items = []
    for x in data.get("results", []):
        media = x.get("media_type")
        if media not in ("movie", "tv"):
            continue
        title = x.get("title") or x.get("name") or "Unbenannt"
        kind = "Film" if media == "movie" else "Serie"
        items.append(make_item(f"[{kind}] {title}", f"{SITE}/{media}/{x['id']}",
                                f"tmdb-trend-{media}-{x['id']}", x.get("overview", ""),
                                x.get("poster_path"), now,
                                f"<p><strong>Bewertung:</strong> {x.get('vote_average', '-')}/10</p>"))
    build_feed("film_news.xml", "Film-News: Trending diese Woche", f"{SITE}",
               "Die angesagtesten Filme & Serien der Woche - Daten von TMDB", items)


if __name__ == "__main__":
    print("Generiere TMDB-RSS-Feeds ...")
    feed_upcoming()
    feed_new_series()
    feed_news()
    print("Fertig.")
