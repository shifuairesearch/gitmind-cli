from __future__ import annotations

import argparse
import getpass
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .auth import BROWSER_PROFILES, import_from_browser, validate_token
from .client import GitMindClient, GitMindError
from .config import load_token, redact_token, save_token
from .files import list_root, resolve_mind, search_files, slim_file, walk_files
from .mind import DEFAULT_BACKUP_DIR, content_summary, load_content_from_file, read_mind, scrub_meta, write_backup, write_export
from .oss import upload_content


def json_out(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def err(message: str) -> None:
    print(message, file=sys.stderr)


def ok(data: Any = None, warnings: list[str] | None = None) -> dict[str, Any]:
    return {"ok": True, "data": data if data is not None else {}, "warnings": warnings or []}


def fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def wants_json(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "json", False))


def get_client(args: argparse.Namespace) -> tuple[GitMindClient | None, dict[str, Any]]:
    info = load_token(getattr(args, "token", None))
    auth = {"available": bool(info.token), "source": info.source, "token": redact_token(info.token)}
    if not info.token:
        return None, auth
    return GitMindClient(info.token), auth


def require_client(args: argparse.Namespace) -> GitMindClient:
    client, _auth = get_client(args)
    if not client:
        raise GitMindError("找不到 GitMind 登入狀態。請先執行：gitmind auth import-browser --browser chrome")
    return client


def cmd_doctor(args: argparse.Namespace) -> int:
    client, auth = get_client(args)
    checks: dict[str, Any] = {
        "ok": False,
        "version": __version__,
        "auth": auth,
        "endpoint": {"reachable": False},
    }
    if not client:
        checks["error"] = "missing auth; run gitmind auth import-browser --browser chrome"
        if wants_json(args):
            json_out(checks)
        else:
            print("尚未完成 GitMind 登入設定。")
            print()
            print("請先用 Chrome 打開 GitMind 並確認已登入，然後執行：")
            print("  gitmind auth import-browser --browser chrome")
            print()
            print("如果你是用 Comet 登入 GitMind，請改執行：")
            print("  gitmind auth import-browser --browser comet")
        return 1
    try:
        payload = client.get("/files", {"per_page": 1})
        checks["endpoint"] = {
            "reachable": True,
            "app_status": payload.get("status"),
            "message": payload.get("message"),
        }
        checks["ok"] = payload.get("status") == 200
        if wants_json(args):
            json_out(checks)
        else:
            print("GitMind CLI 已可連上你的 GitMind。")
            print(f"設定來源：{auth.get('source')}")
            print(f"登入狀態：{payload.get('message')}")
            print()
            print("接下來可以試試：")
            print("  gitmind files search \"關鍵字\" --json")
        return 0 if checks["ok"] else 1
    except GitMindError as exc:
        checks["endpoint"] = {"reachable": False, "message": str(exc), "http_status": exc.http_status}
        if wants_json(args):
            json_out(checks)
        else:
            print("GitMind CLI 目前連不上 GitMind。")
            print(f"原因：{exc}")
            print()
            print("可以先確認網路，或重新匯入登入狀態：")
            print("  gitmind auth import-browser --browser chrome")
        return 1


def cmd_auth_doctor(args: argparse.Namespace) -> int:
    return cmd_doctor(args)


def cmd_auth_import_browser(args: argparse.Namespace) -> int:
    path, message = import_from_browser(args.browser)
    data = {"browser": args.browser, "config": str(path), "message": message}
    if wants_json(args):
        json_out(ok(data))
    else:
        browser_name = "Chrome" if args.browser == "chrome" else "Comet"
        print(f"已成功從 {browser_name} 取得 GitMind 登入狀態。")
        print(f"設定已儲存到：{path}")
        print()
        print("下一步請執行：")
        print("  gitmind doctor")
        print()
        print("如果你想讓 AI agent 讀取結果，可以使用：")
        print("  gitmind doctor --json")
    return 0


def cmd_auth_set_token(args: argparse.Namespace) -> int:
    token = args.value
    if not token:
        token = getpass.getpass("GitMind Authorization token: ")
    normalized = save_token(token, source="manual")
    info = load_token()
    if not info.token:
        json_out(fail("auth_save_failed", "token was saved but could not be loaded"))
        return 1
    valid, message = validate_token(info.token)
    data = {"config": str(normalized), "valid": valid, "message": message, "token": redact_token(info.token)}
    if wants_json(args):
        json_out(ok(data))
    elif valid:
        print("GitMind token 已儲存並驗證成功。")
        print(f"設定已儲存到：{normalized}")
        print()
        print("下一步請執行：")
        print("  gitmind doctor")
    else:
        print("GitMind token 已儲存，但驗證沒有通過。")
        print(f"GitMind 回應：{message}")
    return 0 if valid else 1


def cmd_files_list(args: argparse.Namespace) -> int:
    client = require_client(args)
    items = []
    for item in list_root(client)[: args.limit]:
        record = dict(item)
        name = record.get("file_name") or record.get("name") or ""
        record["path"] = f"ROOT/{name}" if name else "ROOT"
        items.append(slim_file(record))
    json_out(ok(items))
    return 0


def cmd_files_search(args: argparse.Namespace) -> int:
    client = require_client(args)
    json_out(ok(search_files(client, args.term, limit=args.limit)))
    return 0


def cmd_files_tree(args: argparse.Namespace) -> int:
    client = require_client(args)
    items = [slim_file(item) for item in walk_files(client, max_depth=args.max_depth)]
    json_out(ok(items[: args.limit] if args.limit else items))
    return 0


def resolve_arg(client: GitMindClient, value: str) -> dict[str, Any]:
    if len(value) >= 16 and " " not in value and "/" not in value:
        return {"file_guid": value, "file_name": value, "path": None}
    return resolve_mind(client, value)


def cmd_minds_resolve(args: argparse.Namespace) -> int:
    client = require_client(args)
    json_out(ok(slim_file(resolve_mind(client, args.name))))
    return 0


def cmd_minds_get(args: argparse.Namespace) -> int:
    client = require_client(args)
    item = resolve_arg(client, args.file_guid)
    meta, content = read_mind(client, item["file_guid"])
    json_out(ok({"file": slim_file(item), "meta": scrub_meta(meta), "summary": content_summary(content)}))
    return 0


def cmd_minds_export(args: argparse.Namespace) -> int:
    client = require_client(args)
    item = resolve_arg(client, args.file_guid)
    _meta, content = read_mind(client, item["file_guid"])
    text = write_export(content, args.format, Path(args.out) if args.out else None, title=item.get("file_name"))
    if text is not None:
        print(text, end="")
    else:
        json_out(ok({"out": args.out, "summary": content_summary(content)}))
    return 0


def cmd_minds_export_name(args: argparse.Namespace) -> int:
    client = require_client(args)
    item = resolve_mind(client, args.name)
    _meta, content = read_mind(client, item["file_guid"])
    text = write_export(content, args.format, Path(args.out) if args.out else None, title=item.get("file_name"))
    if text is not None:
        print(text, end="")
    else:
        json_out(ok({"out": args.out, "file": slim_file(item), "summary": content_summary(content)}))
    return 0


def save_new_content(client: GitMindClient, file_guid: str, content: dict[str, Any]) -> str:
    oss_auth_payload = client.get("/authorizations/oss/buckets")
    oss_auth = client.require_success(oss_auth_payload, "get OSS auth")
    resource_id = upload_content(oss_auth, file_guid, content)
    payload = client.put(
        f"/minds/{file_guid}",
        {
            "project_id": resource_id,
            "resource_ids": [],
            "nodes": content_summary(content)["node_count"],
            "file_guid": file_guid,
        },
    )
    client.require_success(payload, "save mind")
    return resource_id


def content_from_args(args: argparse.Namespace) -> dict[str, Any]:
    source = args.from_md or args.from_json
    if not source:
        raise ValueError("provide --from-md or --from-json")
    return load_content_from_file(Path(source))


def cmd_minds_create(args: argparse.Namespace) -> int:
    client = require_client(args)
    content = content_from_args(args)
    created = client.require_success(
        client.post("/minds", {"action_type": 1, "file_name": args.name, "parent_id": args.folder or ""}),
        "create mind",
    )
    file_guid = created["file_guid"]
    resource_id = save_new_content(client, file_guid, content)
    json_out(ok({
        "file_name": args.name,
        "file_guid": file_guid,
        "resource_id": resource_id,
        "url": f"https://gitmind.com/app/docs/m/{file_guid}",
        "summary": content_summary(content),
    }))
    return 0


def validate_update_flags(args: argparse.Namespace) -> None:
    if bool(args.dry_run) == bool(args.confirm):
        raise ValueError("choose exactly one: --dry-run or --confirm")


def run_update(args: argparse.Namespace, target: str, resolve_by_name: bool) -> int:
    validate_update_flags(args)
    client = require_client(args)
    item = resolve_mind(client, target) if resolve_by_name else resolve_arg(client, target)
    new_content = content_from_args(args)
    old_meta, old_content = read_mind(client, item["file_guid"])
    preview = {
        "file": slim_file(item),
        "current": content_summary(old_content),
        "candidate": content_summary(new_content),
        "backup_required": True,
    }
    if args.dry_run:
        json_out(ok({"dry_run": True, **preview}))
        return 0
    backup_dir = Path(args.backup_dir) if args.backup_dir else DEFAULT_BACKUP_DIR
    backup_json, backup_md = write_backup(item, old_content, backup_dir)
    resource_id = save_new_content(client, item["file_guid"], new_content)
    json_out(ok({
        "dry_run": False,
        **preview,
        "backup": {"json": str(backup_json), "markdown": str(backup_md)},
        "resource_id": resource_id,
        "url": f"https://gitmind.com/app/docs/m/{item['file_guid']}",
        "previous_meta_status": old_meta.get("status"),
    }))
    return 0


def cmd_minds_update(args: argparse.Namespace) -> int:
    return run_update(args, args.file_guid, resolve_by_name=False)


def cmd_minds_update_name(args: argparse.Namespace) -> int:
    return run_update(args, args.name, resolve_by_name=True)


def cmd_raw_get(args: argparse.Namespace) -> int:
    client = require_client(args)
    raw_path = args.path if args.path.startswith("/") else f"/{args.path}"
    params: dict[str, str] = {}
    for item in args.query or []:
        key, sep, value = item.partition("=")
        if not sep:
            raise ValueError(f"invalid --query value: {item}")
        params[key] = value
    json_out(ok(client.get(raw_path, params or None)))
    return 0


def add_common_file_args(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--from-md")
    group.add_argument("--from-json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gitmind", description="Read and write GitMind mind maps")
    parser.add_argument("--version", action="version", version=f"gitmind {__version__}")
    parser.add_argument("--token", help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command")

    doctor = sub.add_parser("doctor", help="Check auth and GitMind endpoint reachability")
    doctor.add_argument("--json", action="store_true", help="Emit JSON output")
    doctor.set_defaults(func=cmd_doctor)

    auth = sub.add_parser("auth", help="Manage GitMind auth")
    auth_sub = auth.add_subparsers(dest="auth_command")
    auth_doctor = auth_sub.add_parser("doctor", help="Check auth")
    auth_doctor.add_argument("--json", action="store_true")
    auth_doctor.set_defaults(func=cmd_auth_doctor)
    auth_import = auth_sub.add_parser("import-browser", help="Import token from a logged-in browser profile")
    auth_import.add_argument("--browser", choices=sorted(BROWSER_PROFILES), default="chrome")
    auth_import.add_argument("--json", action="store_true")
    auth_import.set_defaults(func=cmd_auth_import_browser)
    auth_set = auth_sub.add_parser("set-token", help="Save a manually copied GitMind Authorization token")
    auth_set.add_argument("--token", dest="value")
    auth_set.add_argument("--json", action="store_true")
    auth_set.set_defaults(func=cmd_auth_set_token)

    files = sub.add_parser("files", help="Discover GitMind files")
    files_sub = files.add_subparsers(dest="files_command")
    files_list = files_sub.add_parser("list", help="List root GitMind files")
    files_list.add_argument("--limit", type=int, default=20)
    files_list.add_argument("--json", action="store_true")
    files_list.set_defaults(func=cmd_files_list)
    files_search = files_sub.add_parser("search", help="Search files by name/path")
    files_search.add_argument("term")
    files_search.add_argument("--limit", type=int, default=20)
    files_search.add_argument("--json", action="store_true")
    files_search.set_defaults(func=cmd_files_search)
    files_tree = files_sub.add_parser("tree", help="List files recursively")
    files_tree.add_argument("--max-depth", type=int, default=3)
    files_tree.add_argument("--limit", type=int, default=200)
    files_tree.add_argument("--json", action="store_true")
    files_tree.set_defaults(func=cmd_files_tree)

    minds = sub.add_parser("minds", help="Read and write mind maps")
    minds_sub = minds.add_subparsers(dest="minds_command")
    minds_resolve = minds_sub.add_parser("resolve", help="Resolve a mind name to file_guid")
    minds_resolve.add_argument("name")
    minds_resolve.add_argument("--json", action="store_true")
    minds_resolve.set_defaults(func=cmd_minds_resolve)
    minds_get = minds_sub.add_parser("get", help="Read mind metadata and content summary")
    minds_get.add_argument("file_guid")
    minds_get.add_argument("--json", action="store_true")
    minds_get.set_defaults(func=cmd_minds_get)
    minds_export = minds_sub.add_parser("export", help="Export a mind by file_guid")
    minds_export.add_argument("file_guid")
    minds_export.add_argument("--format", choices=("md", "json"), default="md")
    minds_export.add_argument("--out")
    minds_export.set_defaults(func=cmd_minds_export)
    minds_export_name = minds_sub.add_parser("export-name", help="Export a mind by name")
    minds_export_name.add_argument("name")
    minds_export_name.add_argument("--format", choices=("md", "json"), default="md")
    minds_export_name.add_argument("--out")
    minds_export_name.set_defaults(func=cmd_minds_export_name)
    minds_create = minds_sub.add_parser("create", help="Create a new mind from Markdown or JSON")
    minds_create.add_argument("--name", required=True)
    minds_create.add_argument("--folder")
    add_common_file_args(minds_create)
    minds_create.set_defaults(func=cmd_minds_create)
    minds_update = minds_sub.add_parser("update", help="Update an existing mind by file_guid")
    minds_update.add_argument("file_guid")
    add_common_file_args(minds_update)
    minds_update.add_argument("--dry-run", action="store_true")
    minds_update.add_argument("--confirm", action="store_true")
    minds_update.add_argument("--backup-dir")
    minds_update.set_defaults(func=cmd_minds_update)
    minds_update_name = minds_sub.add_parser("update-name", help="Update an existing mind by name")
    minds_update_name.add_argument("name")
    add_common_file_args(minds_update_name)
    minds_update_name.add_argument("--dry-run", action="store_true")
    minds_update_name.add_argument("--confirm", action="store_true")
    minds_update_name.add_argument("--backup-dir")
    minds_update_name.set_defaults(func=cmd_minds_update_name)

    raw = sub.add_parser("raw", help="Read-only raw GitMind API helpers")
    raw_sub = raw.add_subparsers(dest="raw_command")
    raw_get = raw_sub.add_parser("get", help="GET a GitMind v3 path")
    raw_get.add_argument("path")
    raw_get.add_argument("--query", action="append", help="Query param as key=value")
    raw_get.add_argument("--json", action="store_true")
    raw_get.set_defaults(func=cmd_raw_get)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except GitMindError as exc:
        json_out(fail("gitmind_api_error", str(exc)))
        return 1
    except Exception as exc:
        json_out(fail("unexpected_error", str(exc)))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
