---
name: gmind
description: Use the local gmind CLI to read and write GitMind mind maps.
---

# gmind

Use `gmind` for GitMind mind-map workflows. `gmind` can import a local browser session, search GitMind files, export mind maps, create new mind maps from Markdown/JSON, and update existing mind maps with automatic backups.

## Start

Check whether the CLI is installed and authenticated:

```bash
command -v gmind
gmind doctor --json
```

If auth is missing and the user is logged in with Comet:

```bash
gmind auth import-browser --browser comet
```

If the user uses Chrome:

```bash
gmind auth import-browser --browser chrome
```

## Safe Read Flow

Search first:

```bash
gmind files search "AI 研究所" --json
```

Resolve a human title to `file_guid` before reading:

```bash
gmind minds resolve "AI 研究所 - 週會課程規劃_Irene（勿動）" --json
```

Export as Markdown:

```bash
gmind minds export-name "AI 研究所 - 週會課程規劃_Irene（勿動）" --format md --out ./mind.md
```

Export raw GitMind JSON:

```bash
gmind minds export-name "AI 研究所 - 週會課程規劃_Irene（勿動）" --format json --out ./mind.json
```

## Write Flow

Create a new mind map:

```bash
gmind minds create --name "Claude 討論整理" --from-md ./outline.md
```

Preview an update:

```bash
gmind minds update-name "既有圖名稱" --from-md ./outline.md --dry-run
```

Only after the user explicitly approves overwriting GitMind content:

```bash
gmind minds update-name "既有圖名稱" --from-md ./outline.md --confirm
```

Confirmed updates automatically create JSON and Markdown backups before uploading.

## Rules

- Always run `gmind doctor --json` before using private GitMind data.
- Use `--json` for agent analysis.
- Resolve names before reading or writing when the user gives a title.
- Run `--dry-run` before any update.
- Do not use `--confirm` unless the user explicitly approved overwriting that exact mind map.
- Do not print, copy, or store full GitMind tokens in chat or deliverables.
- Do not use this CLI for delete, sharing, payments, teams, comments, or AI credit actions.
