# oimus-net-top

Source for the top page of <https://oimus.net/> — an AI news feed with a 3D card ring and a ticker.

## Layout

| Path | What |
|---|---|
| `site/index.html` | The top page. Upload this one file to the oimus.net document root. |
| `scripts/build_news.py` | Collects Japanese AI news from RSS/Atom feeds into `public/news-ja.json` (standard library only). |
| `.github/workflows/news.yml` | Runs the builder every 30 minutes and publishes `public/` to GitHub Pages. |

The page reads:

- Japanese news: `https://oimus1976.github.io/oimus-net-top/news-ja.json` (this repo's Pages)
- English news: Hacker News search API (Algolia), fetched directly by the browser

No PHP or other server-side code runs on oimus.net for this page.

## Local preview

```bash
python -I scripts/build_news.py
cp public/news-ja.json site/
cd site && python -m http.server 8000 --bind 127.0.0.1
```

On `127.0.0.1` / `localhost` the page reads `news-ja.json` next to itself instead of GitHub Pages.

## Feeds

ITmedia AI+, AINOW, Google News (「生成AI」search), Publickey and GIGAZINE (AI-related titles only). At most 8 items per feed, 30 items total, last 7 days.

## Setup notes

- Repository → Settings → Pages → Source: **GitHub Actions**.
- GitHub disables scheduled workflows in public repos after 60 days without activity; the daily `keepalive` job re-enables the workflow to prevent that.
