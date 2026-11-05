#!/usr/bin/env python3
"""
Socrates Mode source checker.

Independently downloads every cited page and checks that the quoted text
really appears on it. The model does not grade its own homework: this
script does the fetching and matching, and its output is shown to the user.

Usage:
    python3 verify_sources.py sources.json
    python3 verify_sources.py sources.json --json    # machine-readable output

sources.json is a list of objects:
    [
      {"id": 1, "claim": "short claim", "url": "https://...", "quote": "exact words from the page"},
      ...
    ]

Statuses:
    PASS       page opened and the quote was found on it
    PARTIAL    page opened, a close but not exact match was found
    FAIL       page did not open (404, bad domain) or the quote is not on it
    UNCHECKED  could not check: blocked for bots, paywall, PDF without a reader,
               or no network access (turn on "Allow network egress")

Only the Python standard library is used, so it runs anywhere.
"""
import difflib
import html
import io
import json
import re
import socket
import ssl
import sys
import unicodedata
import urllib.error
import urllib.request
from html.parser import HTMLParser

TIMEOUT = 20
MAX_BYTES = 8 * 1024 * 1024
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 SocratesModeSourceCheck/1.0")
PASS_RATIO = 0.92
PARTIAL_RATIO = 0.75


class _Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        # meta descriptions often hold the abstract on journal pages
        if tag == "meta":
            a = dict(attrs)
            if a.get("content") and (a.get("name", "") + a.get("property", "")).lower().find("description") >= 0:
                self.parts.append(" " + a["content"] + " ")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        if tag in ("p", "div", "li", "br", "h1", "h2", "h3", "h4", "tr", "td", "section"):
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def normalize(s):
    s = unicodedata.normalize("NFKC", html.unescape(s)).lower()
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = re.sub(r"[‐-―−]", "-", s)
    s = re.sub(r"[^\w%.,;:'\"\-/ ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def pdf_text(data):
    for mod in ("pypdf", "PyPDF2"):
        try:
            lib = __import__(mod)
            reader = lib.PdfReader(io.BytesIO(data))
            return " ".join((p.extract_text() or "") for p in reader.pages[:60])
        except ImportError:
            continue
        except Exception:
            return None
    return None


def fetch(url):
    """Returns (text, http_status, error_kind, detail)."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ssl.create_default_context()) as r:
            status = r.status
            ctype = (r.headers.get("Content-Type") or "").lower()
            data = r.read(MAX_BYTES)
            final_url = r.geturl()
    except urllib.error.HTTPError as e:
        kind = "blocked" if e.code in (401, 402, 403, 406, 429, 451, 503) else "http"
        return None, e.code, kind, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        reason = e.reason
        if isinstance(reason, (socket.gaierror, ConnectionRefusedError, socket.timeout, TimeoutError, OSError)):
            text = str(reason)
            if "Name or service not known" in text or "nodename nor servname" in text or "No address associated" in text:
                return None, None, "dns", "domain not found or no network"
            return None, None, "network", text[:80]
        return None, None, "network", str(reason)[:80]
    except (socket.timeout, TimeoutError):
        return None, None, "network", "timed out"
    except Exception as e:  # noqa: BLE001
        return None, None, "network", type(e).__name__

    if "pdf" in ctype or final_url.lower().endswith(".pdf") or data[:5] == b"%PDF-":
        text = pdf_text(data)
        if text is None:
            return None, status, "pdf", "PDF, no reader installed (pip install pypdf)"
        return text, status, None, "PDF"

    charset = "utf-8"
    m = re.search(r"charset=([\w-]+)", ctype)
    if m:
        charset = m.group(1)
    raw = data.decode(charset, errors="replace")
    p = _Text()
    try:
        p.feed(raw)
        text = " ".join(p.parts)
    except Exception:  # noqa: BLE001
        text = re.sub(r"<[^>]+>", " ", raw)
    return text, status, None, ""


def best_match(quote_n, page_n):
    """Exact substring first, then a fuzzy sliding window over words."""
    if not quote_n:
        return 0.0, ""
    if quote_n in page_n:
        return 1.0, quote_n
    q = quote_n.split()
    words = page_n.split()
    if not words:
        return 0.0, ""
    n = len(q)
    best, best_txt = 0.0, ""
    qset = set(q)
    step = max(1, n // 4)
    for size in (n, max(1, n - 1), n + 1, n + 2):
        for i in range(0, max(1, len(words) - size + 1), step):
            window = words[i:i + size]
            if len(qset.intersection(window)) < 0.5 * len(qset):
                continue
            r = difflib.SequenceMatcher(None, q, window).ratio()
            if r > best:
                best, best_txt = r, " ".join(window)
    return best, best_txt


def check(item):
    url = (item.get("url") or "").strip()
    quote = (item.get("quote") or "").strip()
    res = {"id": item.get("id"), "claim": item.get("claim", ""), "url": url, "quote": quote}
    if not url.startswith(("http://", "https://")):
        return {**res, "status": "FAIL", "reason": "no valid link"}
    if not quote:
        return {**res, "status": "FAIL", "reason": "no quote given"}
    text, code, kind, detail = fetch(url)
    if code is not None:
        res["reached"] = True
    if text is None:
        if kind in ("blocked", "pdf"):
            return {**res, "status": "UNCHECKED", "reason": detail + (" (site blocks automated access or paywall)" if kind == "blocked" else "")}
        if kind in ("dns", "network"):
            return {**res, "status": "UNCHECKED", "reason": detail, "network": True, "dns": kind == "dns"}
        return {**res, "status": "FAIL", "reason": f"page did not open ({detail})"}
    ratio, found = best_match(normalize(quote), normalize(text))
    if ratio >= PASS_RATIO:
        return {**res, "status": "PASS", "reason": "quote found on page" if ratio == 1.0 else f"quote found ({ratio:.0%} match)"}
    if ratio >= PARTIAL_RATIO:
        return {**res, "status": "PARTIAL", "reason": f"close match only ({ratio:.0%}): \"{found[:90]}\""}
    if len(normalize(text)) < 400:
        return {**res, "status": "UNCHECKED", "reason": "page opened but had almost no readable text (JavaScript page or bot wall)"}
    hint = f'; closest text: "{found[:90]}"' if ratio >= 0.5 and found else ""
    return {**res, "status": "FAIL", "reason": "page opened, but the quote is not on it" + hint}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    with open(sys.argv[1], encoding="utf-8") as f:
        items = json.load(f)
    results = [check(it) for it in items]
    # If the network works for other links, a missing domain means the link itself is bad.
    if any(r.get("reached") for r in results):
        for r in results:
            if r.get("dns"):
                r.update(status="FAIL", reason="domain does not exist (other links opened fine)", network=False)

    if "--json" in sys.argv:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print("SOURCE CHECK (done by code, not by the model)\n")
        print("| # | Status | Claim | Result |")
        print("|---|---|---|---|")
        for r in results:
            claim = (r["claim"] or r["url"])[:60].replace("|", "/")
            print(f"| {r['id']} | {r['status']} | {claim} | {r['reason'].replace('|', '/')} |")
        counts = {s: sum(1 for r in results if r["status"] == s) for s in ("PASS", "PARTIAL", "FAIL", "UNCHECKED")}
        print("\nSummary: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
        if results and not any(r.get("reached") for r in results) and any(r.get("network") for r in results):
            print("\nNo page could be reached. Network access is probably off for code.")
            print('Turn on "Allow network egress" in Settings > Capabilities, then run /socrates recheck.')
    sys.exit(0)


if __name__ == "__main__":
    main()
