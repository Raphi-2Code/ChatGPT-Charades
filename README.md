Codex did everything, so let's see

# Ursina CSS Charades (Static Site)

This folder is a self-contained, offline build (Brython + Ursina CSS) that can be hosted as static files.

## Run locally

```bash
python3 -m http.server 8000 --directory site
```

Open `http://localhost:8000/`.

## Host on GitHub Pages

Option A: separate repo (simplest)
1) Create a new repo and copy the contents of `site/` into the repo root.
2) In GitHub `Settings` -> `Pages`, set source to `main` branch and `/ (root)`.
3) Visit the published URL.

Option B: gh-pages branch from this repo
1) Push the contents of `site/` to a `gh-pages` branch.
2) In GitHub `Settings` -> `Pages`, set source to `gh-pages` and `/ (root)`.

## Host on Netlify

1) Create a new site in Netlify.
2) Drag-and-drop the `site/` folder, or configure the publish directory as `site/`.
3) Use the provided Netlify URL.

## Open on iPhone

1) Open the hosted URL in Safari.
2) Open the hosted site once, then Add to Home Screen; after that it works offline.
