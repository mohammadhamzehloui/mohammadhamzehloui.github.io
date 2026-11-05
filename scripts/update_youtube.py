#!/usr/bin/env python3
"""Refresh the "On YouTube" card in index.html from the channel's public RSS feed.

No API key and no token: youtube.com/feeds/videos.xml is public. Run it from the
repo root (the GitHub Action does this on a schedule, and you can run it locally).

SKIP is why this does not show the newest video: the newest reel is usually the
one already featured on the Instagram card, and showing it twice looks thin.
Set SKIP = 0 if you ever want the card to show the very latest upload.
"""
import html
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

CHANNEL_ID = "UCjMbuvM6hSCTTgLnt3yiaHw"
FEED = "https://www.youtube.com/feeds/videos.xml?channel_id=" + CHANNEL_ID
SKIP = 3                      # skip the reels featured on the Instagram card above
PAGE = Path(__file__).resolve().parent.parent / "index.html"
START, END = "<!-- YT:START -->", "<!-- YT:END -->"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "hamzehloui.com feed updater"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def entries(xml):
    out = []
    for block in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        def tag(name):
            m = re.search(r"<%s[^>]*>(.*?)</%s>" % (name, name), block, re.S)
            return html.unescape(m.group(1)).strip() if m else ""
        vid = tag("yt:videoId")
        title = tag("title")
        published = tag("published")
        if vid and title:
            out.append((vid, title, published))
    return out


def clean(title):
    """Drop trailing hashtags - they are for YouTube's algorithm, not a web page."""
    return re.sub(r"\s*#\w+", "", title).strip()


def card(vid, title, published):
    try:
        when = datetime.strptime(published[:10], "%Y-%m-%d").strftime("%-d %b %Y")
    except ValueError:
        when = datetime.strptime(published[:10], "%Y-%m-%d").strftime("%d %b %Y").lstrip("0")
    return (
        '%s<a class="w-row" href="https://www.youtube.com/watch?v=%s" target="_blank" rel="noopener">\n'
        '            <span class="w-thumb"><img src="https://i.ytimg.com/vi/%s/maxresdefault.jpg" '
        'width="78" height="139" loading="lazy" alt=""><span class="play" aria-hidden="true"></span></span>\n'
        '            <span class="w-rt"><span class="w-title">%s</span>'
        '<span class="w-meta">%s</span></span>\n'
        '          </a>%s' % (START, vid, vid, html.escape(clean(title)), when, END)
    )


def main():
    vids = entries(fetch(FEED))
    if not vids:
        sys.exit("no entries in the feed - aborting rather than emptying the card")
    vid, title, published = vids[min(SKIP, len(vids) - 1)]

    page = PAGE.read_text(encoding="utf-8")
    if START not in page or END not in page:
        sys.exit("markers missing from index.html")
    head, rest = page.split(START, 1)
    _, tail = rest.split(END, 1)
    updated = head + card(vid, title, published) + tail

    if updated == page:
        print("no change:", clean(title))
        return
    PAGE.write_text(updated, encoding="utf-8", newline="")
    print("updated to:", clean(title), "(%s)" % vid)


if __name__ == "__main__":
    main()
