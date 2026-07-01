"""
Fetch trust score results for the two completed orders.
Run from inside croo_backend/ directory:
  python check_trust.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'croo_backend.settings')

import django
django.setup()

from croo import AgentClient, Config
from decouple import config
from ledger.trust import compute_trust_score
import json


async def main():
    orch_key = config('CROO_ORCHESTRATOR_SDK_KEY')
    sec_key = config('CROO_SECONDARY_BUYER_SDK_KEY')

    pairs = [
        ('Orchestrator', orch_key, '8aa6f01f-5bdc-47e5-892c-1706b2adaa9a'),
        ('SecondaryBuyer', sec_key, 'f1553ee1-b130-4eb3-8c7c-9bd89f0e7b57'),
    ]

    for label, key, oid in pairs:
        c = AgentClient(Config(base_url='https://api.croo.network', rpc_url='https://mainnet.base.org'), key)
        try:
            order = await c.get_order(oid)
            neg = await c.get_negotiation(order.negotiation_id)
            raw_meta = neg.metadata
            print(f'[{label}] Metadata from negotiation: {raw_meta}')
            try:
                meta = json.loads(raw_meta)
                target = meta.get('target', '')
            except Exception:
                target = ''
            print(f'[{label}] Trust target agent: {target}')
            if target:
                report = compute_trust_score(target)
                print(f'[{label}] ===== TRUST SCORE REPORT =====')
                print(f'         Target  : {report["target_agent_id"]}')
                print(f'         Score   : {report["trust_score"]} / 100')
                print(f'         Completed orders: {report["completed_orders"]}')
                print(f'         Flags   : {report["flags"]}')
                print(f'         Summary : {report["summary"]}')
        except Exception as e:
            import traceback
            traceback.print_exc()
        await c.close()
        print()


asyncio.run(main())
