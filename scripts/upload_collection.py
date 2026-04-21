#!/usr/bin/env python3
"""
Upload a local image directory to Firebase Storage as a named collection.

Usage:
    python scripts/upload_collection.py data/1_full --name original
    python scripts/upload_collection.py ~/my-cards --name "Summer 2025" --display-name "Summer 2025 Expansion"

Requires:
    FIREBASE_CREDENTIALS_PATH (or FIREBASE_CREDENTIALS_JSON) and
    FIREBASE_STORAGE_BUCKET set in the environment or .env file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure src/ is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload a card image directory to Firebase Storage."
    )
    parser.add_argument("directory", help="Local directory containing card images")
    parser.add_argument("--name", required=True, help="Collection slug (URL-safe, e.g. 'original')")
    parser.add_argument("--display-name", default="", help="Human-readable name (defaults to --name)")
    args = parser.parse_args()

    local_dir = Path(args.directory).expanduser().resolve()
    if not local_dir.is_dir():
        print(f"ERROR: Directory not found: {local_dir}", file=sys.stderr)
        sys.exit(1)

    from core.firebase_storage import is_available, upload_collection

    if not is_available():
        print(
            "ERROR: Firebase Storage not available.\n"
            "Set FIREBASE_CREDENTIALS_PATH (or FIREBASE_CREDENTIALS_JSON) "
            "and FIREBASE_STORAGE_BUCKET in your .env file.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Uploading '{local_dir}' → collection '{args.name}' …\n")

    def progress(current: int, total: int, filename: str) -> None:
        bar_width = 30
        filled = int(bar_width * current / total)
        bar = "█" * filled + "░" * (bar_width - filled)
        print(f"\r  [{bar}] {current}/{total}  {filename:<40}", end="", flush=True)

    metadata = upload_collection(
        str(local_dir),
        args.name,
        display_name=args.display_name or args.name,
        progress_cb=progress,
    )

    print(f"\n\nDone! Uploaded {metadata['image_count']} images.")
    print(f"Collection '{args.name}' is now available in the game.")
    print("\nFirst few card URLs:")
    for card in metadata["cards"][:3]:
        print(f"  {card['url']}")
    if len(metadata["cards"]) > 3:
        print(f"  … and {len(metadata['cards']) - 3} more")


if __name__ == "__main__":
    main()
