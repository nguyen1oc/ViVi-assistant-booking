#!/usr/bin/env python3
"""
Codex IDE log scanner.

The Codex VS Code extension currently stores conversations under
~/.codex/sessions but does not run project hooks in every IDE runtime. This
scanner extracts explicit user messages from local IDE transcripts and appends
them to .ai-log/session.jsonl.

Usage:
  python scripts/log_codex_ide.py --auto          # default: last 24h
  python scripts/log_codex_ide.py --hours 72
  python scripts/log_codex_ide.py --all
  python scripts/log_codex_ide.py --dry-run

Environment overrides:
  CODEX_SESSIONS_DIR   path to the Codex sessions directory
  AI_LOG_DIR           output directory (default: .ai-log)
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

VN_TZ = timezone(timedelta(hours=7))
# Codex has used several values here across the VS Code extension and Desktop
# app. All of these still identify a user-owned Codex session; `thread_source`
# and the workspace check below keep unrelated/internal sessions out.
IDE_ORIGINATORS = {"codex_vscode", "vscode", "codex desktop", "codex_desktop"}

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def git(args: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return ""


def normalize_path(value: str) -> str:
    """Normalize Windows, POSIX, and WSL paths for relationship checks."""
    value = (value or "").strip().lower().replace("/", "\\")
    if value.startswith("\\mnt\\") and len(value) > 6:
        parts = value.split("\\")
        if len(parts) > 3 and len(parts[2]) == 1:
            value = f"{parts[2]}:\\" + "\\".join(parts[3:])
    return value.rstrip("\\")


def paths_related(left: str, right: str) -> bool:
    left_n, right_n = normalize_path(left), normalize_path(right)
    if not left_n or not right_n:
        return False
    return (
        left_n == right_n
        or left_n.startswith(right_n + "\\")
        or right_n.startswith(left_n + "\\")
    )


def get_session_dirs() -> list[Path]:
    override = os.environ.get("CODEX_SESSIONS_DIR")
    if override:
        path = Path(override).expanduser()
        return [path] if path.exists() else []

    candidates = [Path.home() / ".codex" / "sessions"]
    if sys.platform != "win32":
        # Try to resolve Windows home directory dynamically in WSL
        try:
            win_profile = subprocess.check_output(
                ["cmd.exe", "/c", "echo %USERPROFILE%"],
                text=True,
                stderr=subprocess.DEVNULL
            ).strip()
            if win_profile:
                wsl_profile = subprocess.check_output(
                    ["wslpath", "-u", win_profile],
                    text=True,
                    stderr=subprocess.DEVNULL
                ).strip()
                candidates.append(Path(wsl_profile) / ".codex" / "sessions")
        except Exception:
            candidates.extend(Path("/mnt/c/Users").glob("*/.codex/sessions"))

    result: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path.resolve()) if path.exists() else str(path)
        if path.exists() and key not in seen:
            result.append(path)
            seen.add(key)
    return result


def parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def read_logged_ids(log_dir: Path) -> set[str]:
    ids: set[str] = set()
    if not log_dir.exists():
        return ids
    # Include the live file, archives, and any pending file left by a submit
    # attempt. Otherwise a successful rotation would make recent IDE prompts
    # look new again on the next push.
    for log_file in log_dir.rglob("*.jsonl"):
        try:
            with open(log_file, encoding="utf-8-sig") as stream:
                for line in stream:
                    try:
                        entry = json.loads(line)
                    except (json.JSONDecodeError, AttributeError):
                        continue
                    entry_id = entry.get("entry_id")
                    if entry_id:
                        ids.add(str(entry_id))
                    if (
                        entry.get("tool") == "codex"
                        and entry.get("session_id")
                        and entry.get("turn_id")
                    ):
                        ids.add(
                            "codex-ide-turn-"
                            f"{entry['session_id']}-{entry['turn_id']}"
                        )
        except OSError:
            continue
    return ids


def iter_transcripts(session_dirs: list[Path]):
    for sessions_dir in session_dirs:
        yield from sessions_dir.rglob("rollout-*.jsonl")


def read_ide_messages(transcript: Path, repo_root: str,
                      cutoff: datetime | None):
    """Return (session metadata, explicit user messages) for one IDE session."""
    meta: dict = {}
    messages: list[dict] = []
    current_model = ""
    pending_turn_id = ""

    try:
        with open(transcript, encoding="utf-8") as stream:
            for line in stream:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                record_type = record.get("type")
                payload = record.get("payload") or {}

                if record_type == "session_meta":
                    meta = payload
                    originator = str(
                        payload.get("originator") or payload.get("source") or ""
                    ).lower()
                    if originator not in IDE_ORIGINATORS:
                        return {}, []
                    # Guardian and other internal subagents also have
                    # originator=codex_vscode, but their user_message events
                    # are synthetic review prompts rather than text typed by
                    # the IDE user.
                    if payload.get("thread_source", "user") != "user":
                        return {}, []
                    if not paths_related(str(payload.get("cwd", "")), repo_root):
                        return {}, []
                    continue

                if record_type == "turn_context":
                    current_model = str(payload.get("model", current_model))
                    continue

                if (
                    record_type == "response_item"
                    and payload.get("type") == "message"
                    and payload.get("role") == "user"
                ):
                    metadata = (
                        payload.get("internal_chat_message_metadata_passthrough")
                        or {}
                    )
                    pending_turn_id = str(metadata.get("turn_id", ""))
                    continue

                if (
                    record_type != "event_msg"
                    or payload.get("type") != "user_message"
                ):
                    continue

                ts_raw = str(record.get("timestamp", ""))
                ts = parse_timestamp(ts_raw)
                if cutoff and ts and ts < cutoff:
                    continue

                prompt = payload.get("message")
                if not isinstance(prompt, str) or len(prompt.strip()) < 1:
                    continue

                client_id = str(payload.get("client_id", ""))
                messages.append({
                    "timestamp": ts_raw,
                    "prompt": prompt.strip(),
                    "client_id": client_id,
                    "turn_id": pending_turn_id,
                    "model": current_model,
                })
                pending_turn_id = ""
    except OSError:
        return {}, []

    # A transcript without session_meta cannot be safely attributed to this
    # repository or distinguished from the CLI.
    if not meta:
        return {}, []
    return meta, messages


def build_entry(meta: dict, message: dict, transcript: Path,
                repo: str, branch: str, commit: str, student: str) -> dict:
    session_id = str(meta.get("id") or meta.get("session_id") or transcript.stem)
    message_id = message["client_id"]
    if not message_id:
        # Stable fallback for older transcript schemas.
        # Use first 80 characters of the UNTRUNCATED prompt to match the deduplication logic.
        message_id = f"{message['timestamp']}-{message['prompt'][:80]}"

    ts = parse_timestamp(message["timestamp"])
    ts_value = (
        ts.astimezone(VN_TZ).isoformat()
        if ts else datetime.now(VN_TZ).isoformat()
    )
    entry_id = f"codex-ide-{session_id}-{message_id}"
    dedupe_ids = [entry_id]
    if message["turn_id"]:
        dedupe_ids.append(
            f"codex-ide-turn-{session_id}-{message['turn_id']}"
        )

    return {
        "entry_id": entry_id,
        "ts": ts_value,
        "tool": "codex",
        "event": "UserPromptSubmit",
        "session_id": session_id,
        "model": message["model"],
        "repo": repo,
        "branch": branch,
        "commit": commit,
        "student": student,
        "prompt": message["prompt"][:1000],
        "turn_id": message["turn_id"],
        "transcript_path": str(transcript),
        "_dedupe_ids": dedupe_ids,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract prompts from local Codex IDE transcripts."
    )
    parser.add_argument("--auto", action="store_true",
                        help="Scan recent IDE sessions (default mode).")
    parser.add_argument("--hours", type=int, default=24,
                        help="Recent window in hours (default: 24).")
    parser.add_argument("--all", action="store_true",
                        help="Scan all local IDE sessions.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview new entries without writing.")
    args = parser.parse_args()

    session_dirs = get_session_dirs()
    if not session_dirs:
        print("[codex-ide-log] No Codex sessions directory found.",
              file=sys.stderr)
        return

    repo_root = git(["rev-parse", "--show-toplevel"])
    origin = git(["remote", "get-url", "origin"])
    if not repo_root or not origin:
        print("[codex-ide-log] Current directory is not a Git repo with origin.",
              file=sys.stderr)
        return

    cutoff = None
    if not args.all:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)

    log_dir = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "session.jsonl"
    logged_ids = read_logged_ids(log_dir)

    repo = origin.rstrip("/").split("/")[-1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    branch = git(["rev-parse", "--abbrev-ref", "HEAD"])
    commit = git(["rev-parse", "--short", "HEAD"])
    student = git(["config", "user.email"])

    new_entries: list[dict] = []
    for transcript in iter_transcripts(session_dirs):
        meta, messages = read_ide_messages(transcript, repo_root, cutoff)
        for message in messages:
            entry = build_entry(
                meta, message, transcript, repo, branch, commit, student
            )
            dedupe_ids = entry.pop("_dedupe_ids")
            if any(entry_id in logged_ids for entry_id in dedupe_ids):
                continue
            new_entries.append(entry)
            logged_ids.update(dedupe_ids)

    new_entries.sort(key=lambda item: item["ts"])
    if not new_entries:
        scope = "all" if args.all else f"{args.hours}h"
        print(f"[codex-ide-log] No new IDE prompts (window={scope}).",
              file=sys.stderr)
        return

    if args.dry_run:
        print(f"[codex-ide-log] DRY RUN - would log "
              f"{len(new_entries)} prompt(s):")
        for entry in new_entries:
            preview = entry["prompt"].replace("\n", " ")[:120]
            print(f"  [{entry['ts'][:19]}] {preview}")
        return

    with open(log_file, "a", encoding="utf-8") as stream:
        for entry in new_entries:
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"[codex-ide-log] Logged {len(new_entries)} IDE prompt(s).",
          file=sys.stderr)


if __name__ == "__main__":
    main()
