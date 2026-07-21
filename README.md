# TMDB RSS Feeds über GitHub Pages

Drei automatisch aktualisierte RSS-Feeds aus TMDB-Daten:

- **kino_demnaechst.xml** – demnächst im Kino
- **neue_serien.xml** – neue Serien
- **film_news.xml** – Trending diese Woche

GitHub Actions baut die Feeds zweimal täglich neu, GitHub Pages liefert sie aus.
Alles kostenlos. Der TMDB-Key liegt sicher als *Secret*, nie im Code.

---

## Einrichtung (einmalig, ca. 5 Minuten)

**1. Repository anlegen**
Erstelle auf GitHub ein neues Repository, z. B. `tmdb-feeds` (public genügt).
Lade den kompletten Inhalt dieses Ordners hoch (per Web-Upload oder Git):

```
tmdb_rss.py
index.html
README.md
.github/workflows/build-feeds.yml
```

> Wichtig: Der Ordner `.github` beginnt mit einem Punkt. Beim Web-Upload
> alle Dateien inkl. Unterordner mit hochziehen; die Struktur muss erhalten bleiben.

**2. TMDB-Key als Secret hinterlegen**
Repository → **Settings** → **Secrets and variables** → **Actions** →
**New repository secret**
- Name: `TMDB_API_KEY`
- Secret: *dein TMDB-API-Key*

**3. GitHub Pages aktivieren**
Repository → **Settings** → **Pages** →
unter **Build and deployment** → **Source**: **GitHub Actions** auswählen.

**4. Workflow starten**
Reiter **Actions** → Workflow „Build & Deploy TMDB RSS Feeds" → **Run workflow**.
(Läuft danach automatisch bei jedem Push und zweimal täglich.)

---

## Deine drei Links

Nach dem ersten erfolgreichen Lauf erreichbar unter:

```
https://<DEIN-BENUTZERNAME>.github.io/<REPO-NAME>/kino_demnaechst.xml
https://<DEIN-BENUTZERNAME>.github.io/<REPO-NAME>/neue_serien.xml
https://<DEIN-BENUTZERNAME>.github.io/<REPO-NAME>/film_news.xml
```

Die Übersichtsseite mit allen drei Links liegt unter
`https://<DEIN-BENUTZERNAME>.github.io/<REPO-NAME>/`.

Diese Links ins RSS-Widget einsetzen – sie sind dauerhaft und werden nicht gedrosselt.

---

## Anpassen

- **Sprache/Region**: in `tmdb_rss.py` oben `LANG` und `REGION` ändern.
- **Aktualisierungs-Rhythmus**: in `build-feeds.yml` die `cron`-Zeile anpassen
  (aktuell 06:00 und 18:00 UTC).
- **Serien-Zeitfenster**: in `feed_new_series()` die 90 Tage ändern.

Daten von The Movie Database (TMDB). Nutzt die TMDB-API, ist aber nicht von TMDB
unterstützt oder zertifiziert.
