"""Minimal sitemap-driven crawler.

Reads sitemap.xml, fetches each <loc>, then follows internal <a href> links
one level deep. Reports status, title, and any 404s discovered.

Usage: python3 crawler.py [path-or-url-to-sitemap]
"""

import sys
import time
import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

USER_AGENT = "demo-crawler/0.1 (+https://shruti12229.github.io/shrutisri.github.io/)"
TIMEOUT = 10
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = None
        self._in_title = False
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        elif tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title and self.title is None:
            self.title = data.strip()


def load_sitemap(source):
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=TIMEOUT) as r:
            data = r.read()
    else:
        with open(source, "rb") as f:
            data = f.read()
    root = ET.fromstring(data)
    return [loc.text.strip() for loc in root.iter(f"{SITEMAP_NS}loc")]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read().decode("utf-8", errors="replace")
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return r.status, body, elapsed_ms, None
    except urllib.error.HTTPError as e:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return e.code, "", elapsed_ms, str(e)
    except Exception as e:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return None, "", elapsed_ms, str(e)


def is_internal(url, base):
    return urllib.parse.urlparse(url).netloc == urllib.parse.urlparse(base).netloc


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else "sitemap.xml"
    print(f"[crawler] sitemap: {source}\n")

    urls = load_sitemap(source)
    print(f"[crawler] {len(urls)} URL(s) in sitemap\n")

    sitemap_results = []
    discovered = {}

    for url in urls:
        status, body, ms, err = fetch(url)
        parser = PageParser()
        if body:
            parser.feed(body)
        sitemap_results.append((url, status, parser.title, ms, err))
        print(f"  [{status}] {url}  ({ms} ms)  title={parser.title!r}")

        for link in parser.links:
            absolute = urllib.parse.urljoin(url, link)
            absolute, _, _ = absolute.partition("#")
            if absolute and is_internal(absolute, url) and absolute not in discovered:
                discovered[absolute] = None

    print(f"\n[crawler] following {len(discovered)} discovered link(s) one level deep\n")
    broken = []
    for link in discovered:
        status, _, ms, err = fetch(link)
        discovered[link] = status
        marker = "OK " if status == 200 else "BAD"
        print(f"  {marker} [{status}] {link}  ({ms} ms)")
        if status != 200:
            broken.append((link, status, err))

    print("\n=== summary ===")
    print(f"sitemap URLs       : {len(urls)}")
    print(f"sitemap 200        : {sum(1 for r in sitemap_results if r[1] == 200)}")
    print(f"discovered links   : {len(discovered)}")
    print(f"broken links found : {len(broken)}")
    if broken:
        print("\nBroken:")
        for link, status, err in broken:
            print(f"  - [{status}] {link}  {err or ''}")


if __name__ == "__main__":
    main()
