#!/usr/bin/env python3
"""Cross-post a Saltmire blog post to Dev.to via the public API.

Republishes the SAME tutorial on dev.to with a canonical_url pointing back to
saltmire.github.io — so Google credits the original (no duplicate-content
penalty) while a dev-native audience discovers it. Fully autonomous: no browser.

Setup (one-time, human):
  1. Create a free account at https://dev.to
  2. Settings -> Extensions -> "Generate API Key"
  3. Save the key to  ../dashboard/.devto_key  (one line, gitignored)

Usage:
  python crosspost_devto.py <slug>      # cross-post one post
  python crosspost_devto.py --latest    # cross-post the newest post by date
  python crosspost_devto.py --dry-run <slug>   # print payload, don't send

Idempotent: a slug already recorded in ../dashboard/devto_posted.json is skipped.
"""
import os
import sys
import json
import urllib.request
import urllib.error

import build  # reuse parse_post / BASE_URL from the site generator

HERE = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(HERE, "..", "dashboard", ".devto_key")
POSTED_FILE = os.path.join(HERE, "..", "dashboard", "devto_posted.json")
API = "https://dev.to/api/articles"

# Dev.to allows max 4 tags, lowercase alphanumeric only.
TAGS = ["godot", "gamedev", "tutorial", "programming"]


def load_key():
    if not os.path.exists(KEY_FILE):
        print(f"[skip] no Dev.to API key at {KEY_FILE} — not set up yet.")
        sys.exit(0)
    return open(KEY_FILE, encoding="utf-8").read().strip()


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


def build_payload(meta):
    canonical = f"{build.BASE_URL}/{meta['slug']}.html"
    body = meta["body_md"]
    # Soft, honest footer leading to the product — mirrors the blog CTA.
    if meta.get("product_name") and meta.get("product_url"):
        body += (
            f"\n\n---\n\nIf you'd rather drop this in than build it, "
            f"**{meta['product_name']}** does it as a ready-made tool: "
            f"{meta['product_url']}\n\n"
            f"*Originally published at {canonical}*"
        )
    return {
        "article": {
            "title": meta["title"],
            "body_markdown": body,
            "published": True,
            "canonical_url": canonical,
            "description": meta.get("description", ""),
            "tags": TAGS,
        }
    }


def post(payload, key):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API, data=data, method="POST")
    req.add_header("api-key", key)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/vnd.forem.api-v1+json")
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SaltmireBot/1.0")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry = "--dry-run" in sys.argv
    if not args:
        sys.exit("usage: crosspost_devto.py <slug>|--latest [--dry-run]")

    meta = pick_post(args[0])
    posted = load_posted()
    if meta["slug"] in posted and not dry:
        print(f"already cross-posted: {meta['slug']} -> {posted[meta['slug']]}")
        return

    payload = build_payload(meta)
    if dry:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    key = load_key()
    try:
        res = post(payload, key)
    except urllib.error.HTTPError as e:
        sys.exit(f"Dev.to API error {e.code}: {e.read().decode(errors='replace')}")

    url = res.get("url", "(no url returned)")
    posted[meta["slug"]] = url
    save_posted(posted)
    print(f"cross-posted {meta['slug']} -> {url}")


if __name__ == "__main__":
    main()
