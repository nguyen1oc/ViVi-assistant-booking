#!/usr/bin/env bash
# Cross-platform Python launcher for AI log hooks.
# Validates candidates because the Microsoft Store alias may be on PATH but
# unusable from Git hooks. Exits 0 if no working Python is found.
set -u

SCRIPT_PATH=$1
shift
SCRIPT_ARGS=("$@")

try_python() {
  "$@" -c "import sys" >/dev/null 2>&1 || return 1
  exec "$@" "$SCRIPT_PATH" "${SCRIPT_ARGS[@]}"
}

# Try local virtual environments first (so installed dotenv, etc., are loaded)
if [ -x ".venv/bin/python" ]; then
  try_python ".venv/bin/python"
fi
if [ -x ".venv/Scripts/python.exe" ]; then
  try_python ".venv/Scripts/python.exe"
fi
if [ -x "venv/bin/python" ]; then
  try_python "venv/bin/python"
fi
if [ -x "venv/Scripts/python.exe" ]; then
  try_python "venv/Scripts/python.exe"
fi

for name in python3 python; do
  if command -v "$name" >/dev/null 2>&1; then
    try_python "$name"
  fi
done
if command -v py >/dev/null 2>&1; then
  try_python py -3
fi

# `where.exe` exposes later PATH matches hidden behind a broken first match.
if command -v where.exe >/dev/null 2>&1; then
  while IFS= read -r win_path; do
    win_path=${win_path%$'\r'}
    [ -n "$win_path" ] || continue
    if command -v cygpath >/dev/null 2>&1; then
      candidate=$(cygpath -u "$win_path")
    else
      candidate=$win_path
    fi
    try_python "$candidate"
  done < <(where.exe python.exe 2>/dev/null || true)
fi

shopt -s nullglob 2>/dev/null || true
for candidate in \
  /c/Users/*/AppData/Local/Programs/Python/Python*/python.exe \
  "/c/Program Files/Python"*/python.exe \
  "/c/Program Files (x86)/Python"*/python.exe \
  /c/Python*/python.exe; do
  try_python "$candidate"
done
shopt -u nullglob 2>/dev/null || true

exit 0
