#!/usr/bin/env python3
"""
Submit .ai-log/session.jsonl to grading server.
Called by git pre-push hook or manually.

After a successful submit, the live log is rotated:
  - Moved into .ai-log/archive/YYYY-MM-DD.jsonl (appended, never overwritten)
  - The live session.jsonl is recreated empty by the next hook write

If the POST fails, the pending file is restored so nothing is lost.
"""
import json
import os
import shutil
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    if Path(".env").exists():
        load_dotenv()
    elif Path("backend/.env").exists():
        load_dotenv(dotenv_path="backend/.env")
except ImportError:
    # Fallback: manually parse .env if python-dotenv is not installed
    import re
    env_file = Path(".env")
    if not env_file.exists() and Path("backend/.env").exists():
        env_file = Path("backend/.env")
    if env_file.exists():
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                m = re.match(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$', line)
                if m:
                    k, v = m.group(1), m.group(2).strip()
                    if v.startswith('"'):
                        q_match = re.match(r'^"([^"\\]*(?:\\.[^"\\]*)*)"', v)
                        if q_match:
                            val = q_match.group(1)
                            try:
                                val = bytes(val, "utf-8").decode("unicode_escape")
                            except Exception:
                                pass
                            os.environ[k] = val
                        else:
                            os.environ[k] = v.strip('"')
                        continue
                    elif v.startswith("'"):
                        q_match = re.match(r"^'([^'\\]*(?:\\.[^'\\]*)*)'", v)
                        if q_match:
                            os.environ[k] = q_match.group(1)
                        else:
                            os.environ[k] = v.strip("'")
                        continue
                    if "#" in v:
                        v = v.split("#", 1)[0].strip()
                    os.environ[k] = v

SERVER_URL = os.environ.get("AI_LOG_SERVER", "")
API_KEY = os.environ.get("AI_LOG_API_KEY", "")
LOG_DIR = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))
LOG_FILE = LOG_DIR / "session.jsonl"
ARCHIVE_DIR = LOG_DIR / "archive"

# Match server-side MAX_BATCH_ENTRIES so we never get a 422.
# If the local file has more than this, we submit the oldest BATCH_LIMIT
# and leave the rest for the next push.
BATCH_LIMIT = 500


def _archive(pending: Path) -> None:
    """Append pending file to today's archive. Never overwrites existing data."""
    if not pending.exists() or pending.stat().st_size == 0:
        return
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    archive_file = ARCHIVE_DIR / f"{today}.jsonl"
    with open(pending, "rb") as src, open(archive_file, "ab") as dst:
        shutil.copyfileobj(src, dst)


def _restore_pending(pending: Path) -> None:
    """Failure path: put pending back at LOG_FILE so the next push retries.
    If hook wrote new entries to LOG_FILE in the meantime, prepend pending."""
    if not pending.exists():
        return
    if LOG_FILE.exists():
        # Concat: pending (older) + LOG_FILE (newer) → LOG_FILE
        tmp = LOG_FILE.with_suffix(".merge.jsonl")
        with open(tmp, "wb") as out:
            with open(pending, "rb") as a:
                shutil.copyfileobj(a, out)
            with open(LOG_FILE, "rb") as b:
                shutil.copyfileobj(b, out)
        os.replace(tmp, LOG_FILE)
        pending.unlink()
    else:
        pending.rename(LOG_FILE)


def _recover_pending_files() -> None:
    """Put interrupted submission batches back into the live queue.

    A process can stop after renaming ``session.jsonl`` to ``session.pending``
    but before the request completes. Those files must be retried on a later
    push; otherwise they are silently stranded forever.
    """
    pending_files = sorted(LOG_DIR.glob("session.pending.*.jsonl"))
    if not pending_files:
        return

    recovered = LOG_FILE.with_name("session.recovering.jsonl")
    try:
        with open(recovered, "wb") as output:
            for pending in pending_files:
                with open(pending, "rb") as source:
                    shutil.copyfileobj(source, output)
            if LOG_FILE.exists():
                with open(LOG_FILE, "rb") as source:
                    shutil.copyfileobj(source, output)
        os.replace(recovered, LOG_FILE)
        for pending in pending_files:
            pending.unlink()
        print(f"[ai-log] Recovered {len(pending_files)} interrupted batch(es).", file=sys.stderr)
    except OSError as exc:
        recovered.unlink(missing_ok=True)
        print(f"[ai-log] Could not recover pending logs: {exc}", file=sys.stderr)


def main():
    _recover_pending_files()

    if not SERVER_URL:
        print("[ai-log] AI_LOG_SERVER not set — skipping submission.", file=sys.stderr)
        sys.exit(0)

    if not LOG_FILE.exists() or LOG_FILE.stat().st_size == 0:
        print("[ai-log] No logs to submit.", file=sys.stderr)
        sys.exit(0)

    # Atomic rename closes the race window: hook writes that arrive after this
    # land in a fresh LOG_FILE, not in the batch we're about to POST.
    pending = LOG_FILE.with_name(f"session.pending.{int(time.time())}.jsonl")
    try:
        LOG_FILE.rename(pending)
    except FileNotFoundError:
        print("[ai-log] No logs to submit.", file=sys.stderr)
        sys.exit(0)

    entries = []
    leftover_lines = []
    with open(pending, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            if len(entries) >= BATCH_LIMIT:
                leftover_lines.append(line)
                continue
            try:
                entries.append(json.loads(stripped))
            except json.JSONDecodeError:
                pass  # drop unparseable line

    if not entries:
        # Nothing to send; archive whatever was there (probably junk) and bail.
        _archive(pending)
        pending.unlink()
        print("[ai-log] No valid entries to submit.", file=sys.stderr)
        sys.exit(0)

    payload = json.dumps({"entries": entries}, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    req = urllib.request.Request(
        SERVER_URL,
        data=payload,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"[ai-log] Submitted {len(entries)} entries → {resp.status}", file=sys.stderr)
    except urllib.error.URLError as e:
        # Failure: restore the whole pending (including leftover) for next push.
        _restore_pending(pending)
        print(f"[ai-log] Submit failed: {e} — logs kept locally.", file=sys.stderr)
        sys.exit(0)  # Don't block push on server error

    # Success: archive the submitted batch, then handle any leftover.
    _archive(pending)
    pending.unlink()

    if leftover_lines:
        # More than BATCH_LIMIT entries existed; put the rest back so the
        # next push picks them up.
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.writelines(leftover_lines)
        print(
            f"[ai-log] {len(leftover_lines)} entries deferred to next push.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
