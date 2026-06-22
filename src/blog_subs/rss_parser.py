"""Unified RSS/Atom feed parser for blog subscriptions."""
from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from typing import Optional

import requests
from loguru import logger

from src.blog_subs.models import BlogPost

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
)
TIMEOUT = 20

# Source configuration
RSS_SOURCES = [
    {
        "name": "ruanyifeng",
        "url": "https://www.ruanyifeng.com/blog/atom.xml",
        "label": "阮一峰周刊",
    },
    {
        "name": "sebastian",
        "url": "https://magazine.sebastianraschka.com/feed",
        "label": "Sebastian Raschka",
    },
    {
        "name": "lilianweng",
        "url": "https://lilianweng.github.io/index.xml",
        "label": "Lilian Weng",
    },
]


def _parse_date(date_str: str) -> Optional[str]:
    """Parse various date formats to YYYY-MM-DD."""
    if not date_str:
        return None
    try:
        # Try ISO 8601 first
        if "T" in date_str:
            return date_str[:10]
        # RFC 2822 (used by RSS 2.0)
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        # Fallback: just take first 10 chars
        return date_str[:10] if len(date_str) >= 10 else None


def fetch_rss_feed(url: str) -> list[dict]:
    """Fetch and parse an RSS/Atom feed. Returns list of raw dicts."""
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT, verify=False)
    if resp.status_code != 200:
        logger.warning(f"RSS fetch failed: {url} (HTTP {resp.status_code})")
        return []

    root = ET.fromstring(resp.text)

    items = []

    # Try Atom namespace first
    atom_ns = {"atom": "http://www.w3.org/2005/Atom"}
    atom_entries = root.findall("atom:entry", atom_ns)

    if atom_entries:
        # Atom format (阮一峰)
        for entry in atom_entries:
            title = entry.findtext("atom:title", "", atom_ns).strip()
            link_el = entry.find("atom:link", atom_ns)
            url_entry = link_el.get("href", "") if link_el is not None else ""
            published = _parse_date(entry.findtext("atom:published", "", atom_ns))
            summary = entry.findtext("atom:summary", "", atom_ns)[:300]
            items.append({
                "title": title,
                "url": url_entry,
                "date": published,
                "summary": summary,
            })
        return items

    # Try RSS 2.0 format (Substack, Hugo)
    rss_items = root.findall(".//item")
    if rss_items:
        for item in rss_items:
            title = (item.findtext("title") or "").strip()
            url_entry = (item.findtext("link") or "").strip()
            pub_date = _parse_date(item.findtext("pubDate") or "")
            description = (item.findtext("description") or "")[:300]
            items.append({
                "title": title,
                "url": url_entry,
                "date": pub_date,
                "summary": description,
            })
        return items

    logger.warning(f"No entries found in RSS feed: {url}")
    return []


def fetch_all_feeds(max_per_source: int = 10) -> list[BlogPost]:
    """Fetch all configured RSS feeds and return unified BlogPost list."""
    all_posts = []

    for source in RSS_SOURCES:
        logger.info(f"Fetching RSS: {source['label']} ({source['url']})")
        try:
            items = fetch_rss_feed(source["url"])
            for item in items[:max_per_source]:
                if not item.get("url") or not item.get("title"):
                    continue

                # Create unique slug from URL path
                from urllib.parse import urlparse
                path = urlparse(item["url"]).path.rstrip("/")
                slug_part = path.split("/")[-1] if path else item["title"]
                slug = f"{source['name']}:{slug_part}"

                post = BlogPost(
                    source=source["name"],
                    slug=slug,
                    url=item["url"],
                    title=item["title"],
                    date=item.get("date"),
                    source_label=source["label"],
                    summary=item.get("summary"),
                )
                all_posts.append(post)

            logger.info(f"  {source['label']}: {len(items)} posts found")
        except Exception as e:
            logger.warning(f"  {source['label']}: fetch failed: {e}")

        # Be polite between feeds
        if source != RSS_SOURCES[-1]:
            time.sleep(0.5)

    logger.info(f"All RSS feeds: {len(all_posts)} total posts")
    return all_posts
