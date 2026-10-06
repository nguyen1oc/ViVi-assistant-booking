"""Validate and publish a vehicle/content CMS JSON snapshot.

Usage: python scripts/import_site_catalog.py input.json [output.json]
"""

import sys
from pathlib import Path

from src.services.site_catalog import SiteCatalogService


def main() -> int:
    if len(sys.argv) not in {2, 3}:
        print("Usage: python scripts/import_site_catalog.py input.json [output.json]")
        return 2
    source = Path(sys.argv[1]).resolve()
    destination = Path(sys.argv[2]).resolve() if len(sys.argv) == 3 else Path("data/site_catalog.json").resolve()
    counts = SiteCatalogService().import_snapshot(source, destination)
    print(f"Imported {counts['vehicles']} vehicles and {counts['contentPages']} content pages into {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
