"""Sanitize existing `mobiles.json` by removing discount keys.

This script removes discount-related keys (`price_discount`, `price_original`,
and `price_discount_pct`) from the JSON entries. It does NOT attempt to
re-scrape pages; use the main spider to recompute prices if needed.

Usage:
    python scripts/fix_prices.py mobiles.json

It creates a backup of the original file before writing.
"""
import json
import sys
from pathlib import Path
from datetime import datetime


def sanitize_prices(file_path: Path, dry_run=True):
    data = json.loads(file_path.read_text(encoding='utf-8'))
    updated = 0
    for itm in data:
        changed = False
        for k in ('price_original', 'price_discount', 'price_discount_pct'):
            if k in itm:
                changed = True
                itm.pop(k, None)
        if changed:
            updated += 1
    if dry_run:
        print(f"Dry run: {updated} items would be updated (discount keys removed)")
        return updated
    # backup and write
    backup = file_path.with_suffix(f".bak.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
    file_path.rename(backup)
    file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Wrote {file_path} (backup saved to {backup}); {updated} items were updated")
    return updated


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python scripts/fix_prices.py mobiles.json [--apply]')
        sys.exit(1)
    p = Path(sys.argv[1])
    apply_changes = '--apply' in sys.argv
    sanitize_prices(p, dry_run=not apply_changes)