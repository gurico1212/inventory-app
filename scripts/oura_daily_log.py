#!/usr/bin/env python3
"""Fetch yesterday's Oura Ring sleep/activity/readiness data and append it to the vault log."""

import os
import sys
from datetime import datetime, timedelta, timezone

import requests

JST = timezone(timedelta(hours=9))
API_BASE = "https://api.ouraring.com/v2/usercollection"
LOG_FILE = os.path.join("Health", "oura-log.md")

TITLE = "# Oura Ring Daily Log\n"
HEADER = "| 日付 | 睡眠スコア | 総睡眠時間 | レディネススコア | 活動スコア | 歩数 |\n"
DIVIDER = "| --- | --- | --- | --- | --- | --- |\n"


def get_target_date():
    """Return the previous calendar day in JST (the day the 07:00 JST run reports on)."""
    now_jst = datetime.now(JST)
    return (now_jst - timedelta(days=1)).date()


def fetch_endpoint(token, endpoint, date_str):
    url = f"{API_BASE}/{endpoint}"
    params = {"start_date": date_str, "end_date": date_str}
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return data[0] if data else None


def format_duration(seconds):
    if seconds is None:
        return "-"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h{minutes:02d}m"


def build_row(date_str, sleep, activity, readiness):
    sleep_score = sleep.get("score") if sleep else None
    total_sleep = sleep.get("total_sleep_duration") if sleep else None
    readiness_score = readiness.get("score") if readiness else None
    activity_score = activity.get("score") if activity else None
    steps = activity.get("steps") if activity else None

    cells = [
        date_str,
        str(sleep_score) if sleep_score is not None else "-",
        format_duration(total_sleep),
        str(readiness_score) if readiness_score is not None else "-",
        str(activity_score) if activity_score is not None else "-",
        str(steps) if steps is not None else "-",
    ]
    return "| " + " | ".join(cells) + " |\n"


def ensure_log_file(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(TITLE)
            f.write("\n")
            f.write(HEADER)
            f.write(DIVIDER)


def date_already_logged(path, date_str):
    prefix = f"| {date_str} "
    with open(path, "r", encoding="utf-8") as f:
        return any(line.startswith(prefix) for line in f)


def append_row(path, row):
    with open(path, "a", encoding="utf-8") as f:
        f.write(row)


def main():
    token = os.environ.get("OURA_TOKEN")
    if not token:
        print("Error: OURA_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    date_str = get_target_date().isoformat()

    ensure_log_file(LOG_FILE)

    if date_already_logged(LOG_FILE, date_str):
        print(f"{date_str} is already logged in {LOG_FILE}. Skipping.")
        return

    sleep = fetch_endpoint(token, "daily_sleep", date_str)
    activity = fetch_endpoint(token, "daily_activity", date_str)
    readiness = fetch_endpoint(token, "daily_readiness", date_str)

    if sleep is None and activity is None and readiness is None:
        print(f"No Oura data available for {date_str} yet. Skipping.")
        return

    row = build_row(date_str, sleep, activity, readiness)
    append_row(LOG_FILE, row)
    print(f"Appended log for {date_str}: {row.strip()}")


if __name__ == "__main__":
    main()
