#!/usr/bin/env python3
"""Regenerate the Skills Index app's catalog from the live ~/.claude/agents
directory plus Claude Code's built-in skills, and write it to shared
storage so the Android app's Sync button can pick it up.

Run this any time you install/remove Claude Code agents or skills, then
tap Sync in the app (first time: pick the file; after that it re-reads
the same picked file automatically on every launch).
"""
import json
import re
import sys
from pathlib import Path

AGENTS_DIR = Path.home() / ".claude" / "agents"
DEFAULT_OUT = Path("/storage/emulated/0/Public/skills-catalog-sync.json")

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

BUILTIN_SKILLS = [
    ("design", "Create a design canvas — a multi-artboard visual design published as an Artifact that runs Claude Design's canvas editor."),
    ("dataviz", "Use before creating any chart, graph, plot, dashboard, or data visualization in any medium."),
    ("artifact-design", "Design guidance and fundamentals for Artifacts. Load before writing any artifact."),
    ("artifact-diagramming", "Diagramming know-how for Artifacts — drawing mechanism diagrams and inline-SVG mechanics."),
    ("artifact-capabilities", "Runtime capabilities a published Artifact page can be granted — live data, saved state, shared state, user identity, file storage."),
    ("update-config", "Configure the Claude Code harness via settings.json — hooks, permissions, env vars."),
    ("keybindings-help", "Customize keyboard shortcuts, rebind keys, add chord bindings, modify keybindings.json."),
    ("code-review", "Review the current diff or a PR/branch for correctness bugs and simplification opportunities."),
    ("simplify", "Review changed code for reuse, simplification, efficiency, and apply the fixes."),
    ("fewer-permission-prompts", "Scan transcripts for common read-only tool calls and allowlist them in settings.json."),
    ("loop", "Run a prompt or slash command on a recurring interval, self-paced or fixed."),
    ("schedule", "Create, update, list, or run scheduled cloud agents (cron routines)."),
    ("claude-api", "Reference for the Claude API / Anthropic SDK — models, pricing, params, streaming, tool use."),
    ("claude-in-chrome", "Automate Chrome to click, fill forms, screenshot, and navigate sites."),
    ("run", "Launch and drive this project's app to see a change working in a real browser/CLI."),
    ("init", "Initialize a new CLAUDE.md file with codebase documentation."),
    ("security-review", "Complete a security review of the pending changes on the current branch."),
]


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


def parse_agent(path: Path):
    name = None
    desc = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("name: ") and name is None:
            name = line[len("name: "):].strip()
        if line.startswith("description: ") and desc is None:
            desc = line[len("description: "):].strip()
            desc = re.sub(r'^"|"$', "", desc)
        if name and desc:
            break
    slug = path.stem
    return {
        "n": name or slug,
        "s": slug,
        "c": categorize(slug),
        "d": desc or "",
        "k": "agent",
    }


def build_catalog():
    items = []
    if AGENTS_DIR.is_dir():
        for f in sorted(AGENTS_DIR.glob("*.md")):
            items.append(parse_agent(f))
    else:
        print(f"warning: {AGENTS_DIR} not found — no agents included", file=sys.stderr)

    for slug, desc in BUILTIN_SKILLS:
        items.append({"n": slug, "s": slug, "c": "Claude Code Skill", "d": desc, "k": "skill"})

    return items


def main():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    items = build_catalog()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(items, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {len(items)} entries to {out_path}")


if __name__ == "__main__":
    main()
