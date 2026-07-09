#!/usr/bin/env python3
"""Collect per-post engagement from Dev.to + Bluesky, aggregated by FORMAT.

This is the measurement half of the format A/B test: it pulls real numbers per
post and rolls them up by the "format" tag in catalog.json, so we can see which
post format actually earns attention — data, not guesswork.

Writes dashboard/channel_metrics.json and prints a short table.
Safe to run repeatedly (read-only API calls). Self-skips channels with no token.
"""
import os
import sys
import json
import datetime
import urllib.request
import urllib.error

import build  # BASE_URL, HERE

HERE = os.path.dirname(os.path.abspath(__file__))
DASH = os.path.join(HERE, "..", "dashboard")
CATALOG = os.path.join(HERE, "..", "catalog.json")
OUT = os.path.join(DASH, "channel_metrics.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SaltmireBot/1.0"


def _get(url, headers, timeout=30):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def load_catalog_posts():
    cat = json.load(open(CATALOG, encoding="utf-8"))
    posts = cat.get("blog", {}).get("posts", [])
    by_canonical = {}
    for p in posts:
        canonical = f"{build.BASE_URL}/{p['slug']}.html"
        by_canonical[canonical] = p
    return posts, by_canonical


def devto_metrics(by_canonical):
    key_file = os.path.join(DASH, ".devto_key")
    if not os.path.exists(key_file):
        return {}
    key = open(key_file, encoding="utf-8").read().strip()
    out = {}
    try:
        arts = _get("https://dev.to/api/articles/me/published?per_page=100",
                    {"api-key": key, "Accept": "application/vnd.forem.api-v1+json"})
    except urllib.error.HTTPError as e:
        print(f"[devto] error {e.code}")
        return {}
    for a in arts:
        canonical = a.get("canonical_url", "")
        p = by_canonical.get(canonical)
        if not p:
            continue
        out[p["slug"]] = {
            "url": a.get("url"),
            "views": a.get("page_views_count", 0),
            "reactions": a.get("public_reactions_count", 0),
            "comments": a.get("comments_count", 0),
        }
    return out


def bluesky_metrics(by_canonical):
    key_file = os.path.join(DASH, ".bluesky_key")
    if not os.path.exists(key_file):
        return {}
    lines = [l.strip() for l in open(key_file, encoding="utf-8") if l.strip()]
    handle, app_pw = lines[0], lines[1]
    try:
        req = urllib.request.Request(
            "https://bsky.social/xrpc/com.atproto.server.createSession",
            data=json.dumps({"identifier": handle, "password": app_pw}).encode(),
            method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            sess = json.load(r)
    except urllib.error.HTTPError as e:
        print(f"[bluesky] auth error {e.code}")
        return {}
    token, did = sess["accessJwt"], sess["did"]
    out = {}
    cursor = None
    for _ in range(5):  # up to 5 pages
        url = f"https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed?actor={did}&limit=100"
        if cursor:
            url += f"&cursor={cursor}"
        feed = _get(url, {"Authorization": f"Bearer {token}"})
        for item in feed.get("feed", []):
            post = item.get("post", {})
            embed = post.get("embed", {}) or {}
            ext = embed.get("external", {}) or {}
            canonical = ext.get("uri", "")
            p = by_canonical.get(canonical)
            if not p:
                continue
            out[p["slug"]] = {
                "url": f"https://bsky.app/profile/{handle}/post/{post['uri'].rsplit('/',1)[-1]}",
                "likes": post.get("likeCount", 0),
                "reposts": post.get("repostCount", 0),
                "replies": post.get("replyCount", 0),
            }
        cursor = feed.get("cursor")
        if not cursor:
            break
    return out


def main():
    posts, by_canonical = load_catalog_posts()
    devto = devto_metrics(by_canonical)
    bsky = bluesky_metrics(by_canonical)

    per_post = {}
    by_format = {}
    for p in posts:
        slug = p["slug"]
        fmt = p.get("format", "unknown")
        d = devto.get(slug, {})
        b = bsky.get(slug, {})
        per_post[slug] = {"format": fmt, "date": p.get("date"),
                          "devto": d, "bluesky": b}
        agg = by_format.setdefault(fmt, {"posts": 0, "devto_views": 0,
                                         "devto_reactions": 0, "devto_comments": 0,
                                         "bsky_likes": 0, "bsky_reposts": 0, "bsky_replies": 0})
        agg["posts"] += 1
        agg["devto_views"] += d.get("views", 0)
        agg["devto_reactions"] += d.get("reactions", 0)
        agg["devto_comments"] += d.get("comments", 0)
        agg["bsky_likes"] += b.get("likes", 0)
        agg["bsky_reposts"] += b.get("reposts", 0)
        agg["bsky_replies"] += b.get("replies", 0)

    result = {
        "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "per_post": per_post,
        "by_format": by_format,
    }
    json.dump(result, open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    print(f"channel metrics -> {OUT}\n")
    print(f"{'format':<11} {'posts':>5} {'dv.views':>8} {'dv.react':>8} {'bsky.likes':>10}")
    for fmt, a in sorted(by_format.items()):
        print(f"{fmt:<11} {a['posts']:>5} {a['devto_views']:>8} "
              f"{a['devto_reactions']:>8} {a['bsky_likes']:>10}")


if __name__ == "__main__":
    main()
