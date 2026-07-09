#!/usr/bin/env python3
"""Set the Saltmire Bluesky profile (avatar, banner, name, bio) via AT Protocol.

One-shot brand setup so the account doesn't look like an empty bot. Reads creds
from ../dashboard/.bluesky_key (handle + app-password). Uploads the brand assets
as blobs and writes the app.bsky.actor.profile record.
"""
import os
import sys
import json
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(HERE, "..", "dashboard", ".bluesky_key")
BRAND = os.path.join(HERE, "..", "brand")
AVATAR = os.path.join(BRAND, "saltmire_icon.png")
BANNER = os.path.join(BRAND, "saltmire_logo_wide.png")
PDS = "https://bsky.social"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SaltmireBot/1.0"

DISPLAY_NAME = "Saltmire"
DESCRIPTION = ("Game-feel tools & templates for Godot 4. Free & open-source core.\n"
               "Tutorials: saltmire.github.io\nTools: saltmire.itch.io")


def creds():
    lines = [l.strip() for l in open(KEY_FILE, encoding="utf-8") if l.strip()]
    return lines[0], lines[1]


def api(endpoint, payload=None, token=None, raw=None, ctype="application/json"):
    url = f"{PDS}/xrpc/{endpoint}"
    if raw is not None:
        data = raw
    else:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
    method = "POST" if data is not None else "GET"
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("User-Agent", UA)
    if data is not None:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def upload_blob(path, token):
    with open(path, "rb") as f:
        data = f.read()
    res = api("com.atproto.repo.uploadBlob", token=token, raw=data, ctype="image/png")
    return res["blob"]


def main():
    handle, app_pw = creds()
    sess = api("com.atproto.server.createSession",
               {"identifier": handle, "password": app_pw})
    token, did = sess["accessJwt"], sess["did"]

    avatar_blob = upload_blob(AVATAR, token)
    banner_blob = upload_blob(BANNER, token)

    record = {
        "$type": "app.bsky.actor.profile",
        "displayName": DISPLAY_NAME,
        "description": DESCRIPTION,
        "avatar": avatar_blob,
        "banner": banner_blob,
    }
    try:
        api("com.atproto.repo.putRecord", {
            "repo": did,
            "collection": "app.bsky.actor.profile",
            "rkey": "self",
            "record": record,
        }, token=token)
    except urllib.error.HTTPError as e:
        sys.exit(f"putRecord error {e.code}: {e.read().decode(errors='replace')}")

    print(f"profile updated for {handle}: name={DISPLAY_NAME!r}, avatar+banner set.")


if __name__ == "__main__":
    main()
