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
.bundle{margin:24px 0 34px;padding:20px;background:var(--card);border:1px solid var(--accent);border-radius:8px}
.bundle .was{color:var(--muted);text-decoration:line-through;margin-left:8px;font-weight:400;font-size:16px}
.bundle .now{color:var(--accent);font-size:26px;font-weight:700}
.bundle .off{color:var(--fg);background:#173a26;border:1px solid var(--accent);border-radius:4px;
padding:2px 7px;font-size:12px;margin-left:8px;vertical-align:middle}
.tools{list-style:none;padding:0;margin:0}
.tools li{padding:16px 0;border-bottom:1px solid var(--border);display:flex;gap:16px;
align-items:baseline;flex-wrap:wrap}
.tools .name{color:#fff;font-weight:600;font-size:17px;flex:1 1 260px}
.tools .price{color:var(--accent);font-weight:700;white-space:nowrap;font-variant-numeric:tabular-nums}
.tools .price.free{color:var(--muted);font-weight:400}
.tools .blurb{color:var(--muted);flex:1 1 100%;margin:0;font-size:15px}
.tools .lite,.tools .tut{font-size:13px}
.tools .meta{flex:1 1 100%;display:flex;gap:18px;flex-wrap:wrap;margin-top:2px}
.tools pre{flex:1 1 100%;margin:10px 0 4px;font-size:13px;padding:10px 13px}
.badge{background:#173a26;border:1px solid var(--accent);color:var(--accent);
border-radius:4px;padding:2px 7px;font-size:12px;white-space:nowrap}
.compat{color:var(--muted);font-size:14px;margin:-6px 0 22px}
"""

HEAD = """<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="google-site-verification" content="NRdTRCtBSnyvD3n-5LdnRtloOkbNX9RzroWI8vIDe3A">
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
<nav class="site"><a href="{base}/">Home</a><a href="{base}/tools.html">Tools &amp; templates</a>
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
            v = v.strip()
            # Tira aspas envolventes do valor. Sem isto, `title: "Foo"` virava literalmente
            # <title>"Foo"</title> no HTML (e no Dev.to/Bluesky) -- aspas visiveis no
            # resultado de busca. 3 dos 6 posts sairam assim ate 17/07/2026, porque cada
            # sessao escrevia o front-matter com ou sem aspas e o parser passava adiante.
            # Corrigir aqui vale pra todo post, escrito por quem for.
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1].strip()
            meta[k.strip()] = v
    meta["body_md"] = m.group(2).strip()
    meta["_file"] = os.path.basename(path)
    return meta


def utm(url, slug, medium="cta"):
    """Tag an outbound product link so itch's analytics attributes the source."""
    sep = "&" if "?" in url else "?"
    return (f"{url}{sep}utm_source=saltmire-blog&utm_medium={medium}"
            f"&utm_campaign={slug}")


def render_body(meta):
    body = markdown.markdown(meta["body_md"], extensions=["fenced_code", "tables"])
    if meta.get("product_url") and meta.get("product_name"):
        link = utm(meta["product_url"], meta["slug"])
        body += (
            f'<div class="cta">Built this the long way once too many times. '
            f'<b>{html.escape(meta["product_name"])}</b> does it as a drop-in tool: '
            f'<a href="{link}" data-product="{html.escape(meta["product_name"])}" '
            f'class="product-cta">{meta["product_url"]}</a></div>'
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


# ---------------------------------------------------------------- tools page
# Precos, nomes e URLs vem do data.js que o dashboard ja coleta do itch, para a
# pagina nunca discordar da loja. So os textos ficam aqui, porque sao copy.
DATA_JS = os.path.join(HERE, "..", "dashboard", "data.js")

BUNDLE = {
    "url": "https://itch.io/s/196174/saltmire-complete-launch-bundle",
    "name": "Saltmire Complete \u2014 Launch Bundle",
    "price": 19.80,
    "full": 31.96,
    "blurb": "All four paid tools in one purchase: Survivors Template, Impact, "
             "Hitbox and Save.",
}

GODOT_VERSION = "4.6"   # de config/features nos project.godot dos addons

BLURBS = {
    "survivors-template-godot":
        "A complete, data-driven survivors-like template for Godot 4.6 \u2014 with a playable web demo.",
    "saltmire-impact":
        "One-call game feel for Godot 4: shake, hit-stop, flash, damage numbers & FX combined "
        "into simple combo calls.",
    "saltmire-hitbox":
        "Drop-in Hitbox2D / Hurtbox2D for Godot 4 \u2014 damage, teams, knockback and i-frames "
        "with zero collision-layer setup.",
    "saltmire-save":
        "One-line save/load for Godot 4 \u2014 encryption, schema migration, backup recovery, "
        "gzip compression & smart autosave.",
    "saltmire-juice":
        "Free MIT game-feel kit for Godot 4 \u2014 shake, hit-stop, flash and damage numbers "
        "in one call.",
    "saltmire-fx":
        "One-line 2D sprite shader effects for Godot 4 \u2014 dissolve, outline, hit-flash, "
        "freeze, hologram.",
    "saltmire-spark":
        "Free MIT one-call 2D particle bursts for Godot 4 \u2014 sparks, pickups, explosions, "
        "dust & confetti in one line.",
    "saltmire-trail":
        "Free MIT motion-trail tool for Godot 4. Attach fading afterimages to any sprite in one "
        "call \u2014 dashes, speed, juice.",
    "saltmire-transitions-scene-transition-kit-for-godot-4":
        "Free MIT scene-transition manager for Godot 4 \u2014 fade, iris, wipes, pixelate in "
        "one line.",
    "saltmire-hitbox-lite":
        "Free MIT Hitbox2D / Hurtbox2D for Godot 4 \u2014 damage, teams, knockback, i-frames "
        "with zero collision-layer setup.",
    "saltmire-save-lite":
        "One-line save/load for Godot 4 \u2014 free, MIT. Write & read game state in a single call.",
}

# A promessa de todo produto e "uma linha". Mostrar a linha e a prova.
# Cada snippet foi COPIADO da API real do addon (addons/*/*.gd e demo/demo.gd).
# Nao inventar assinatura aqui: se a API mudar, corrigir junto.
SNIPPETS = {
    "saltmire-impact": "Impact.hit(sprite, camera, 12)",
    "saltmire-hitbox": "$Hitbox2D.activate()",
    "saltmire-save": 'Save.write("slot1", {"hp": 80, "level": 3})',
    "saltmire-juice": "Juice.shake(camera)",
    "saltmire-fx": "FX.outline(sprite, Color(1, 0.9, 0.2), 2.0)",
    "saltmire-spark": "Spark.at(enemy)",
    "saltmire-trail": "Trail.attach(sprite)",
    "saltmire-transitions-scene-transition-kit-for-godot-4":
        'Transitions.to("res://level2.tscn", "iris")',
}

# So os que REALMENTE tem demo jogavel na pagina do itch (conferido 03/09/2026).
DEMOS = {"survivors-template-godot", "saltmire-juice"}

LITE_OF = {
    "saltmire-hitbox": "saltmire-hitbox-lite",
    "saltmire-save": "saltmire-save-lite",
}


def slug_of(url):
    return url.rstrip("/").rsplit("/", 1)[-1]


def read_products():
    """Le o data.js do dashboard. Devolve [] se nao existir -- a pagina de tools
    e opcional e nunca pode derrubar o build do blog."""
    import json
    try:
        raw = open(DATA_JS, encoding="utf-8").read()
    except OSError:
        print("  ! data.js nao encontrado; pulando tools.html")
        return []
    try:
        data = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
    except (ValueError, IndexError):
        print("  ! data.js ilegivel; pulando tools.html")
        return []
    out = []
    for pr in data.get("products", []):
        if not pr.get("published"):
            continue
        pr["slug"] = slug_of(pr["url"])
        pr["blurb"] = BLURBS.get(pr["slug"], "")
        out.append(pr)
    return out


def tool_row(pr, by_slug):
    link = utm(pr["url"], pr["slug"], medium="tools")
    price = ('<span class="price">${:.2f}</span>'.format(pr["price"]) if pr["paid"]
             else '<span class="price free">Free \u00b7 MIT</span>')
    badge = '<span class="badge">Playable demo</span>' if pr["slug"] in DEMOS else ""
    snip = SNIPPETS.get(pr["slug"])
    code = "<pre><code>{}</code></pre>".format(html.escape(snip)) if snip else ""

    meta = []
    lite_slug = LITE_OF.get(pr["slug"])
    if lite_slug and lite_slug in by_slug:
        lp = by_slug[lite_slug]
        meta.append('<span class="lite">Free version: <a href="{}">{}</a></span>'.format(
            utm(lp["url"], lp["slug"], medium="tools"), html.escape(lp["name"])))
    meta_html = '<div class="meta">{}</div>'.format("".join(meta)) if meta else ""

    return ('<li><a class="name" href="{}">{}</a>{}{}<p class="blurb">{}</p>{}{}</li>'.format(
        link, html.escape(pr["name"]), price, badge,
        html.escape(pr["blurb"]), code, meta_html))


def build_tools(products, posts):
    if not products:
        return False
    by_slug = {pr["slug"]: pr for pr in products}
    lite_slugs = set(LITE_OF.values())
    paid = sorted([pr for pr in products if pr["paid"]], key=lambda pr: -pr["price"])
    free = sorted([pr for pr in products
                   if not pr["paid"] and pr["slug"] not in lite_slugs],
                  key=lambda pr: -pr.get("views", 0))

    off = round((1 - BUNDLE["price"] / BUNDLE["full"]) * 100)
    each = BUNDLE["price"] / 4
    body = (
        "<h1>Godot 4 tools &amp; templates</h1>"
        "<p>Small, drop-in addons for Godot 4. Every paid tool has a free version, "
        "so you can try the approach before paying for anything.</p>"
        '<p class="compat">Godot {} \u00b7 full source included \u00b7 MIT free versions</p>'.format(GODOT_VERSION) +
        '<div class="bundle"><div><b>{}</b></div>'.format(html.escape(BUNDLE["name"])) +
        '<p class="blurb">{}</p>'.format(html.escape(BUNDLE["blurb"])) +
        '<span class="now">${:.2f}</span>'.format(BUNDLE["price"]) +
        '<span class="was">${:.2f}</span>'.format(BUNDLE["full"]) +
        '<span class="off">save {}% \u2014 ${:.2f} per tool</span> &nbsp; '.format(off, each) +
        '<a href="{}">Get the bundle</a></div>'.format(
            utm(BUNDLE["url"], "complete-bundle", medium="tools")) +
        "<h2>Paid tools</h2>" +
        '<ul class="tools">{}</ul>'.format(
            "".join(tool_row(pr, by_slug) for pr in paid)) +
        "<h2>Free tools (MIT)</h2>" +
        '<ul class="tools">{}</ul>'.format(
            "".join(tool_row(pr, by_slug) for pr in free)) +
        '<div class="cta">Questions before buying, or a problem with an order? '
        "Email <b>saltmiregames@gmail.com</b> \u2014 I answer every one.</div>"
    )
    url = "{}/tools.html".format(BASE_URL)
    desc = ("Godot 4 addons and templates by Saltmire \u2014 hitbox, save/load, game feel, "
            "particles, shaders and a survivors template. Free MIT versions included.")
    head = HEAD.format(title="Godot 4 tools & templates \u2014 Saltmire",
                       desc=html.escape(desc), canonical=url, og_type="website",
                       site=SITE_NAME, css=CSS, base=BASE_URL,
                       tagline=html.escape(TAGLINE), jsonld="")
    open(os.path.join(HERE, "tools.html"), "w", encoding="utf-8").write(head + body + FOOT)
    print("built tools.html ({} paid, {} free, {} snippets)".format(
        len(paid), len(free),
        sum(1 for pr in products if SNIPPETS.get(pr["slug"]))))
    return True


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

    has_tools = build_tools(read_products(), posts)

    # sitemap
    urls = [f"{BASE_URL}/"] + [f"{BASE_URL}/{p['slug']}.html" for p in posts]
    if has_tools:
        urls.append(f"{BASE_URL}/tools.html")
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
