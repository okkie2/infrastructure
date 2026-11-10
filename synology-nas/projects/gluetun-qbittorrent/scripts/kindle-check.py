#!/usr/bin/env python3
"""LazyLibrarian pre-process hook: warn (never modify) when an EPUB is likely to fail
Amazon's Send-to-Kindle conversion.

Called by LazyLibrarian as: kindle-check.py <book_type> <book_path> <author> <bookname>
Known case: "A Fire Upon the Deep" had 1,581 spine items and never delivered;
a 568-item omnibus delivered fine. Threshold sits in between.

Safety: always exits 0 so a problem here can never fail an import.
"""
import os
import re
import sys
import time
import urllib.request
import zipfile

MAX_OPF_BYTES = 20_000_000            # never load a larger manifest into memory
THRESHOLD = 1000                      # spine items above this trigger a warning
CONF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kindle-check.conf")
LOG = "/config/log/kindle-check.log"


def log(msg):
    try:
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except OSError:
        pass


def ntfy_url():
    try:
        with open(CONF, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("NTFY_URL="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def notify(title, message):
    url = ntfy_url()
    if not url:
        log("no NTFY_URL configured; alert not sent")
        return
    req = urllib.request.Request(
        url, data=message.encode("utf-8"),
        headers={"Title": title, "Tags": "warning,books", "Priority": "default"})
    try:
        urllib.request.urlopen(req, timeout=10).read()
        log(f"alert sent: {title}")
    except Exception as exc:  # noqa: BLE001 - alerting must never raise
        log(f"alert failed: {exc!r}")


def epubs_in(path):
    if os.path.isfile(path):
        return [path] if path.lower().endswith(".epub") else []
    found = []
    for root, _dirs, files in os.walk(path):
        found += [os.path.join(root, f) for f in files if f.lower().endswith(".epub")]
    return found


def spine_items(epub):
    with zipfile.ZipFile(epub) as zf:
        opf = next((n for n in zf.namelist() if n.lower().endswith(".opf")), None)
        if not opf:
            return 0
        if zf.getinfo(opf).file_size > MAX_OPF_BYTES:   # hostile or corrupt archive
            raise ValueError(f"manifest larger than {MAX_OPF_BYTES} bytes, skipped")
        return len(re.findall(rb"<(?:\w+:)?itemref\b", zf.read(opf)))


def main():
    if len(sys.argv) < 3:
        return
    book_type, book_path = sys.argv[1], sys.argv[2]
    author = sys.argv[3] if len(sys.argv) > 3 else "?"
    bookname = sys.argv[4] if len(sys.argv) > 4 else "?"
    if book_type.lower() not in ("ebook", "book"):
        return
    for epub in epubs_in(book_path):
        try:
            n = spine_items(epub)
        except Exception as exc:  # noqa: BLE001
            log(f"could not inspect {epub}: {exc!r}")
            continue
        log(f"checked {author} - {bookname}: {n} spine items ({os.path.basename(epub)})")
        if n > THRESHOLD:
            notify(
                "Kindle delivery risk: EPUB badly split",
                f"{author} - {bookname}\n{n} internal files (limit I trust: {THRESHOLD}). "
                "A 1,581-file EPUB never reached the Kindle; rebuild it before sending "
                "(fix-epub on the Mac).")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        log(f"unexpected error: {exc!r}")
    sys.exit(0)
