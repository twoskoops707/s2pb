#!/usr/bin/env python3
"""Export everything installed in Claude Code (plugins, skills, commands,
agents, hooks, MCP + LSP servers) with full descriptions and live status,
for the Skills Index Android app.

    python3 tools/export_catalog.py            # full run, incl. MCP health checks (~1-2 min)
    python3 tools/export_catalog.py --fast     # skip MCP health checks, reuse last results
    python3 tools/export_catalog.py --out PATH # default: shared storage file the app reads

Run automatically by the Claude Code SessionStart hook and by
tools/s2pb_server.py (POST /refresh).
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

CLAUDE = Path.home() / ".claude"
AGENTS_DIR = CLAUDE / "agents"
DEFAULT_OUT = Path("/storage/emulated/0/Public/skills-catalog-sync.json")
BODY_CHARS = 1500

# Division categorization — mirrors the agency-agents repo layout.
SPATIAL_SLUGS = {
    "macos-spatial-metal-engineer", "terminal-integration-specialist",
    "visionos-spatial-engineer", "xr-cockpit-interaction-specialist",
    "xr-immersive-developer", "xr-interface-architect",
}
GAMEDEV_SLUGS = {
    "blender-addon-engineer", "economy-designer", "game-audio-engineer",
    "game-designer", "godot-gameplay-scripter", "godot-multiplayer-engineer",
    "godot-shader-developer", "level-designer", "narrative-designer",
    "roblox-avatar-creator", "roblox-experience-designer",
    "roblox-systems-scripter", "technical-artist", "unity-architect",
    "unity-editor-tool-developer", "unity-multiplayer-engineer",
    "unity-shader-graph-artist", "unreal-multiplayer-architect",
    "unreal-systems-engineer", "unreal-technical-artist", "unreal-world-builder",
}
PREFIX_CAT = {
    "academic-": "Academic", "design-": "Design", "engineering-": "Engineering",
    "finance-": "Finance", "gis-": "GIS", "healthcare-": "Healthcare",
    "marketing-": "Marketing", "paid-media-": "Paid Media", "product-": "Product",
    "project-management-": "Project Mgmt", "research-": "Research",
    "sales-": "Sales", "security-": "Security", "support-": "Support",
    "testing-": "Testing",
}
SPECIALIZED_EXTRA = {
    "accounts-payable-agent", "agentic-identity-trust", "agents-orchestrator",
    "automation-governance-architect", "business-strategist",
    "change-management-consultant", "chief-financial-officer",
    "corporate-training-designer", "customer-service", "customer-success-manager",
    "data-consolidation-agent", "data-privacy-officer", "esg-sustainability-officer",
    "government-digital-presales-consultant", "grant-writer",
    "healthcare-aging-parent-care-companion", "healthcare-customer-service",
    "healthcare-marketing-compliance", "hospitality-guest-services",
    "hr-onboarding", "identity-graph-operator", "language-translator",
    "legal-billing-time-tracking", "legal-client-intake", "legal-document-review",
    "loan-officer-assistant", "lsp-index-engineer", "ma-integration-manager",
    "medical-billing-coding-specialist", "operations-manager",
    "organizational-psychologist", "personal-growth-mentor",
    "real-estate-buyer-seller", "recruitment-specialist",
    "report-distribution-agent", "resume-tailor", "retail-customer-returns",
    "sales-data-extraction-agent", "sales-outreach", "project-manager-senior",
}

def categorize(slug: str) -> str:
    if slug in SPATIAL_SLUGS:
        return "Spatial Computing"
    if slug in GAMEDEV_SLUGS:
        return "Game Dev"
    if slug in SPECIALIZED_EXTRA or slug.startswith("specialized-"):
        return "Specialized"
    for prefix, cat in PREFIX_CAT.items():
        if slug.startswith(prefix):
            return cat
    return "Other"


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def flat(s):
    return re.sub(r"\s+", " ", s or "").strip()


def read_md(path):
    """(description, plain-text body excerpt) from a markdown file with optional frontmatter."""
    try:
        txt = Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "", ""
    desc, body = "", txt
    m = re.match(r"---\s*\n(.*?)\n---\s*\n?", txt, re.S)
    if m:
        body = txt[m.end():]
        out, grab = [], False
        for line in m.group(1).splitlines():
            if grab:
                if re.match(r"^\S", line):
                    break
                out.append(line.strip())
            elif line.startswith("description:"):
                v = line[len("description:"):].strip()
                if v not in ("|", ">", "|-", ">-", ""):
                    out.append(v.strip("\"'"))
                grab = True
        desc = flat(" ".join(out)).replace("\\n", " ")
    body = re.sub(r"```.*?```", " ", body, flags=re.S)          # drop code blocks
    body = re.sub(r"<[^>]+>", " ", body)                         # drop tags
    body = re.sub(r"^[#>*\-\s|]+", "", body, flags=re.M)         # md line markers
    body = re.sub(r"[*_`]|\[([^\]]*)\]\([^)]*\)", r"\1", body)   # emphasis, links -> text
    body = flat(body)
    if not desc:
        desc, body = body[:200], body[200:]
    return desc, body[:BODY_CHARS]


def plugin_roots():
    roots = []
    inst = load(CLAUDE / "plugins/installed_plugins.json") or {}
    for key, v in inst.get("plugins", inst).items():
        v = v[0] if isinstance(v, list) else v
        roots.append((key.split("@")[0], v["installPath"]))
    for d in glob.glob(str(CLAUDE / "plugins/synced/*/*/")):
        name = os.path.basename(d.rstrip("/")).split("~")[0]
        if not name.startswith(".") and not d.rstrip("/").endswith(".json"):
            roots.append((name, d.rstrip("/")))
    return roots


MARKETPLACE = {}
for mp in glob.glob(str(CLAUDE / "plugins/marketplaces/*/.claude-plugin/marketplace.json")):
    for e in (load(mp) or {}).get("plugins", []):
        MARKETPLACE.setdefault(e.get("name"), e)


def manifest(root, name):
    for p in (f"{root}/.claude-plugin/plugin.json", f"{root}/plugin.json"):
        m = load(p)
        if m:
            return {**MARKETPLACE.get(name, {}), **m}
    return MARKETPLACE.get(name, {})


def as_list(x):
    return x if isinstance(x, list) else [x]


def mcp_of(root, m):
    out = []
    for s in [s for s in as_list(m.get("mcpServers")) if s] or [".mcp.json"]:
        if isinstance(s, str):
            s = load(os.path.join(root, s)) or {}
        s = s.get("mcpServers", s) if isinstance(s, dict) else {}
        for k, v in s.items():
            if isinstance(v, dict):
                where = v.get("url") or " ".join([v.get("command", "")] + [str(a) for a in v.get("args", [])])
                out.append((k, flat(where)))
    return out


def hooks_of(root, m):
    out = []
    for h in [h for h in as_list(m.get("hooks")) if h] or ["hooks/hooks.json"]:
        if isinstance(h, str):
            h = load(os.path.join(root, h)) or {}
        h = h.get("hooks", h) if isinstance(h, dict) else {}
        for event, groups in h.items():
            for g in groups if isinstance(groups, list) else []:
                for hk in g.get("hooks", []) if isinstance(g, dict) else []:
                    out.append((event, g.get("matcher", ""),
                                hk.get("description") or g.get("description") or "",
                                hk.get("command") or hk.get("type", "")))
    return out


def lsp_of(root, m):
    s = m.get("lspServers") or load(f"{root}/.lsp.json") or {}
    if isinstance(s, str):
        s = load(os.path.join(root, s)) or {}
    return s if isinstance(s, dict) else {}


def run(cmd, timeout):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except Exception:
        return ""


def plugin_status():
    """{plugin name: entry from `claude plugin list --json`}"""
    try:
        return {p["id"].split("@")[0]: p for p in json.loads(run(["claude", "plugin", "list", "--json"], 60))}
    except Exception:
        return {}


MCP_LINE = re.compile(r"^(.+?): (.+) - (✔|✘|!|✗|⚠)?\s*(.+)$")


def mcp_health():
    """{server name as `claude mcp list` prints it: (status, detail)}"""
    out = {}
    for line in run(["claude", "mcp", "list"], 300).splitlines():
        m = MCP_LINE.match(line.strip())
        if not m:
            continue
        name, text = m.group(1), m.group(4)
        low = text.lower()
        if "not configured" in low:
            st = "not-configured"
        elif "connected" in low and "fail" not in low:
            st = "connected"
        elif "auth" in low:
            st = "needs-auth"
        elif "fail" in low or "error" in low:
            st = "failed"
        else:
            st = "unknown"
        err = text.split("—", 1)[1].strip() if "—" in text else ("" if st == "connected" else text)
        out[name] = (st, err, re.sub(r"\s*\((HTTP|SSE|stdio)\)$", "", m.group(2).strip()))
    return out


def item(k, n, s, g, d="", body="", src="", status="", err="", **meta):
    return {"k": k, "n": n, "s": s, "g": g, "d": d, "body": body, "src": src,
            "status": status, "err": err, "meta": {k2: v for k2, v in meta.items() if v}}


def build(fast, previous):
    items = []
    pstat = plugin_status()
    health = None if fast else mcp_health()
    if health is None:  # reuse last known MCP health
        health = {i["meta"].get("key"): (i["status"], i["err"], i["meta"].get("endpoint", ""))
                  for i in previous.get("items", []) if i["k"] == "mcp" and i["meta"].get("key")}
    health = {k: v for k, v in health.items() if k}
    by_url = {v[2]: v for v in health.values() if v[2]}

    def status_of(key, where):
        return health.get(key) or by_url.get(where) or ("unknown", "", "")

    for name, root in plugin_roots():
        m = manifest(root, name)
        ps = pstat.get(name, {})
        status = ("enabled" if ps.get("enabled") else "disabled") if ps else "synced"
        author = m.get("author", {})
        n_before = len(items)
        for p in sorted(glob.glob(f"{root}/skills/**/SKILL.md", recursive=True)):
            slug = os.path.basename(os.path.dirname(p))
            d, body = read_md(p)
            items.append(item("skill", slug, f"{name}:{slug}", name, d, body, p))
        for p in sorted(glob.glob(f"{root}/commands/**/*.md", recursive=True)):
            slug = Path(p).stem
            d, body = read_md(p)
            items.append(item("command", "/" + slug, f"/{name}:{slug}", name, d, body, p))
        for p in sorted(glob.glob(f"{root}/agents/**/*.md", recursive=True)):
            slug = Path(p).stem
            d, body = read_md(p)
            items.append(item("agent", slug, f"{name}:{slug}", name, d, body, p))
        for event, matcher, desc, cmd in hooks_of(root, m):
            items.append(item("hook", event + (f" · {matcher}" if matcher else ""), f"{name}:{event}", name,
                              flat(desc) or f"Runs on {event}", flat(cmd), root, event=event, matcher=matcher))
        for srv, where in mcp_of(root, m):
            key = f"plugin:{name}:{srv}"
            st, err, _ = status_of(key, where)
            items.append(item("mcp", srv, key, name, f"MCP server from the {name} plugin", where, root,
                              st, err, key=key, endpoint=where))
        for srv, cfg in lsp_of(root, m).items():
            langs = ", ".join(sorted(set(cfg.get("extensionToLanguage", {}).values())))
            items.append(item("lsp", srv, f"{name}:{srv}", name, f"Language server for {langs}",
                              flat(" ".join([cfg.get("command", "")] + cfg.get("args", []))), root))
        counts = {}
        for i in items[n_before:]:
            counts[i["k"]] = counts.get(i["k"], 0) + 1
        items.append(item("plugin", name, ps.get("id", name), name, flat(m.get("description", "")),
                          ", ".join(f"{v} {k}s" for k, v in sorted(counts.items())), root, status,
                          version=ps.get("version") or m.get("version"),
                          author=author.get("name") if isinstance(author, dict) else author,
                          installed=ps.get("installedAt"), updated=ps.get("lastUpdated"),
                          homepage=m.get("homepage") or m.get("repository")))

    # user-level skills, agents, MCP servers, hooks
    for p in sorted(glob.glob(str(CLAUDE / "skills/*/SKILL.md"))):
        slug = os.path.basename(os.path.dirname(p))
        d, body = read_md(p)
        items.append(item("skill", slug, slug, "Your skills", d, body, p))
    for p in sorted(AGENTS_DIR.glob("*.md")):
        d, body = read_md(p)
        nm = re.search(r"^name:\s*(.+)$", p.read_text(encoding="utf-8", errors="replace"), re.M)
        items.append(item("agent", nm.group(1).strip().strip("\"'") if nm else p.stem, p.stem,
                          categorize(p.stem), d, body, str(p)))
    seen = {i["meta"].get("key") for i in items if i["k"] == "mcp"}
    for srv, cfg in ((load(Path.home() / ".claude.json") or {}).get("mcpServers", {})).items():
        where = flat(cfg.get("url") or " ".join([cfg.get("command", "")] + cfg.get("args", [])))
        st, err, _ = status_of(srv, where)
        seen.add(srv)
        items.append(item("mcp", srv, srv, "Your MCP servers", "MCP server from your Claude Code config",
                          where, "~/.claude.json", st, err, key=srv, endpoint=where))
    for key, (st, err, where) in health.items():  # claude.ai connectors etc.
        if key not in seen:
            grp = "claude.ai" if key.startswith("claude.ai ") else "Other"
            items.append(item("mcp", key.replace("claude.ai ", ""), key, grp,
                              "Connector from your claude.ai account" if grp == "claude.ai" else "MCP server",
                              where, "", st, err, key=key, endpoint=where))
    for event, groups in ((load(CLAUDE / "settings.json") or {}).get("hooks", {})).items():
        for g in groups:
            for hk in g.get("hooks", []):
                items.append(item("hook", event, f"settings:{event}", "Your settings", f"Runs on {event}",
                                  flat(hk.get("command", "")), str(CLAUDE / "settings.json"), event=event))
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="skip MCP health checks")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args()
    previous = load(a.out) or {}
    if isinstance(previous, list):  # v1 file
        previous = {}
    items = build(a.fast, previous)
    stats = {}
    for i in items:
        stats[i["k"]] = stats.get(i["k"], 0) + 1
    data = {"v": 2, "generated": int(time.time()),
            "mcpChecked": previous.get("mcpChecked") if a.fast else int(time.time()),
            "stats": stats, "items": items}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = a.out.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, a.out)  # atomic: the app never reads a half-written file
    print(f"wrote {len(items)} entries to {a.out}: {stats}")


if __name__ == "__main__":
    main()
