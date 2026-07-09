#!/usr/bin/env python3
"""Post a Saltmire blog post to Bluesky via the AT Protocol (no browser).

Bluesky is where a chunk of the Godot community is migrating, links are NOT
suppressed there (unlike X), and it has a clean public API — so this is fully
autonomous. Posts a short hook + a link card pointing at the blog post.

Setup (one-time, human):
  1. Create the account (e.g. @saltmire.bsky.social)
  2. Settings -> App Passwords -> add one
  3. Save to ../dashboard/.bluesky_key as TWO lines (gitignored):
        handle.bsky.social
        xxxx-xxxx-xxxx-xxxx

Usage:
  python crosspost_bluesky.py <slug>|--latest [--dry-run]

Idempotent: a slug already in ../dashboard/bluesky_posted.json is skipped.
"""
import os
import sys
import json
import datetime
import urllib.request
import urllib.error

import build

HERE = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(HERE, "..", "dashboard", ".bluesky_key")
POSTED_FILE = os.path.join(HERE, "..", "dashboard", "bluesky_posted.json")
PDS = "https://bsky.social"


def load_creds():
    if not os.path.exists(KEY_FILE):
        print(f"[skip] no Bluesky creds at {KEY_FILE} — not set up yet.")
        sys.exit(0)
    lines = [l.strip() for l in open(KEY_FILE, encoding="utf-8") if l.strip()]
    if len(lines) < 2:
        sys.exit("Bluesky key file needs 2 lines: handle then app-password.")
    return lines[0], lines[1]


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


def api(endpoint, payload, token=None):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(f"{PDS}/xrpc/{endpoint}", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SaltmireBot/1.0")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def build_record(meta):
    canonical = f"{build.BASE_URL}/{meta['slug']}.html"
    text = f"{meta['title']} — a short, practical Godot 4 walkthrough with paste-ready code."
    if len(text) > 300:
        text = text[:297] + "..."
    return {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "langs": ["en"],
        "embed": {
            "$type": "app.bsky.embed.external",
            "external": {
                "uri": canonical,
                "title": meta["title"],
                "description": meta.get("description", "")[:300],
            },
        },
    }


def main():
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry = "--dry-run" in sys.argv
    if not args:
        sys.exit("usage: crosspost_bluesky.py <slug>|--latest [--dry-run]")

    meta = pick_post(args[0])
    posted = load_posted()
    if meta["slug"] in posted and not dry:
        print(f"already posted to Bluesky: {meta['slug']} -> {posted[meta['slug']]}")
        return

    record = build_record(meta)
    if dry:
        print(json.dumps(record, indent=2, ensure_ascii=False))
        return

    handle, app_pw = load_creds()
    try:
        sess = api("com.atproto.server.createSession",
                   {"identifier": handle, "password": app_pw})
        res = api("com.atproto.repo.createRecord", {
            "repo": sess["did"],
            "collection": "app.bsky.feed.post",
            "record": record,
        }, token=sess["accessJwt"])
    except urllib.error.HTTPError as e:
        sys.exit(f"Bluesky API error {e.code}: {e.read().decode(errors='replace')}")

    # Build a friendly post URL from the returned at:// uri.
    rkey = res["uri"].rsplit("/", 1)[-1]
    url = f"https://bsky.app/profile/{handle}/post/{rkey}"
    posted[meta["slug"]] = url
    save_posted(posted)
    print(f"posted to Bluesky {meta['slug']} -> {url}")


if __name__ == "__main__":
    main()
