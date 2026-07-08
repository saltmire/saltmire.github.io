#!/usr/bin/env python3
"""Saltmire blog — tiny static site generator.

Reads posts/*.md (each with a simple `---` front-matter block) and emits:
  index.html, <slug>.html for every post, sitemap.xml, robots.txt, feed.xml
into this same folder (repo root -> served by GitHub Pages at BASE_URL).

No external services, no build daemon. Run:  python build.py
"""
import os
import re
import html
import datetime
import markdown

BASE_URL = "https://saltmire.github.io"
SITE_NAME = "Saltmire Devlog"
TAGLINE = "Practical Godot 4 tutorials — game feel, saving, and shipping polish fast."
HERE = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(HERE, "posts")

CSS = """
:root{--bg:#0b0f1a;--bg2:#0e1524;--fg:#e6eefc;--muted:#93a7c6;--accent:#7cfc98;--card:#121a2c;--border:#1e2a44}
*{box-sizing:border-box}
body{margin:0;background:linear-gradient(180deg,#0e1524,#090c14);color:var(--fg);
font:16px/1.7 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:760px;margin:0 auto;padding:0 20px}
header.site{padding:34px 0 10px}
header.site .brand{font-size:22px;font-weight:700;color:#fff}
header.site .tag{color:var(--muted);margin-top:4px}
nav.site{margin-top:14px;padding-bottom:18px;border-bottom:1px solid var(--border)}
nav.site a{color:var(--muted);margin-right:18px;font-size:14px}
main{padding:26px 0 10px}
h1{font-size:30px;line-height:1.25;color:#fff;margin:.2em 0 .3em}
h2{font-size:22px;color:#fff;margin-top:1.8em}
article time,.post-list time{color:var(--muted);font-size:13px}
pre{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px 16px;
overflow:auto;font-size:14px}
code{background:#0f1728;border:1px solid var(--border);border-radius:4px;padding:1px 5px;font-size:.92em}
pre code{background:none;border:none;padding:0}
.cta{margin:30px 0;padding:18px 20px;background:var(--card);border:1px solid var(--border);
border-left:3px solid var(--accent);border-radius:8px}
.cta b{color:#fff}
.post-list{list-style:none;padding:0}
.post-list li{padding:18px 0;border-bottom:1px solid var(--border)}
.post-list a.title{font-size:19px;color:#fff;font-weight:600}
.post-list p{color:var(--muted);margin:.4em 0 0}
footer.site{margin-top:40px;padding:26px 0;border-top:1px solid var(--border);color:var(--muted);font-size:13px}
"""

HEAD = """<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="{og_type}"><meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}"><meta property="og:url" content="{canonical}">
<meta property="og:site_name" content="{site}">
<meta name="twitter:card" content="summary">
<style>{css}</style>
{jsonld}
</head><body><div class="wrap">
<header class="site"><div class="brand">Saltmire</div>
<div class="tag">{tagline}</div>
<nav class="site"><a href="{base}/">Home</a><a href="https://saltmire.itch.io">Tools &amp; templates</a>
<a href="https://github.com/saltmire">GitHub</a></nav></header><main>
"""

FOOT = """</main><footer class="site">
Saltmire — small, honest, drop-in tools for Godot 4.
<a href="https://saltmire.itch.io">saltmire.itch.io</a>.
Built with AI assistance, reviewed by hand. No AI art or audio.
</footer></div></body></html>"""


def parse_post(path):
    raw = open(path, encoding="utf-8").read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.S)
    if not m:
        raise ValueError(f"missing front matter in {path}")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    meta["body_md"] = m.group(2).strip()
    meta["_file"] = os.path.basename(path)
    return meta


def render_body(meta):
    body = markdown.markdown(meta["body_md"], extensions=["fenced_code", "tables"])
    if meta.get("product_url") and meta.get("product_name"):
        body += (
            f'<div class="cta">Built this the long way once too many times. '
            f'<b>{html.escape(meta["product_name"])}</b> does it as a drop-in tool: '
            f'<a href="{meta["product_url"]}">{meta["product_url"]}</a></div>'
        )
    return body


def jsonld_article(meta, url):
    return (
        '<script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"Article",'
        f'"headline":{escape_json(meta["title"])},'
        f'"description":{escape_json(meta["description"])},'
        f'"datePublished":"{meta["date"]}","author":{{"@type":"Organization","name":"Saltmire"}},'
        f'"publisher":{{"@type":"Organization","name":"Saltmire"}},'
        f'"mainEntityOfPage":"{url}"}}'
        "</script>"
    )


def escape_json(s):
    import json
    return json.dumps(s)


def build():
    posts = [parse_post(os.path.join(POSTS_DIR, f))
             for f in os.listdir(POSTS_DIR) if f.endswith(".md")]
    posts.sort(key=lambda p: p["date"], reverse=True)

    for p in posts:
        url = f"{BASE_URL}/{p['slug']}.html"
        head = HEAD.format(title=html.escape(p["title"]), desc=html.escape(p["description"]),
                           canonical=url, og_type="article", site=SITE_NAME,
                           css=CSS, base=BASE_URL, tagline=html.escape(TAGLINE),
                           jsonld=jsonld_article(p, url))
        art = (f'<article><h1>{html.escape(p["title"])}</h1>'
               f'<time datetime="{p["date"]}">{p["date"]}</time>'
               f'{render_body(p)}</article>')
        open(os.path.join(HERE, f"{p['slug']}.html"), "w", encoding="utf-8").write(head + art + FOOT)

    # index
    items = ""
    for p in posts:
        items += (f'<li><a class="title" href="{BASE_URL}/{p["slug"]}.html">{html.escape(p["title"])}</a>'
                  f'<br><time datetime="{p["date"]}">{p["date"]}</time>'
                  f'<p>{html.escape(p["description"])}</p></li>')
    head = HEAD.format(title=f"{SITE_NAME} — Godot 4 tutorials", desc=html.escape(TAGLINE),
                       canonical=f"{BASE_URL}/", og_type="website", site=SITE_NAME,
                       css=CSS, base=BASE_URL, tagline=html.escape(TAGLINE), jsonld="")
    open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(
        head + f'<ul class="post-list">{items}</ul>' + FOOT)

    # sitemap
    urls = [f"{BASE_URL}/"] + [f"{BASE_URL}/{p['slug']}.html" for p in posts]
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sm += "".join(f"<url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n"
    open(os.path.join(HERE, "sitemap.xml"), "w", encoding="utf-8").write(sm)
    open(os.path.join(HERE, "robots.txt"), "w", encoding="utf-8").write(
        f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n")

    # RSS
    now = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    rss = ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
           f'<title>{SITE_NAME}</title><link>{BASE_URL}/</link>'
           f'<description>{html.escape(TAGLINE)}</description><lastBuildDate>{now}</lastBuildDate>')
    for p in posts:
        u = f"{BASE_URL}/{p['slug']}.html"
        rss += (f'<item><title>{html.escape(p["title"])}</title><link>{u}</link>'
                f'<guid>{u}</guid><description>{html.escape(p["description"])}</description></item>')
    rss += "</channel></rss>"
    open(os.path.join(HERE, "feed.xml"), "w", encoding="utf-8").write(rss)

    print(f"built {len(posts)} post(s) + index + sitemap + feed")


if __name__ == "__main__":
    build()
