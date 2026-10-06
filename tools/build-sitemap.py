#!/usr/bin/env python3
"""Regenerate sitemap.xml from the pages that are actually in the site.

    python3 tools/build-sitemap.py                 # this site
    python3 tools/build-sitemap.py --root public   # a site that publishes a subfolder

Netlify runs this as the build command (see netlify.toml), so every push
ships a sitemap that matches the site: new pages appear, deleted pages drop
out, and each <lastmod> is the date of that page's last git commit.

Which pages are listed: every .html file under the publish root, except
  * 404.html (Netlify serves it for missing paths; it isn't a page),
  * anything robots.txt disallows (tools/, docs/ and so on),
  * pages with <meta name="robots" content="noindex">,
  * pages whose <link rel="canonical"> points at a different URL, which are
    duplicates by their own admission.

Why <lastmod> comes from git and not the file's modified time: a fresh clone
(which is what Netlify builds from) stamps every file with the clone time, so
mtime would claim every page changed on every deploy. Google stops trusting
<lastmod> on sites where it's consistently wrong. Git's commit date is the real
"when did this page last change". If history isn't available (a shallow clone
that can't be deepened), <lastmod> is left out rather than guessed.

Standard library only, Python 3.8+, so it runs on Netlify's build image with
no install step. Copy it into any static site as-is.
"""

import argparse
import os
import pathlib
import re
import subprocess
import sys
from xml.sax.saxutils import escape

SKIP_DIRS = {".git", "node_modules", ".netlify", "__pycache__"}


def git(*args, cwd):
    try:
        out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def ensure_history(repo):
    """Netlify may clone shallowly; one commit of history would date every
    page to the latest push. Deepen it once if so."""
    if git("rev-parse", "--is-shallow-repository", cwd=repo) == "true":
        print("sitemap: shallow clone, fetching full history for page dates")
        git("fetch", "--unshallow", "--quiet", cwd=repo)
    return git("rev-parse", "--is-shallow-repository", cwd=repo) != "true"


def base_url(root, given):
    """The site's public origin. Explicit flag, then Netlify's URL env var
    (the primary domain on production builds), then the Sitemap: line in
    robots.txt, then the home page's canonical."""
    if given:
        return given.rstrip("/")
    if os.environ.get("CONTEXT") == "production" and os.environ.get("URL"):
        return os.environ["URL"].rstrip("/")
    robots = root / "robots.txt"
    if robots.exists():
        m = re.search(r"(?im)^sitemap:\s*(https?://[^/\s]+)", robots.read_text())
        if m:
            return m.group(1)
    index = root / "index.html"
    if index.exists():
        m = re.search(r'<link[^>]+rel="canonical"[^>]+href="(https?://[^/"]+)', index.read_text())
        if m:
            return m.group(1)
    sys.exit("sitemap: can't tell the site's URL; pass --base https://example.com")


def disallowed(root):
    robots = root / "robots.txt"
    if not robots.exists():
        return []
    return [p.strip() for p in re.findall(r"(?im)^disallow:\s*(\S+)", robots.read_text())]


def page_url(base, rel):
    rel = rel.as_posix()
    if rel == "index.html":
        return base + "/"
    if rel.endswith("/index.html"):
        return base + "/" + rel[: -len("index.html")]
    return base + "/" + rel


def build(root, base, out):
    repo = git("rev-parse", "--show-toplevel", cwd=root)
    have_history = bool(repo) and ensure_history(repo)
    blocked = disallowed(root)

    entries = []
    for path in sorted(root.rglob("*.html")):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts) or rel.name == "404.html":
            continue
        if any(("/" + rel.as_posix()).startswith(b) for b in blocked if b != "/"):
            continue
        html = path.read_text(errors="replace")
        if re.search(r'<meta[^>]+name="robots"[^>]+content="[^"]*noindex', html, re.I):
            continue
        url = page_url(base, rel)
        canon = re.search(r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"', html)
        if canon and canon.group(1).rstrip("/") != url.rstrip("/"):
            continue
        lastmod = git("log", "-1", "--format=%cI", "--", str(path.resolve()), cwd=root)[:10] if have_history else ""
        entries.append((url, lastmod))

    # Home page first, then the rest alphabetically: stable output, so the
    # file only shows up in a diff when a page or a date really changed.
    entries.sort(key=lambda e: (e[0] != base + "/", e[0]))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, lastmod in entries:
        lines.append("  <url>")
        lines.append(f"    <loc>{escape(url)}</loc>")
        if lastmod:
            lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    out.write_text("\n".join(lines) + "\n")

    print(f"sitemap: wrote {len(entries)} pages to {out}" + ("" if have_history else " (no git history: lastmod omitted)"))
    for url, lastmod in entries:
        print(f"  {lastmod or '----------'}  {url}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=".", help="the publish directory (default: .)")
    ap.add_argument("--base", help="the site's origin, e.g. https://example.com")
    args = ap.parse_args()

    root = pathlib.Path(args.root).resolve()
    out = root / "sitemap.xml"
    try:
        build(root, base_url(root, args.base), out)
    except SystemExit:
        raise
    except Exception as exc:  # never fail a deploy over the sitemap
        if os.environ.get("NETLIFY"):
            print(f"sitemap: WARNING, generation failed ({exc!r}); keeping the committed sitemap.xml")
            return
        raise


if __name__ == "__main__":
    main()
