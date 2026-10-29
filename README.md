# Battery Alert Pro — Landing Site

Static landing page and blog for **Battery Alert Pro**, a Windows battery management utility.

- **Live site:** https://battery-alert-pro.github.io/home/
- **Blog:** https://battery-alert-pro.github.io/home/blog/
- **Publisher:** Woteq Software
- **Stack:** plain HTML / CSS / JS, plus a small Python builder for the blog

## Repository layout

The site is published from the **repository root**. The hand-written pages are
served as they are; `tools/build.py` generates the blog into the same tree at
deploy time.

```
.
├── index.html                     # Landing page (entry point)
├── buy_now.html                   # Purchase instructions
├── 404.html                       # Custom "page not found" page
├── social_card.png                # 1200x630 social preview card (og:image)
├── blog.css                       # Styles for the blog pages
├── .nojekyll                      # Serve the branch as static files
├── _config.yml                    # Fallback config for the branch-based build
├── BatteryAlertPro_Setup.zip      # Installer (recommended download)
├── BatteryAlertProSetup.exe       # Installer (direct download)
├── user_manual.pdf                # 4-page user manual
├── image.png                      # Application icon / favicon
├── main_screen.png                # Screenshot — main settings
├── low_alert.png                  # Screenshot — low battery alert
├── high_alert.png                 # Screenshot — high battery alert
├── sys_tray.png                   # Screenshot — system tray
├── content/posts/                 # Blog posts (Markdown) — the source of truth
│   ├── windows-battery-warning-10-percent.md
│   ├── adhd-laptop-shutdown-lost-work.md
│   ├── best-battery-monitoring-software-windows-11.md
│   └── charging-laptop-to-100-battery-health.md
├── blog/                          # Generated — post and tag listings
├── posts/                         # Generated — one page per post
├── feed.xml                       # Generated — RSS feed
├── sitemap.xml                    # Generated — search engine sitemap
├── robots.txt                     # Generated — crawler directives
├── templates/                     # HTML templates for the blog
│   ├── base.html                  # Shared page skeleton
│   ├── post_body.html             # Single post
│   ├── blog_index_body.html       # Post listing
│   └── tag_index_body.html        # Tag listing
├── tools/
│   ├── build.py                   # Builds the blog
│   └── make_social_card.py        # Regenerates social_card.png
├── requirements.txt               # Build dependency (Python-Markdown)
├── .github/workflows/static.yml   # Pages deployment workflow
├── .gitattributes                 # LF normalisation, binary file types
├── .gitignore
└── README.md
```

These paths are **generated** by `tools/build.py` and are **committed**, so that
GitHub's branch-based Pages build can publish them as well:

```
blog/        posts/        feed.xml        sitemap.xml        robots.txt
```

Regenerate them whenever you change a post:

```bash
python3 tools/build.py && git add -A && git commit -m "Update blog"
```

The workflow also regenerates and commits them automatically, so a forgotten
local build will not leave the site stale.

## Deployment

The site is deployed by **GitHub Actions**, not by the legacy branch-based Pages build.

- `.github/workflows/static.yml` runs on every push to `main`.
- It installs the one build dependency, runs `tools/build.py`, removes the
  build-only files, and uploads the repository root as the Pages artifact.
- Because the artifact is uploaded as-is, **Jekyll is never involved** in this
  workflow — a `.nojekyll` file is therefore not required.

> **One thing to check in the repository settings.**
> Go to **Settings → Pages → Build and deployment → Source**. If it says
> *Deploy from a branch*, switch it to **GitHub Actions**. With the branch
> option selected, GitHub also runs its own build of `main` alongside this
> workflow, and the two compete for the live site. The repository is set up so
> both publish identical content — `.nojekyll` stops the branch build
> processing anything, and the generated blog is committed — but pointing
> Pages at **GitHub Actions** removes the ambiguity entirely.

To publish a change:

```bash
git add -A
git commit -m "Describe the change"
git push origin main
```

The workflow then redeploys automatically. You can watch the run under
**Actions → Deploy static content to Pages**.

> Note: everything in the repository root is published, so any file committed
> here ends up downloadable from the public site URL. Keep credentials and
> working files out of it (see `.gitignore`).

## Writing a new post

Posts are Markdown files in `content/posts/`. The filename becomes the URL slug,
unless you set `slug` in the front matter.

```markdown
---
title: "Your Post Title"
slug: your-post-title
date: 2026-11-04
description: "One or two sentences. This becomes the meta description, the
  social preview text and the RSS summary, so make it count."
keywords: "primary keyword, secondary keyword"
tags: [Battery Alerts, Windows 11]
---

Your article goes here. Standard Markdown: **bold**, *italic*, `code`,
[links](/posts/another-post/), lists, tables and fenced code blocks all work.
```

Things worth knowing:

- **Internal links are written site-root-relative** — `/posts/another-post/` or
  `/#download`. The builder rewrites them to page-relative paths, so the site
  keeps working from a repository root, a `docs/` folder, or a custom domain.
- **Tags** are comma-separated in the front matter (or a YAML list). Each tag
  gets its own page at `/blog/tag/<tag>/`.
- The landing page's "From the blog" list is **hand-written** in `index.html`.
  Add a link there when you publish something worth featuring; the blog index
  at `/blog/` lists everything regardless.

## Adding a new release

1. Replace `BatteryAlertPro_Setup.zip` and `BatteryAlertProSetup.exe` with the new
   build. Keep the file names — the download buttons link to them by name.
2. Update the size shown on the download button in `index.html` (`.zip` and `.exe`
   sizes are both listed).
3. Commit and push.

## Local preview

The blog needs Python-Markdown. Install it once, then build and serve from the
repository root:

```bash
pip install -r requirements.txt
python3 tools/build.py
python3 -m http.server 8080
# then open http://localhost:8080/
```

`tools/build.py` writes `blog/`, `posts/`, `feed.xml`, `sitemap.xml` and
`robots.txt` into the repository root. Run it and commit the result before
pushing.

## Notes

- `index.html` is UTF-8 encoded. The original file was latin-1 with a stray `0xA6`
  byte in the CSS list bullet; this has been corrected to a real `•` (U+2022).
- `BatteryAlertProSetup.exe` is a Windows PE binary. Some browsers and antivirus
  products flag raw `.exe` downloads, which is why the `.zip` is the primary button.
- The page loads Google Fonts and a `livetrafficfeed.com` visitor-counter widget from
  third-party CDNs. Remove the `<script>` in `index.html` if you would rather not
  include the counter.
- Social preview images must be **absolute** URLs, otherwise Facebook/Twitter/X will
  not render the preview card. They point at
  `https://battery-alert-pro.github.io/home/social_card.png`.
- `social_card.png` is generated by `tools/make_social_card.py` (requires Pillow and
  the Noto Sans fonts). Re-run it from the repository root after changing the branding:

  ```bash
  python3 tools/make_social_card.py
  ```

## After publishing

The site publishes `sitemap.xml`, `robots.txt` and `feed.xml` automatically. Once
the blog is live, register the sitemap in **Google Search Console** and submit
`https://battery-alert-pro.github.io/home/sitemap.xml`.
