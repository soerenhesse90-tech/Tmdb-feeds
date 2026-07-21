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
    "Vom Lorbeer (bac
