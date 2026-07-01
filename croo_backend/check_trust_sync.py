"""
Sync version — just computes and shows the trust score results.
Run from inside croo_backend/ directory: python check_trust_sync.py
"""
import sys, os
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'croo_backend.settings')
import django; django.setup()

from ledger.trust import compute_trust_score
import json

# These are the two target agents from the negotiation metadata
targets = {
    'SecondaryBuyer (target of Orchestrator lookup)': '83739384-fb06-437e-9cd7-0e1f5c8ea464',
    'Orchestrator (target of SecondaryBuyer lookup)': '34ee2d7d-6812-48a7-99fc-d743c044827b',
}

for description, agent_id in targets.items():
    print(f'\n===== TRUST SCORE: {description} =====')
    report = compute_trust_score(agent_id)
    print(f'  Target Agent  : {report["target_agent_id"]}')
    print(f'  Trust Score   : {report["trust_score"]} / 100')
    print(f'  Completed     : {report["completed_orders"]} orders')
    print(f'  Disputed      : {report["disputed_or_refunded_orders"]} orders')
    print(f'  Completion %  : {report["completion_rate"]:.1%}')
    print(f'  Dispute %     : {report["dispute_rate"]:.1%}')
    print(f'  Total Volume  : {report["total_volume_usdc"]} USDC')
    print(f'  Unique Buyers : {report["unique_buyer_count"]}')
    print(f'  Account Age   : {report["account_age_days"]} days')
    print(f'  Flags         : {report["flags"] or "none"}')
    print(f'  Summary       : {report["summary"]}')
