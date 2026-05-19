# GitHub Safe Upload Policy

This repo is a private personal Life OS workspace. Even for a private GitHub
repository, upload only the project shell and code—never personal data.

## Never Upload

- `profile.md`
- `Moonlight.md`
- `moonlight/`
- `.mcp.json`
- `.claude/brief/context.md`
- `.claude/logs/`
- `.claude/cache/`
- `.claude/settings.local.json`
- `.claude/memory-graph.json`
- `.claude/worktrees/`
- `.obsidian/.rest-api-key`
- `.obsidian/workspace.json`

## Safe To Upload

- `.gitignore`
- `README.md`
- `LICENSE`
- `GITHUB-SAFE-FILES.md`
- `CLAUDE.md` (v3+ only — pure DNA, no personal data)
- `index.html` (v3 reset placeholder)
- `.claude/agents/`
- `.claude/scripts/` (non-personal scripts only — review before adding)

## Before Every Push

`.gitignore` is the primary safety layer—it excludes all "Never Upload" files
so `git push` only ships what's listed in "Safe To Upload".

Check before each push:

```bash
git status
git diff --cached --stat
```

Make sure no path matching "Never Upload" appears in either output.
