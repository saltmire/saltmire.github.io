#!/usr/bin/env python3
"""Post a Saltmire blog post to Mastodon / Fediverse (no browser).

Mastodon is where a big chunk of the Godot community lives (esp. the
gamedev.place instance), the API is trivial, and it respects link previews via
OpenGraph — so this is fully autonomous. Posts a short hook + the canonical blog
URL; Mastodon auto-builds the link card and Google still credits the original.

Setup (one-time, human):
  1. Create a free account. RECOMMENDED instance for us: https://mastodon.gamedev.place
     (gamedev-focused; our exact audience). Any instance works though.
  2. Settings -> Development -> New application. Name it "Saltmire crosspost".
     Scopes: tick at least  write:statuses  (read is fine too). Submit.
  3. Open the app -> copy "Your access token".
  4. Save to  ../dashboard/.mastodon_key  as TWO lines (gitignored):
        https://mastodon.gamedev.place      <- your instance base URL (no trailing slash)
        <your access token>

Usage:
  python crosspost_mastodon.py <slug>|--latest [--dry-run]

Idempotent: a slug already in ../dashboard/mastodon_posted.json is skipped.
"""
import os
import sys
import json
import urllib.parse
import urllib.request
import urllib.error

import build  # reuse parse_post / BASE_URL from the site generator

HERE = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(HERE, "..", "dashboard", ".mastodon_key")
POSTED_FILE = os.path.join(HERE, "..", "dashboard", "mastodon_posted.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SaltmireBot/1.0"
HASHTAGS = "#godot #godotengine #gamedev #gdscript"


def load_creds():
    if not os.path.exists(KEY_FILE):
        print(f"[skip] no Mastodon creds at {KEY_FILE} — not set up yet.")
        sys.exit(0)
    lines = [l.strip() for l in open(KEY_FILE, encoding="utf-8") if l.strip()]
    if len(lines) < 2:
        sys.exit("Mastodon key file needs 2 lines: instance base URL then access token.")
    return lines[0].rstrip("/"), lines[1]


def load_posted():
    if os.path.exists(POSTED_FILE):
        return json.load(open(POSTED_FILE, encoding="utf-8"))
    return {}


def save_posted(d):
    json.dump(d, open(POSTED_FILE, "w", encoding="utf-8"), indent=2)


def pick_post(arg):
    posts = [build.parse_post(os.path.join(build.POSTS_DIR, f))
             for f in os.listdir(build.POSTS_DIR) if f.endswith(".md")]
    if arg == "--latest":
        posts.sort(key=lambda p: p["date"], reverse=True)
        return posts[0]
    for p in posts:
        if p["slug"] == arg:
            return p
    sys.exit(f"No post with slug {arg!r} in {build.POSTS_DIR}")


def build_status(meta):
    canonical = f"{build.BASE_URL}/{meta['slug']}.html"
    # Mastodon default limit is 500 chars; keep the hook short, URL builds the card.
    hook = f"{meta['title']} — a short, practical Godot 4 walkthrough with paste-ready code."
    status = f"{hook}\n\n{canonical}\n\n{HASHTAGS}"
    if len(status) > 500:
        over = len(status) - 500
        hook = hook[: max(0, len(hook) - over - 3)] + "..."
        status = f"{hook}\n\n{canonical}\n\n{HASHTAGS}"
    return status


def post(base, token, status):
    data = urllib.parse.urlencode({"status": status, "visibility": "public"}).encode()
    req = urllib.request.Request(f"{base}/api/v1/statuses", data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("User-Agent", UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry = "--dry-run" in sys.argv
    if not args:
        sys.exit("usage: crosspost_mastodon.py <slug>|--latest [--dry-run]")

    meta = pick_post(args[0])
    posted = load_posted()
    if meta["slug"] in posted and not dry:
        print(f"already posted to Mastodon: {meta['slug']} -> {posted[meta['slug']]}")
        return

    status = build_status(meta)
    if dry:
        print(status)
        return

    base, token = load_creds()
    try:
        res = post(base, token, status)
    except urllib.error.HTTPError as e:
        sys.exit(f"Mastodon API error {e.code}: {e.read().decode(errors='replace')}")

    url = res.get("url") or res.get("uri", "(no url returned)")
    posted[meta["slug"]] = url
    save_posted(posted)
    print(f"posted to Mastodon {meta['slug']} -> {url}")


if __name__ == "__main__":
    main()
