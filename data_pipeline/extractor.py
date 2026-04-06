from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from schemas import PageSection, RawDocument


NOISE_SELECTORS = [
    "nav",
    "footer",
    "aside",
    "script",
    "style",
    "noscript",
    ".menu",
    ".navigation",
    ".breadcrumbs",
    ".footer",
    ".site-header",
    ".sidebar",
    ".sharedaddy",
]


def _remove_noise(container: Tag) -> None:
    for selector in NOISE_SELECTORS:
        for node in container.select(selector):
            node.decompose()


def _content_root(soup: BeautifulSoup) -> Tag:
    return (
        soup.find("main")
        or soup.find("article")
        or soup.find(class_="entry-content")
        or soup.find(id="content")
        or soup.body
    )


def _text_from_block(tag: Tag) -> str:
    text = tag.get_text(" ", strip=True)
    return " ".join(text.split())


def _iter_content_blocks(root: Tag) -> Iterable[Tag]:
    return root.find_all(["h1", "h2", "h3", "h4", "p", "li", "td", "th"], recursive=True)


def derive_category(url: str, soup: BeautifulSoup) -> str:
    breadcrumb = soup.select(".breadcrumbs a, nav[aria-label='breadcrumb'] a")
    if breadcrumb:
        texts = [node.get_text(" ", strip=True) for node in breadcrumb if node.get_text(strip=True)]
        if len(texts) >= 2:
            return texts[-1]

    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if "resource-and-information-hub" in parts:
        index = parts.index("resource-and-information-hub")
        if index + 1 < len(parts):
            return parts[index + 1].replace("-", " ").title()
    return "Resource Hub"


def extract_document(url: str, html: str) -> RawDocument:
    soup = BeautifulSoup(html, "html.parser")
    root = _content_root(soup)
    _remove_noise(root)

    title = "Resource Hub"
    h1 = root.find(["h1", "title"])
    if h1:
        title = _text_from_block(h1)

    category = derive_category(url, soup)
    sections: list[PageSection] = []
    current_heading = title
    current_content: list[str] = []

    for element in _iter_content_blocks(root):
        if element.name in {"h1", "h2", "h3", "h4"}:
            if current_content:
                sections.append(
                    PageSection(heading=current_heading or "Overview", content=" ".join(current_content).strip())
                )
                current_content = []
            current_heading = _text_from_block(element)
            continue

        text = _text_from_block(element)
        if text:
            current_content.append(text)

    if current_content:
        sections.append(PageSection(heading=current_heading or "Overview", content=" ".join(current_content).strip()))

    if not sections:
        full_text = _text_from_block(root)
        sections = [PageSection(heading="Overview", content=full_text)]

    return RawDocument(url=url, title=title, category=category, sections=sections)
