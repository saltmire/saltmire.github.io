#!/usr/bin/env python3
"""Cross-post a Saltmire blog post to Hashnode via its GraphQL API (no browser).

Hashnode is a dev-native blog network with real Google reach; it respects a
canonical URL (originalArticleURL) so Google still credits saltmire.github.io as
the original (no duplicate-content penalty). Fully autonomous.

Setup (one-time, human):
  1. Create a free account at https://hashnode.com and create a publication
     (your blog) during onboarding — any name, e.g. "Saltmire".
  2. Settings -> Developer -> "Generate new token" (Personal Access Token).
  3. Save the token to  ../dashboard/.hashnode_key  (one line, gitignored).
     (The publication ID is looked up automatically from your account.)

Usage:
  python crosspost_hashnode.py <slug>|--latest [--dry-run]

Idempotent: a slug already in ../dashboard/hashnode_posted.json is skipped.
"""
import os
import sys
import json
import urllib.request
import urllib.error

import build  # reuse parse_post / BASE_URL from the site generator

HERE = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(HERE, "..", "dashboard", ".hashnode_key")
POSTED_FILE = os.path.join(HERE, "..", "dashboard", "hashnode_posted.json")
GQL = "https://gql.hashnode.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SaltmireBot/1.0"

# Hashnode tags: each needs a slug + display name.
TAGS = [
    {"slug": "godot", "name": "Godot"},
    {"slug": "gamedev", "name": "GameDev"},
    {"slug": "tutorial", "name": "Tutorial"},
    {"slug": "programming", "name": "Programming"},
]


def load_key():
    if not os.path.exists(KEY_FILE):
        print(f"[skip] no Hashnode token at {KEY_FILE} — not set up yet.")
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


def gql(query, variables, token):
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(GQL, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", token)  # Hashnode PAT goes in Authorization (no "Bearer")
    req.add_header("User-Agent", UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.load(r)
    if out.get("errors"):
        raise RuntimeError(json.dumps(out["errors"]))
    return out["data"]


def get_publication_id(token):
    q = "query { me { publications(first: 1) { edges { node { id title } } } } }"
    data = gql(q, {}, token)
    edges = data["me"]["publications"]["edges"]
    if not edges:
        sys.exit("No Hashnode publication found on this account. Create one first.")
    return edges[0]["node"]["id"]


def build_input(meta, publication_id):
    canonical = f"{build.BASE_URL}/{meta['slug']}.html"
    body = meta["body_md"]
    if meta.get("product_name") and meta.get("product_url"):
        body += (
            f"\n\n---\n\nIf you'd rather drop this in than build it, "
            f"**{meta['product_name']}** does it as a ready-made tool: "
            f"{meta['product_url']}\n\n"
            f"*Originally published at {canonical}*"
        )
    return {
        "title": meta["title"],
        "contentMarkdown": body,
        "publicationId": publication_id,
        "tags": TAGS,
        "originalArticleURL": canonical,  # canonical -> no duplicate-content penalty
    }


def main():
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry = "--dry-run" in sys.argv
    if not args:
        sys.exit("usage: crosspost_hashnode.py <slug>|--latest [--dry-run]")

    meta = pick_post(args[0])
    posted = load_posted()
    if meta["slug"] in posted and not dry:
        print(f"already cross-posted to Hashnode: {meta['slug']} -> {posted[meta['slug']]}")
        return

    if dry:
        # No token needed to preview the payload shape.
        inp = build_input(meta, "<publication-id>")
        print(json.dumps({"title": inp["title"],
                          "originalArticleURL": inp["originalArticleURL"],
                          "tags": [t["slug"] for t in inp["tags"]],
                          "body_chars": len(inp["contentMarkdown"])}, indent=2))
        return

    token = load_key()
    try:
        pub_id = get_publication_id(token)
        mutation = ("mutation Publish($input: PublishPostInput!) { "
                    "publishPost(input: $input) { post { id url slug } } }")
        data = gql(mutation, {"input": build_input(meta, pub_id)}, token)
    except urllib.error.HTTPError as e:
        sys.exit(f"Hashnode API error {e.code}: {e.read().decode(errors='replace')}")
    except RuntimeError as e:
        sys.exit(f"Hashnode GraphQL error: {e}")

    url = data["publishPost"]["post"]["url"]
    posted[meta["slug"]] = url
    save_posted(posted)
    print(f"cross-posted to Hashnode {meta['slug']} -> {url}")


if __name__ == "__main__":
    main()
