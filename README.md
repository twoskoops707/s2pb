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

`app/` is a full-screen WebView around `app/src/main/assets/index.html` — a
dark, searchable index of everything installed in Claude Code: agents,
skills, slash commands, plugins, hooks, MCP servers and LSP servers, with
full descriptions and live status.

- **Search** covers names, descriptions *and* the body text of each skill /
  agent / command, with highlighted matches.
- **Tabs** per kind, chips per plugin/category, and a status filter on the
  MCP and Plugins tabs (connected / needs auth / failed / not configured,
  enabled / disabled), with the error text for anything that failed.
- **Tap any card** for the full description, contents, version, endpoint,
  source path and a copy button.
- **Settings** (gear): accent color, text size, manual sync-file picker,
  update check.

### Sync with Claude Code

Data comes from `tools/export_catalog.py`, which reads `~/.claude` plus
`claude plugin list --json` and `claude mcp list` (health checks).

1. A Claude Code **SessionStart hook** runs on every session:
   ```
   cd /root/s2pb && (nohup setsid sh -c 'python3 tools/export_catalog.py --fast; python3 tools/s2pb_server.py' > /tmp/s2pb.log 2>&1 &)
   ```
   It re-exports the catalog (skipping slow MCP health checks) and starts
   the local helper API if it isn't running.
2. **`tools/s2pb_server.py`** serves `127.0.0.1:8765` (loopback only):
   `GET /catalog`, `GET /status`, `POST /refresh` (full export incl. MCP
   health, ~1–2 min). The app's ↻ button calls `/refresh`.
3. The app loads, in order: live helper → the shared file
   (`/storage/emulated/0/Public/skills-catalog-sync.json`, picked once via
   Settings → *Choose sync file*) → the snapshot bundled in the APK. It
   reloads every time it comes to the foreground.

Manual export: `python3 tools/export_catalog.py` (full) or `--fast`.

### Builds and updates

`.github/workflows/build-apk.yml` builds on every push to `main`;
`versionCode` is the workflow run number. The app checks
`releases/latest` of this repo on launch and shows an *Update* banner when
a newer `v<run>` release with an `.apk` asset exists. `app/build.gradle`
signs release builds with the keystore given in `SIGNING_KEYSTORE` /
`SIGNING_PASSWORD` (falls back to debug signing).

License: MIT.
