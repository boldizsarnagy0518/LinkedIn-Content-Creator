---
name: manage-content-workflow
description: Capture raw content ideas, turn researched material into drafts, apply durable writing preferences, manage revision feedback, approve an exact content version, and record a human-confirmed publication handoff through the ContentOps MCP server. Use for idea-to-post requests, LinkedIn post drafting, draft review, rewrite feedback, approval, publication planning, or a safe LinkedIn-native handoff.
---

# Manage Content Workflow (Claude Code)

This project ships one host-independent workflow skill shared by Claude Code and Codex. Read and follow it in full before calling any ContentOps tool:

- `plugins/contentops-mcp/skills/manage-content-workflow/SKILL.md`
- its references in `plugins/contentops-mcp/skills/manage-content-workflow/references/`

In this repository the ContentOps tools come from the project `.mcp.json` server named `contentops`, so they appear as `mcp__contentops__contentops_*`. The server stores state in the same local database as the web workspace, so saved drafts appear at http://localhost:3000.

Do not edit application code while running the content workflow unless the user asks for a code change.
