#!/usr/bin/env python3
"""Crawl MII KDS specs into an Obsidian vault. Re-runnable mirror.

Sources:
  1. MII website KDS pages (basismodule + erweiterungsmodule overviews and the
     linked IG sites under /Kerndatensatz/), bounded BFS, HTML -> Markdown.
  2. Simplifier MII org page + its project listing (one level deep).

Output: knowledge/mii-kds/ Obsidian vault. Idempotent: re-crawls and overwrites,
writes per-source MOC index notes. Bounded by --max-pages / --depth with the cap
logged (no silent truncation). Polite: User-Agent + delay.

Usage:
  python3 scripts/update_mii_kds.py [--max-pages N] [--depth D] [--delay S]
"""
import argparse, re, sys, time, json
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

VAULT = Path(__file__).resolve().parent.parent / "knowledge" / "mii-kds"
UA = {"User-Agent": "genomDE2FHIR-kds-crawler/1.0 (+KohlbacherLab; research doc mirror)"}

MII_SEEDS = [
    "https://www.medizininformatik-initiative.de/de/basismodule-des-kerndatensatzes-der-mii",
    "https://www.medizininformatik-initiative.de/de/erweiterungsmodule-des-kerndatensatzes-der-mii",
    "https://www.medizininformatik-initiative.de/de/der-kerndatensatz-der-medizininformatik-initiative",
]
SIMPLIFIER_SEED = "https://simplifier.net/organization/koordinationsstellemii"

def slug(url):
    p = urlparse(url)
    s = (p.netloc + p.path).rstrip("/")
    if s.endswith(".html"):
        s = s[:-5]
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return s[:180] or "index"

def fetch(url):
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    ct = r.headers.get("content-type", "")
    if "html" not in ct and "xml" not in ct:
        raise ValueError(f"non-html ({ct})")
    if "charset" not in ct.lower():  # header omits charset -> requests guesses latin-1
        r.encoding = r.apparent_encoding or "utf-8"
    return r.text

def to_markdown(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "form", "noscript"]):
        tag.decompose()
    main = soup.select_one("main") or soup.select_one("article") or soup.body or soup
    title = (soup.title.get_text(strip=True) if soup.title else "").strip()
    h1 = main.find("h1")
    if h1 and h1.get_text(strip=True):
        title = h1.get_text(strip=True)
    body = md(str(main), heading_style="ATX", strip=["img"])
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return title or "Untitled", body

def in_scope_mii(url):
    p = urlparse(url)
    if not p.netloc.endswith("medizininformatik-initiative.de"):
        return False
    path = p.path.lower()
    return ("/kerndatensatz/" in path
            or "modul" in path
            or "kerndatensatz" in path)

def write_note(subdir, url, title, body, extra=None):
    d = VAULT / subdir
    d.mkdir(parents=True, exist_ok=True)
    fm = [f'title: "{title.replace(chr(34), chr(39))}"', f"source_url: {url}", "source: mii-kds-crawl"]
    if extra:
        fm += [f"{k}: {v}" for k, v in extra.items()]
    (d / f"{slug(url)}.md").write_text(
        "---\n" + "\n".join(fm) + "\n---\n\n" + body + f"\n\n---\n[Source]({url})\n")

def crawl_mii(max_pages, depth, delay):
    seen, ok, errors, order = set(), 0, [], []
    q = deque((u, 0) for u in MII_SEEDS)
    truncated = False
    while q:
        url, d = q.popleft()
        url = url.split("#")[0].rstrip("/")
        if url in seen:
            continue
        seen.add(url)
        if ok >= max_pages:
            truncated = True
            break
        try:
            html = fetch(url)
            title, body = to_markdown(html)
            write_note("mii-website", url, title, body, {"depth": d})
            order.append((title, url))
            ok += 1
            sys.stderr.write(f"[mii {ok}] d{d} {title[:60]}\n")
            if d < depth:
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.find_all("a", href=True):
                    nxt = urljoin(url, a["href"]).split("#")[0].rstrip("/")
                    if nxt not in seen and in_scope_mii(nxt):
                        q.append((nxt, d + 1))
            time.sleep(delay)
        except Exception as e:
            errors.append((url, str(e)))
    write_moc("mii-website", "MII KDS — Website & IGs", order, errors, truncated, max_pages)
    return ok, errors, truncated

def crawl_simplifier(max_pages, delay):
    seen, ok, errors, order = set(), 0, [], []
    truncated = False
    try:
        html = fetch(SIMPLIFIER_SEED)
        title, body = to_markdown(html)
        write_note("simplifier", SIMPLIFIER_SEED, title, body)
        order.append((title, SIMPLIFIER_SEED))
        ok += 1
        soup = BeautifulSoup(html, "html.parser")
        # project links: simplifier.net/<project> and /packages/<id>
        cand = set()
        for a in soup.find_all("a", href=True):
            full = urljoin(SIMPLIFIER_SEED, a["href"]).split("#")[0].split("?")[0].rstrip("/")
            pp = urlparse(full)
            if pp.netloc != "simplifier.net":
                continue
            parts = [x for x in pp.path.split("/") if x]
            if len(parts) == 1 and parts[0] not in ("organization", "login", "register", "guides", "packages"):
                cand.add(full)
            elif len(parts) >= 2 and parts[0] in ("packages", "guides"):
                cand.add(full)
        for url in sorted(cand):
            if ok >= max_pages:
                truncated = True
                break
            if url in seen:
                continue
            seen.add(url)
            try:
                t, b = to_markdown(fetch(url))
                write_note("simplifier", url, t, b)
                order.append((t, url))
                ok += 1
                sys.stderr.write(f"[simplifier {ok}] {t[:60]}\n")
                time.sleep(delay)
            except Exception as e:
                errors.append((url, str(e)))
    except Exception as e:
        errors.append((SIMPLIFIER_SEED, str(e)))
    write_moc("simplifier", "MII on Simplifier", order, errors, truncated, max_pages)
    return ok, errors, truncated

def write_moc(subdir, heading, order, errors, truncated, cap):
    lines = [f"# {heading}", "", f"_{len(order)} pages crawled._", ""]
    if truncated:
        lines.append(f"> ⚠️ Truncated at --max-pages={cap}. Raise the cap to crawl further.\n")
    for title, url in order:
        lines.append(f"- [[{slug(url)}|{title}]]")
    if errors:
        lines += ["", "## Errors", ""] + [f"- {u} — {e}" for u, e in errors]
    (VAULT / subdir / "_MOC.md").write_text("\n".join(lines) + "\n")

def write_root_index(stats):
    VAULT.mkdir(parents=True, exist_ok=True)
    (VAULT / "MII-KDS.md").write_text(
        "# MII Kerndatensatz — knowledge base\n\n"
        "Crawled mirror of the MII KDS specs. Re-run `update-mii-kds` to refresh.\n\n"
        "## Maps of content\n"
        "- [[_MOC|MII KDS — Website & IGs]] (`mii-website/`)\n"
        "- [[_MOC|MII on Simplifier]] (`simplifier/`)\n\n"
        f"## Last run\n```json\n{json.dumps(stats, indent=2)}\n```\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-pages", type=int, default=1200)
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("--delay", type=float, default=0.4)
    ap.add_argument("--only", choices=["mii", "simplifier"], help="crawl one source only")
    a = ap.parse_args()

    stats = {"max_pages": a.max_pages, "depth": a.depth}
    if a.only != "simplifier":
        n, err, trunc = crawl_mii(a.max_pages, a.depth, a.delay)
        stats["mii"] = {"pages": n, "errors": len(err), "truncated": trunc}
    if a.only != "mii":
        n, err, trunc = crawl_simplifier(a.max_pages, a.delay)
        stats["simplifier"] = {"pages": n, "errors": len(err), "truncated": trunc}
    write_root_index(stats)
    sys.stderr.write(f"\nDONE: {json.dumps(stats)}\nVault: {VAULT}\n")

if __name__ == "__main__":
    main()
