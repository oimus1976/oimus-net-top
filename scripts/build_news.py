"""Collect Japanese AI news from RSS/Atom feeds into public/news-ja.json.

Standard library only, so the GitHub Actions job needs no dependencies.
A feed that fails to load is skipped; the job fails only if every feed fails.
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime
from html import unescape
from pathlib import Path

MAX_ITEMS = 30
PER_FEED = 8  # keep one busy feed (Google News) from crowding out the rest
MAX_AGE = 7 * 86400  # ignore items older than a week
OUT = Path(__file__).resolve().parent.parent / "public" / "news-ja.json"

# (source name, url, filter) — filter: keep only titles that look AI-related
FEEDS = [
    ("ITmedia AI+", "https://rss.itmedia.co.jp/rss/2.0/aiplus.xml", False),
    ("AINOW", "https://ainow.ai/feed/", False),
    ("Google News", "https://news.google.com/rss/search?q=%E7%94%9F%E6%88%90AI&hl=ja&gl=JP&ceid=JP:ja", False),
    ("Publickey", "https://www.publickey1.jp/atom.xml", True),
    ("GIGAZINE", "https://gigazine.net/news/rss_2.0/", True),
]

AI_PATTERN = re.compile(
    r"(?<![A-Za-z])(AI|ＡＩ|AGI|LLM|GPT|ChatGPT|OpenAI|Anthropic|Claude|Gemini|Copilot|DeepMind|Llama|MCP)(?![A-Za-z])"
    r"|人工知能|生成|機械学習|深層学習|ディープラーニング|エージェント|大規模言語モデル"
)

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "dc": "http://purl.org/dc/elements/1.1/",
    "rss1": "http://purl.org/rss/1.0/",
}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "oimus.net news builder (+https://oimus.net/)"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()


def clean(s: str | None) -> str:
    s = re.sub(r"<[^>]+>", "", s or "")
    return re.sub(r"\s+", " ", unescape(s)).strip()


def parse_date(s: str | None) -> int | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return int(parsedate_to_datetime(s).timestamp())  # RFC 822 (RSS 2.0)
    except (TypeError, ValueError):
        pass
    try:
        return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())  # ISO 8601
    except ValueError:
        return None


def entries(root: ET.Element):
    """Yield (title, link, date) for RSS 2.0, RSS 1.0 and Atom."""
    for it in root.iter("item"):  # RSS 2.0
        yield it.findtext("title"), it.findtext("link"), it.findtext("pubDate") or it.findtext("dc:date", namespaces=NS)
    for it in root.iter(f"{{{NS['rss1']}}}item"):  # RSS 1.0
        yield it.findtext("rss1:title", namespaces=NS), it.findtext("rss1:link", namespaces=NS), it.findtext("dc:date", namespaces=NS)
    for e in root.iter(f"{{{NS['atom']}}}entry"):  # Atom
        href = ""
        for l in e.findall("atom:link", NS):
            if l.get("rel") in (None, "alternate"):
                href = l.get("href", "")
                break
        yield e.findtext("atom:title", namespaces=NS), href, e.findtext("atom:published", namespaces=NS) or e.findtext("atom:updated", namespaces=NS)


def parse_feed(xml: bytes, source: str, filt: bool, now: int) -> list[dict]:
    out = []
    for title, link, date in entries(ET.fromstring(xml)):
        title, link, ts = clean(title), (link or "").strip(), parse_date(date)
        if not title or not re.match(r"https?://", link) or ts is None or now - ts > MAX_AGE:
            continue
        item_source = source
        # Google News titles end with " - <publisher>"
        if source == "Google News" and (m := re.match(r"^(.*) - ([^-]+)$", title)):
            title, item_source = m[1].strip(), m[2].strip()
        if filt and not AI_PATTERN.search(title):
            continue
        out.append({"title": title, "url": link, "source": item_source, "ts": ts})
    return out


def main() -> int:
    now = int(time.time())
    items, ok = [], 0
    for name, url, filt in FEEDS:
        try:
            got = sorted(parse_feed(fetch(url), name, filt, now), key=lambda it: it["ts"], reverse=True)
            ok += 1
            print(f"{name}: {len(got)} items")
            items += got[:PER_FEED]
        except Exception as e:  # one broken feed must not take down the rest
            print(f"{name}: skipped ({e})", file=sys.stderr)
    if not ok:
        print("all feeds failed", file=sys.stderr)
        return 1

    items.sort(key=lambda it: it["ts"], reverse=True)
    seen, unique = set(), []
    for it in items:
        key = re.sub(r"\s+", "", it["title"])[:40]
        if key not in seen:
            seen.add(key)
            unique.append(it)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"updated": now, "items": unique[:MAX_ITEMS]}, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {min(len(unique), MAX_ITEMS)} items to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
