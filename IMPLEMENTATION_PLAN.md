# gitmind CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local `gitmind` CLI that can import GitMind auth from a logged-in browser, read/export mind maps, create new maps from Markdown/JSON, and update existing maps with mandatory backups.

**Architecture:** A small Python package with focused modules for config/auth, HTTP API access, file discovery, mind-map conversion, OSS upload, and argparse command handling. Writes are restricted to create/update flows, and update always exports JSON and Markdown backups before upload.

**Tech Stack:** Python 3.10+, `argparse`, stdlib HTTP/JSON/filesystem, optional `oss2` for GitMind OSS upload, `uv` packaging.

---

## Files

- Create `work/gitmind/pyproject.toml`: package metadata, script entry point, dependencies.
- Create `work/gitmind/README.md`: quick start and command examples.
- Create `work/gitmind/install.sh`: optional local wrapper installer.
- Create `work/gitmind/src/gitmind/__init__.py`: package version.
- Create `work/gitmind/src/gitmind/config.py`: config paths, token loading, redaction.
- Create `work/gitmind/src/gitmind/auth.py`: browser token scanning and validation.
- Create `work/gitmind/src/gitmind/client.py`: GitMind HTTP client.
- Create `work/gitmind/src/gitmind/files.py`: folder walking, search, resolve.
- Create `work/gitmind/src/gitmind/markdown.py`: Markdown outline parser.
- Create `work/gitmind/src/gitmind/mind.py`: GitMind JSON normalization, export rendering, backup.
- Create `work/gitmind/src/gitmind/oss.py`: OSS upload.
- Create `work/gitmind/src/gitmind/cli.py`: command surface.
- Create `work/gitmind/tests/test_markdown.py`: Markdown parser tests.
- Create `work/gitmind/tests/test_config.py`: redaction/config tests.

## Tasks

### Task 1: Tracer Bullet Read Path

- [ ] Create package skeleton.
- [ ] Implement token loading and API client.
- [ ] Implement `doctor` and `files list`.
- [ ] Verify `doctor --json` and `files list --limit 1 --json`.

### Task 2: Browser Auth Import

- [ ] Implement Comet/Chrome LevelDB token scanner.
- [ ] Implement `auth doctor`, `auth import-browser`, and `auth set-token`.
- [ ] Verify browser import redacts tokens and validates against `/files`.

### Task 3: Discovery And Export

- [ ] Implement folder walking, search, resolve.
- [ ] Implement `minds get`, `minds export`, and `minds export-name`.
- [ ] Verify target mind export works as Markdown without leaking token or signed URL.

### Task 4: Markdown Conversion

- [ ] Implement Markdown outline parser and node counter.
- [ ] Add tests for headings, nested bullets, and paragraphs.
- [ ] Verify tests pass.

### Task 5: Create And Update

- [ ] Implement GitMind create flow.
- [ ] Implement OSS upload helper.
- [ ] Implement update dry-run and confirmed update.
- [ ] Enforce mandatory JSON/Markdown backup before update.
- [ ] Verify dry-run performs no writes.

### Task 6: Polish And Install Surface

- [ ] Add README and install script.
- [ ] Verify `--help`, `doctor`, search, resolve, export, parser tests, and sensitive-output scan.
