#!/usr/bin/env python3
"""Static site builder for the Battery Alert Pro site.

The hand-written pages (index.html, buy_now.html, 404.html) and all binary
assets already live at the repository root and are published as they are.
This script generates the blog alongside them:

    posts/<slug>/index.html    one page per post
    blog/index.html            post listing
    blog/tag/<tag>/index.html  per-tag listing
    sitemap.xml                 search engine sitemap
    feed.xml                    RSS 2.0 feed
    robots.txt                  crawler directives

Everything it writes is listed in .gitignore, so the generated output stays
out of version control while still being published.

Paths inside the generated pages are relative, so the site keeps working
from a repository root, a docs/ folder, or a custom domain.

Usage:
    python3 tools/build.py
"""

import datetime
import html
import json
import re
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content" / "posts"
TEMPLATES = ROOT / "templates"

SITE_URL = "https://battery-alert-pro.github.io/home"
SITE_NAME = "Battery Alert Pro"
PUBLISHER = "Woteq Software"

SLUG_RE = re.compile(r"[^a-z0-9]+")
DATE_FMT = "%Y-%m-%d"
WORDS_PER_MINUTE = 220


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def slugify(text):
    return SLUG_RE.sub("-", text.lower()).strip("-")


def parse_front_matter(text):
    """Split a leading `---` delimited block of `key: value` lines off the body."""
    if not text.startswith("---"):
        return {}, text.strip()

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text.strip()

    raw, body = parts[1], parts[2]
    meta = {}
    key = None
    for line in raw.strip().splitlines():
        if not line.strip():
            continue
        if line.startswith((" ", "\t")) and key:
            meta[key] += " " + line.strip()
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            value = [v.strip().strip("\"'") for v in value[1:-1].split(",") if v.strip()]
        elif len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        meta[key] = value
    return meta, body.strip()


def esc(text):
    """Escape a value for use in an HTML attribute or text node."""
    return html.escape(str(text), quote=True)


def rewrite_root_links(text, prefix):
    """Turn site-root-relative URLs into page-relative ones.

    The site is published under a subpath (`/home/`), so a link written as
    `/posts/foo/` would resolve to the domain root and 404. Rewriting to a
    relative path keeps it working from a repository root, a docs/ folder or
    a custom domain.
    """
    return re.sub(
        r'\b(href|src)="/(?!/)([^"]*)"',
        lambda m: f'{m.group(1)}="{prefix}{m.group(2)}"',
        text,
    )


def render_template(name, slots):
    """Fill `{{ name }}` slots in a template file."""
    source = (TEMPLATES / name).read_text(encoding="utf-8")

    def replace(match):
        key = match.group(1).strip()
        if key not in slots:
            raise KeyError(f"{name}: unknown slot {{{{{key}}}}}")
        return str(slots[key])

    return re.sub(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", replace, source)


def render_page(body_template, slots):
    """Render an inner template, then wrap it in the shared base layout."""
    base_slots = dict(slots)
    base_slots["content"] = render_template(body_template, slots)
    return render_template("base.html", base_slots)


def pretty_date(value):
    return datetime.datetime.strptime(value, DATE_FMT).strftime("%B %d, %Y").replace(" 0", " ")


def meta_tag(name, content, attr="name"):
    if not content:
        return ""
    return f'<meta {attr}="{name}" content="{html.escape(content, quote=True)}">'


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------
# build steps
# --------------------------------------------------------------------------
def load_posts():
    posts = []
    for path in sorted(CONTENT.glob("*.md")):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))

        slug = meta.get("slug") or slugify(meta.get("title", path.stem))
        date = meta.get("date", DATE_FMT)
        tags = meta.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        html_body = markdown.markdown(
            body,
            extensions=["extra", "toc", "sane_lists", "smarty"],
            output_format="html5",
        )

        words = len(body.split())

        posts.append(
            {
                "slug": slug,
                "title": meta.get("title", slug),
                "description": meta.get("description", ""),
                "date": date,
                "pretty_date": pretty_date(date),
                "tags": tags,
                "keywords": meta.get("keywords", ""),
                "body": html_body,
                "words": words,
                "reading_time": max(1, round(words / WORDS_PER_MINUTE)),
                "source": path.name,
            }
        )

    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def base_slots(post, prefix, url, og_type, published_time=""):
    return {
        "title": esc(f'{post["title"]} | {SITE_NAME}'),
        "description": esc(post["description"]),
        "keywords_meta": meta_tag("keywords", post.get("keywords", "")),
        "published_meta": meta_tag("article:published_time", published_time, attr="property"),
        "canonical": url,
        "og_image": f"{SITE_URL}/social_card.png",
        "og_type": og_type,
        "prefix": prefix,
        "jsonld": "",
    }


def build_post_pages(posts):
    for post in posts:
        prefix = "../../"
        url = f"{SITE_URL}/posts/{post['slug']}/"

        tags_html = "".join(
            f'<a class="tag" href="/blog/tag/{slugify(t)}/">{html.escape(t)}</a>'
            for t in post["tags"]
        )

        # Prefer posts that share tags, then fall back to most recent.
        scored = []
        for other in posts:
            if other["slug"] == post["slug"]:
                continue
            shared = len(set(post["tags"]) & set(other["tags"]))
            recency = 1 if other["date"] > post["date"] else 0
            scored.append((shared * 10 + recency, other))
        scored.sort(key=lambda item: item[0], reverse=True)

        related_html = ""
        if scored:
            items = "".join(
                f'<li><a href="/posts/{other["slug"]}/">{html.escape(other["title"])}</a>'
                f'<span class="muted"> &mdash; {other["pretty_date"]}</span></li>'
                for _, other in scored[:3]
            )
            related_html = (
                '<div class="related"><h2>Keep reading</h2>'
                f"<ul>{items}</ul></div>"
            )

        slots = base_slots(post, prefix, url, "article", post["date"])
        slots.update(
            {
                "h1": esc(post["title"]),
                "date": post["pretty_date"],
                "date_iso": post["date"],
                "reading_time": post["reading_time"],
                "tags_html": rewrite_root_links(tags_html, prefix),
                "body": rewrite_root_links(post["body"], prefix),
                "related_html": rewrite_root_links(related_html, prefix),
                "jsonld": json.dumps(
                    {
                        "@context": "https://schema.org",
                        "@type": "BlogPosting",
                        "headline": post["title"],
                        "description": post["description"],
                        "image": f"{SITE_URL}/social_card.png",
                        "datePublished": post["date"],
                        "dateModified": post["date"],
                        "author": {"@type": "Organization", "name": PUBLISHER},
                        "publisher": {"@type": "Organization", "name": PUBLISHER},
                        "mainEntityOfPage": url,
                        "wordCount": post["words"],
                    },
                    indent=2,
                ),
            }
        )

        write(
            ROOT / "posts" / post["slug"] / "index.html",
            render_page("post_body.html", slots),
        )


def build_blog_index(posts):
    items = "".join(
        f'<article class="post-card">'
        f'<h2><a href="/posts/{post["slug"]}/">{html.escape(post["title"])}</a></h2>'
        f'<p class="meta"><time datetime="{post["date"]}">{post["pretty_date"]}</time>'
        f' &middot; {post["reading_time"]} min read</p>'
        f'<p class="excerpt">{html.escape(post["description"])}</p>'
        f'<a class="read-more" href="/posts/{post["slug"]}/">Read article &rarr;</a>'
        f"</article>"
        for post in posts
    )

    slots = base_slots(
        {"title": "Blog", "description": "", "keywords": ""},
        "../",
        f"{SITE_URL}/blog/",
        "website",
    )
    slots.update(
        {
            "h1": "Blog",
            "lead": (
                "Guides on battery alerts, laptop longevity, and not losing the work "
                "you have already done."
            ),
            "items": rewrite_root_links(items, "../"),
        }
    )

    write(ROOT / "blog" / "index.html", render_page("blog_index_body.html", slots))


def build_tag_pages(posts):
    tags = {}
    for post in posts:
        for tag in post["tags"]:
            tags.setdefault(tag, []).append(post)

    for tag, tagged in tags.items():
        items = "".join(
            f'<li><a href="/posts/{post["slug"]}/">{html.escape(post["title"])}</a>'
            f'<span class="muted"> &mdash; {post["pretty_date"]}</span></li>'
            for post in tagged
        )

        slots = base_slots(
            {"title": tag, "description": "", "keywords": ""},
            "../../../",
            f"{SITE_URL}/blog/tag/{slugify(tag)}/",
            "website",
        )
        slots.update(
            {
                "h1": esc(f"Tagged: {tag}"),
                "items": rewrite_root_links(items, "../../../"),
            }
        )

        write(
            ROOT / "blog" / "tag" / slugify(tag) / "index.html",
            render_page("tag_index_body.html", slots),
        )


def build_sitemap(posts):
    urls = [
        (f"{SITE_URL}/", None, "1.0"),
        (f"{SITE_URL}/buy_now.html", None, "0.6"),
        (f"{SITE_URL}/blog/", None, "0.8"),
    ]
    for post in posts:
        urls.append((f"{SITE_URL}/posts/{post['slug']}/", post["date"], "0.9"))
    for tag in sorted({t for post in posts for t in post["tags"]}):
        urls.append((f"{SITE_URL}/blog/tag/{slugify(tag)}/", None, "0.4"))

    seen = set()
    parts = []
    for url, lastmod, priority in urls:
        if url in seen:
            continue
        seen.add(url)
        entry = f"  <url>\n    <loc>{html.escape(url)}</loc>\n"
        if lastmod:
            entry += f"    <lastmod>{lastmod}</lastmod>\n"
        entry += f"    <priority>{priority}</priority>\n  </url>"
        parts.append(entry)

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(parts)
        + "\n</urlset>\n"
    )
    write(ROOT / "sitemap.xml", xml)


def build_feed(posts):
    items = []
    for post in posts:
        pub = datetime.datetime.strptime(post["date"], DATE_FMT).strftime(
            "%a, %d %b %Y 00:00:00 +0000"
        )
        items.append(
            "<item>"
            f"<title>{html.escape(post['title'])}</title>"
            f"<link>{SITE_URL}/posts/{post['slug']}/</link>"
            f'<guid isPermaLink="true">{SITE_URL}/posts/{post["slug"]}/</guid>'
            f"<pubDate>{pub}</pubDate>"
            f"<description>{html.escape(post['description'])}</description>"
            f"<category>{html.escape(post['tags'][0] if post['tags'] else 'General')}</category>"
            "</item>"
        )

    # Deliberately derived from the newest post rather than the current time:
    # the generated output is committed, so a wall-clock timestamp would make
    # every build differ and trigger a commit on every push.
    newest = max((post["date"] for post in posts), default=DATE_FMT)
    last_build = datetime.datetime.strptime(newest, DATE_FMT).strftime(
        "%a, %d %b %Y %H:%M:%S +0000"
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">'
        "<channel>"
        f"<title>{SITE_NAME} Blog</title>"
        f"<link>{SITE_URL}/blog/</link>"
        "<description>Practical articles on battery alerts, laptop longevity, and "
        "protecting unsaved work.</description>"
        "<language>en-us</language>"
        f"<lastBuildDate>{last_build}</lastBuildDate>"
        f'<atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>'
        + "".join(items)
        + "</channel></rss>\n"
    )
    write(ROOT / "feed.xml", xml)


def build_robots():
    write(
        ROOT / "robots.txt",
        "User-agent: *\nAllow: /\n\n" f"Sitemap: {SITE_URL}/sitemap.xml\n",
    )


def main():
    posts = load_posts()
    build_post_pages(posts)
    build_blog_index(posts)
    build_tag_pages(posts)
    build_sitemap(posts)
    build_feed(posts)
    build_robots()

    print(f"built {len(posts)} posts")
    for post in posts:
        print(f"  /posts/{post['slug']}/  ({post['words']} words, {post['reading_time']} min)")


if __name__ == "__main__":
    main()
