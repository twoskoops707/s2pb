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

License: MIT.
