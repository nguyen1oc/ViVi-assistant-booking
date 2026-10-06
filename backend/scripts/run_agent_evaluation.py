"""Repository entry point for behavioral agent evaluation."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.evaluation.agent_benchmark import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
