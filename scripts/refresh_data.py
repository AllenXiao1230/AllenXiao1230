"""Fetch the public GitHub contribution calendar. No packages or personal token needed."""
from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cells = {}
        self.counts = {}
        self.tip_id = None
        self.tip_text = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "td" and a.get("data-date") and a.get("id"):
            self.cells[a["id"]] = {"date": a["data-date"], "level": int(a.get("data-level", 0))}
        if tag == "tool-tip":
            self.tip_id = a.get("for")
            self.tip_text = []

    def handle_data(self, data):
        if self.tip_id:
            self.tip_text.append(data)

    def handle_endtag(self, tag):
        if tag == "tool-tip" and self.tip_id:
            text = " ".join("".join(self.tip_text).split())
            m = re.match(r"^([\d,]+) contributions?\b", text)
            if text.startswith("No contributions"):
                self.counts[self.tip_id] = 0
            elif m:
                self.counts[self.tip_id] = int(m.group(1).replace(",", ""))
            self.tip_id = None


def parse_calendar(html, start, end):
    parser = CalendarParser()
    parser.feed(html)
    days = []
    for cell_id, cell in parser.cells.items():
        d = date.fromisoformat(cell["date"])
        if start <= d <= end:
            if cell_id not in parser.counts:
                raise ValueError(f"Missing exact contribution count for {d}; keeping previous data.")
            count = parser.counts[cell_id]
            if (count == 0) != (cell["level"] == 0):
                raise ValueError(f"Calendar level/count mismatch on {d}.")
            days.append({**cell, "count": count})
    days.sort(key=lambda d: d["date"])
    expected = (end - start).days + 1
    if len(days) != expected or len({d["date"] for d in days}) != expected:
        raise ValueError(f"Expected {expected} calendar days, received {len(days)}; keeping previous data.")
    return days


def fetch(url):
    req = Request(url, headers={"User-Agent": "AllenXiao1230-profile-readme", "Accept-Language": "en-US,en;q=0.9"})
    with urlopen(req, timeout=40) as response:
        return response.read().decode("utf-8")


def main():
    config = json.loads((ROOT / "profile.json").read_text("utf-8"))
    username = config["username"]
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", username):
        raise ValueError("Invalid GitHub username in profile.json.")
    today = datetime.now(timezone(timedelta(hours=8))).date()
    url = f"https://github.com/users/{username}/contributions"
    source_html = fetch(url)
    parser = CalendarParser()
    parser.feed(source_html)
    if not parser.cells:
        raise ValueError("GitHub returned no contribution calendar.")
    # The default endpoint spans the year boundary; from/to can select one year.
    # GitHub's current date may trail Taiwan until UTC midnight.
    end = min(today, max(date.fromisoformat(c["date"]) for c in parser.cells.values()))
    if (today - end).days > 1:
        raise ValueError("GitHub returned a stale contribution calendar.")
    start = end - timedelta(days=364)
    days = parse_calendar(source_html, start, end)
    result = {"username": username, "source": url, "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "from": str(start), "to": str(end), "days": days}
    target = ROOT / "data" / "contributions.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf-8")
    tmp.replace(target)
    print(f"Fetched {len(days)} real calendar days; {sum(d['count'] for d in days)} contributions.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Refresh failed: {exc}", file=sys.stderr)
        sys.exit(1)
