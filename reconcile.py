#!/usr/bin/env python3
"""Detect (and optionally heal) posts left half-shipped by a dead autopost run.

The autopost routine writes the post, builds, updates the catalog, commits,
pushes, then cross-posts. It is an agent run, so it can die between any two of
those steps -- and twice it did (2026-08-20 and 2026-09-04), each time leaving a
post that existed on disk but was 404 on the live site and absent from Dev.to
and Bluesky. The 08-20 one sat broken for 14 days because nothing ever looked.

This sweeps the four invariants a fully shipped post satisfies and reports what
is missing. With --ship it heals the two steps that are safely automatable:
the git commit/push and the cross-posts (both idempotent).

Usage:
  python reconcile.py            # report only, exit 1 if anything is orphaned
  python reconcile.py --ship     # also commit+push and cross-post what is missing
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

import build

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "..", "catalog.json")
DASH = os.path.join(HERE, "..", "dashboard")
CHANNELS = {"devto": "crosspost_devto.py", "bluesky": "crosspost_bluesky.py"}

# Dev.to returns 429 with a 30s window when posts are created back to back.
DEVTO_COOLDOWN = 35


def sh(*args, check=True):
    return subprocess.run(args, cwd=HERE, capture_output=True, text=True,
                          check=check, timeout=180).stdout.strip()


def local_posts():
    posts = [build.parse_post(os.path.join(build.POSTS_DIR, f))
             for f in os.listdir(build.POSTS_DIR) if f.endswith(".md")]
    return sorted(posts, key=lambda p: p["date"])


def catalog_slugs():
    cat = json.load(open(CATALOG, encoding="utf-8"))
    return {p["slug"] for p in cat["blog"]["posts"]}


def posted_slugs(channel):
    path = os.path.join(DASH, f"{channel}_posted.json")
    if not os.path.exists(path):
        return set()
    return set(json.load(open(path, encoding="utf-8")))


def is_live(slug):
    url = f"{build.BASE_URL}/{slug}.html"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 SaltmireBot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status == 200
    except urllib.error.HTTPError:
        return False
    except Exception:
        return False


def git_dirty():
    return bool(sh("git", "status", "--porcelain"))


def git_unpushed():
    return bool(sh("git", "log", "@{u}..HEAD", "--oneline", check=False))


def main():
    ship = "--ship" in sys.argv
    posts = local_posts()
    in_catalog = catalog_slugs()
    problems = []

    # 1. catalog -- needs a human/agent decision (format is the A/B variable), never auto-filled
    missing_cat = [p["slug"] for p in posts if p["slug"] not in in_catalog]
    for slug in missing_cat:
        problems.append(f"nao esta no catalog.json: {slug} (precisa de format+date a mao)")

    # 2. git -- an uncommitted post is a 404 on the live site
    dirty, unpushed = git_dirty(), git_unpushed()
    if dirty or unpushed:
        what = "mudancas nao commitadas" if dirty else "commits nao enviados"
        if ship:
            print(f"[ship] {what} -> commit+push")
            if dirty:
                sh("git", "add", "-A")
                sh("git", "commit", "-m", "blog: reconcile posts orfaos de run interrompida")
            print(sh("git", "push"))
        else:
            problems.append(what)

    # 3 + 4. live URL and cross-posts
    already = {c: posted_slugs(c) for c in CHANNELS}
    devto_sent = False
    for p in posts:
        slug = p["slug"]
        pending = [c for c in CHANNELS if slug not in already[c]]
        if not pending:
            continue
        if not is_live(slug):
            problems.append(f"404 no ar (cross-post bloqueado ate publicar): {slug}")
            continue
        for channel in pending:
            if not ship:
                problems.append(f"falta {channel}: {slug}")
                continue
            if channel == "devto" and devto_sent:
                time.sleep(DEVTO_COOLDOWN)
            r = subprocess.run([sys.executable, CHANNELS[channel], slug],
                               cwd=HERE, capture_output=True, text=True, timeout=180)
            out = (r.stdout + r.stderr).strip().splitlines()
            print(f"[ship] {channel} {slug}: {out[-1] if out else '(sem saida)'}")
            if r.returncode != 0:
                problems.append(f"{channel} falhou em {slug}")
            elif channel == "devto":
                devto_sent = True

    if problems:
        print("\nPENDENCIAS:")
        for x in problems:
            print(" -", x)
        return 1
    print(f"OK: {len(posts)} post(s) commitados, no ar e cross-postados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
