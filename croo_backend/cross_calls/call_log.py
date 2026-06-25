"""
cross_calls/call_log.py — Shared append-only CSV log for all cross-agent calls.

Every successful or failed negotiate→pay→deliver cycle writes one row here so
post-hoc verification of buyer/counterparty diversity is trivial.

Log file: croo_backend/cross_call_log.csv  (created on first write)
"""

import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

# Sits alongside manage.py at the croo_backend root
LOG_PATH = Path(__file__).resolve().parent.parent / 'cross_call_log.csv'

COLUMNS = [
    'timestamp',           # ISO-8601 UTC
    'round',               # e.g. "A", "B", "all"
    'call_index',          # position within the sequence (1-based)
    'buyer_label',         # human name, e.g. "Orchestrator"
    'buyer_key_prefix',    # first 20 chars of SDK key (non-secret identifier)
    'counterparty_label',  # e.g. "LedgerOps", "Citeable"
    'service_name',        # e.g. "trust_score_lookup", "balance_check"
    'metadata_sent',       # exact metadata string sent to provider
    'requirements_sent',   # requirements string sent
    'negotiation_id',      # CROO negotiation_id
    'order_id',            # CROO order_id
    'amount_usdc',         # price paid (from Order.price)
    'status',              # "ok" | "error" | "skipped" | "timeout"
    'error_detail',        # exception message if status != "ok"
    'delivery_preview',    # first 200 chars of deliverable_text
    'notes',               # business-logic description of why this call makes sense
]


def log_call(record: dict) -> None:
    """
    Append one call record to cross_call_log.csv.
    Creates the file (with header) on first write.
    Silently ignores any extra keys in record via extrasaction='ignore'.
    """
    file_exists = LOG_PATH.exists()
    with open(LOG_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction='ignore')
        if not file_exists:
            writer.writeheader()
        # Fill defaults for any missing columns
        row = {col: record.get(col, '') for col in COLUMNS}
        if not row['timestamp']:
            row['timestamp'] = datetime.now(timezone.utc).isoformat()
        writer.writerow(row)


def read_log() -> list[dict]:
    """Return all rows from the CSV log as a list of dicts."""
    if not LOG_PATH.exists():
        return []
    with open(LOG_PATH, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def print_summary(verbose: bool = False) -> None:
    """
    Print a structured summary of all logged cross-calls and compare against
    CROO's stated anti-sybil thresholds:
      ≥ 3 unique counterparty agents transacting with LedgerOps
      ≥ 5 unique buyer wallet identities transacting with LedgerOps
    """
    records = read_log()
    width = 68

    print(f"\n{'═' * width}")
    print(f"  CROSS-CALL DIVERSITY REPORT  ({LOG_PATH.name})")
    print(f"{'═' * width}")

    if not records:
        print("  No calls logged yet — run some rounds first.")
        print(f"{'═' * width}")
        return

    total   = len(records)
    ok      = [r for r in records if r.get('status') == 'ok']
    errors  = [r for r in records if r.get('status') == 'error']
    skipped = [r for r in records if r.get('status') == 'skipped']

    # Diversity metrics — use buyer_key_prefix as the wallet proxy
    # (a unique SDK key corresponds to a unique wallet on CROO)
    unique_buyer_keys    = set(r['buyer_key_prefix'] for r in ok if r.get('buyer_key_prefix'))
    unique_buyer_labels  = set(r['buyer_label']      for r in ok if r.get('buyer_label'))
    unique_counterparties = set(r['counterparty_label'] for r in ok if r.get('counterparty_label'))

    print(f"  Total calls logged  : {total}  (ok={len(ok)}, errors={len(errors)}, skipped={len(skipped)})")
    print()
    print(f"  Unique buyer agents      : {len(unique_buyer_labels)}")
    for lbl in sorted(unique_buyer_labels):
        count = sum(1 for r in ok if r['buyer_label'] == lbl)
        print(f"    • {lbl} ({count} calls)")
    print()
    print(f"  Unique buyer key prefixes: {len(unique_buyer_keys)}")
    for pfx in sorted(unique_buyer_keys):
        lbl = next((r['buyer_label'] for r in ok if r['buyer_key_prefix'] == pfx), '?')
        print(f"    • {pfx}…  ({lbl})")
    print()
    print(f"  Unique counterparty agents: {len(unique_counterparties)}")
    for cp in sorted(unique_counterparties):
        count = sum(1 for r in ok if r['counterparty_label'] == cp)
        print(f"    • {cp} ({count} orders received)")
    print()

    # Anti-sybil threshold check
    print(f"  {'─' * (width - 2)}")
    print(f"  ANTI-SYBIL THRESHOLD CHECK")
    print(f"  {'─' * (width - 2)}")

    cp_target  = 3
    wlt_target = 5
    cp_ok      = len(unique_counterparties) >= cp_target
    wlt_ok     = len(unique_buyer_keys)     >= wlt_target

    print(f"  {'✅' if cp_ok  else '⚠️ '} ≥{cp_target} unique counterparty agents  "
          f"[{len(unique_counterparties)}/{cp_target}]"
          + ('' if cp_ok else '  ← need more providers or external buyers'))
    print(f"  {'✅' if wlt_ok else '⚠️ '} ≥{wlt_target} unique buyer wallet keys    "
          f"[{len(unique_buyer_keys)}/{wlt_target}]"
          + ('' if wlt_ok else '  ← add more buyer agent keys or run external testers'))

    if not cp_ok or not wlt_ok:
        print()
        print("  Tip: to close the gap —")
        if not cp_ok:
            print("    • Register Citeable (2nd provider) and add CROO_CITEABLE_* env vars")
            print("    • Have LedgerOps buy from Citeable (3rd counterparty for Citeable's view)")
        if not wlt_ok:
            print("    • Add CROO_ORCHESTRATOR_SDK_KEY, CROO_SECONDARY_BUYER_SDK_KEY, etc.")
            print("    • Demo the dashboard live — each viewer who triggers a lookup adds a real call")

    if verbose and ok:
        print()
        print(f"  {'─' * (width - 2)}")
        print(f"  CALL DETAIL")
        print(f"  {'─' * (width - 2)}")
        hdr = f"  {'#':<4} {'Buyer':<18} {'→ Counterparty':<16} {'Service':<22} {'Order ID':<20} {'Status'}"
        print(hdr)
        print(f"  {'─' * (width - 2)}")
        for i, r in enumerate(records, 1):
            status_icon = '✅' if r['status'] == 'ok' else ('⚠️' if r['status'] == 'skipped' else '❌')
            print(f"  {i:<4} {r['buyer_label'][:17]:<18} {'→ ' + r['counterparty_label'][:13]:<16} "
                  f"{r['service_name'][:21]:<22} {r['order_id'][:19]:<20} {status_icon}")

    print(f"{'═' * width}\n")
