from __future__ import annotations

import logging
import time
from collections import deque
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from config import ScraperConfig
from exceptions import ScrapingError


LOGGER = logging.getLogger(__name__)

DISALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".pdf", ".zip", ".doc", ".docx")
DISALLOWED_PATH_KEYWORDS = ("/tag/", "/author/", "/feed/", "/wp-json/", "/search/")
ALLOWED_PATH_PREFIXES = (
    "/international-student-services",
    "/events",
    "/event/",
)


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    cleaned = parsed._replace(fragment="", query="")
    normalized = urlunparse(cleaned).rstrip("/")
    return normalized


def _build_robot_parser(start_url: str) -> tuple[RobotFileParser, bool]:
    parsed = urlparse(start_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        parser.read()
        return parser, True
    except Exception:  # noqa: BLE001
        LOGGER.warning("Could not load robots.txt from %s; falling back to allowlist checks.", robots_url)
        return parser, False


def _is_allowed(url: str, config: ScraperConfig, parser: RobotFileParser, robots_loaded: bool) -> bool:
    parsed = urlparse(url)
    if parsed.netloc != config.allowed_domain:
        return False
    if not parsed.path.startswith(ALLOWED_PATH_PREFIXES):
        return False
    if any(parsed.path.lower().endswith(ext) for ext in DISALLOWED_EXTENSIONS):
        return False
    if any(keyword in parsed.path.lower() for keyword in DISALLOWED_PATH_KEYWORDS):
        return False
    return parser.can_fetch(config.user_agent, url) if robots_loaded else True


def _extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    content_root = soup.find("main") or soup.find("article") or soup.body
    if content_root is None:
        return []

    links: list[str] = []
    for anchor in content_root.find_all("a", href=True):
        href = anchor["href"].strip()
        if href.startswith(("mailto:", "tel:", "#", "javascript:", "webcal:")):
            continue
        resolved = _normalize_url(urljoin(base_url, href))
        scheme = urlparse(resolved).scheme
        if scheme not in {"http", "https"}:
            continue
        links.append(resolved)
    return links


def crawl_site(config: ScraperConfig) -> dict[str, str]:
    parser, robots_loaded = _build_robot_parser(config.start_url)
    session = requests.Session()
    session.headers.update({"User-Agent": config.user_agent})

    visited: set[str] = set()
    pages: dict[str, str] = {}
    seed_urls = [_normalize_url(config.start_url), *[_normalize_url(url) for url in config.extra_seed_urls]]
    queue: deque[str] = deque(dict.fromkeys(seed_urls))

    while queue and len(pages) < config.max_pages:
        url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        if not _is_allowed(url, config, parser, robots_loaded):
            LOGGER.info("Skipping disallowed URL: %s", url)
            continue

        try:
            response = session.get(url, timeout=config.timeout_seconds)
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.warning("Failed to fetch %s: %s", url, exc)
            continue

        if "text/html" not in response.headers.get("content-type", ""):
            continue

        html = response.text
        pages[url] = html
        LOGGER.info("Fetched %s (%d/%d)", url, len(pages), config.max_pages)

        for discovered_url in _extract_links(html, url):
            if discovered_url not in visited and _is_allowed(discovered_url, config, parser, robots_loaded):
                queue.append(discovered_url)

        time.sleep(config.delay_seconds)

    if not pages:
        raise ScrapingError("Crawler did not fetch any pages. Check network access and robots.txt constraints.")

    return pages
