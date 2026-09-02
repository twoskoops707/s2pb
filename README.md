# s2pb — Skills Index

Searchable, category-filtered index of installed Claude Code subagents
(from [agency-agents](https://github.com/msitarzewski/agency-agents)) plus
Claude Code's built-in skills. Built as a Claude Design canvas.

- `Main.dc.html` — the app (search box + category chips + list), Design
  Component source.
- `canvas.json` — canvas layout / launch view for the design editor.
- `catalog.json` — the indexed data (290 entries: 273 agents + 17 skills).
- `skills-index.html` — the seeded, published artifact page.

Live: https://claude.ai/code/artifact/eb630a23-678d-4e75-af78-353b32c6608f

## Android app

`app/` is a minimal WebView wrapper (`MainActivity.java`) around a standalone
copy of the same catalog UI (`app/src/main/assets/index.html` — plain HTML/JS,
no editor chrome, works fully offline). The `Build APK` GitHub Actions
workflow (`.github/workflows/build-apk.yml`) compiles it on every push to
`main` and uploads `app-debug.apk` as a workflow artifact — check the
Actions tab for the download.

### Resyncing the catalog

There's no live connection between an installed Android app and a Claude
Code install — the app reads a JSON file you export instead:

1. After installing/removing agents or skills, run:
   ```
   python3 tools/export_catalog.py
   ```
   (writes to `/storage/emulated/0/Public/skills-catalog-sync.json` by
   default; pass a different path as the first argument).
2. In the app, tap **Sync** and pick that file. It's a one-time pick —
   Android grants a persistent permission to that file, so the app
   silently re-reads it on every later launch. Run step 1 again whenever
   the catalog changes, then relaunch the app (or tap Sync again if you
   picked a different file).

### Settings

Tap **Settings** for background color, text color (10 curated swatches
each), and font (System / Serif / Monospace). Applied live via CSS custom
properties in `index.html` — everything else (borders, muted text, chip
states) derives from those two colors with `color-mix()`, so there's no
way to end up with a broken-looking in-between state.

License: MIT.
