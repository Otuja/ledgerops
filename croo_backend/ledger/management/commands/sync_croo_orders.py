"""
Management command: sync_croo_orders
Backfills completed CROO provider orders into the local database.
Fetches all orders from the CROO network and ensures every completed
order is reflected in TrustScoreLookup or TransactionAuditLog.
Run:  python manage.py sync_croo_orders
"""
import asyncio
import json
import logging

from decouple import config
from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand

from croo import AgentClient, Config, ListOptions

from ledger.models import TrustScoreLookup, TransactionAuditLog, VirtualWallet
from ledger.trust import compute_trust_score

logger = logging.getLogger('croo')

# Service IDs to service name mapping (from .env)
TRUST_SERVICE_ID = config('CROO_SERVICE_ID_TRUST', default='')
BALANCE_SERVICE_ID = config('CROO_SERVICE_ID_BALANCE', default='')
VERIFY_SERVICE_ID = config('CROO_SERVICE_ID_VERIFY', default='')
REPORT_SERVICE_ID = config('CROO_SERVICE_ID_REPORT', default='')
DEFAULT_SERVICE_ID = config('CROO_SERVICE_ID_DEFAULT', default='')


class Command(BaseCommand):
    help = 'Sync completed CROO orders into the local database'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would be synced without writing to DB')

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        asyncio.run(self.sync(dry_run))

    async def sync(self, dry_run: bool):
        self.stdout.write(self.style.SUCCESS('=== CROO Order Sync ==='))

        croo_config = Config(
            base_url=config('CROO_API_URL', default='https://api.croo.network'),
            ws_url=config('CROO_WS_URL', default='wss://api.croo.network/ws'),
        )
        sdk_key = config('CROO_SDK_KEY', default=config('CROO_API_KEY', default=''))
        client = AgentClient(croo_config, sdk_key)

        # Fetch all provider orders from CROO with pagination
        orders = []
        page = 1
        while True:
            from croo import ListOptions
            opts = ListOptions(role='provider', page=page, page_size=100)
            res = await client.list_orders(opts)
            items = getattr(res, 'data', None)
            if items is None:
                items = getattr(res, 'items', res)
                if not isinstance(items, list):
                    items = getattr(items, 'data', [])
            orders.extend(items)
            if len(items) < 100:
                break
            page += 1
            
        completed = [o for o in orders if getattr(o, 'status', '') == 'completed']
        self.stdout.write(f'CROO: {len(orders)} total orders, {len(completed)} completed')

        synced = 0
        skipped = 0
        errors = 0

        for order in completed:
            order_id = order.order_id
            service_id = getattr(order, 'service_id', '') or ''
            buyer_id = (getattr(order, 'requester_agent_id', '') or
                        getattr(order, 'buyer_user_id', '') or 'unknown')
            price = getattr(order, 'price', 0) or 0
            negotiation_id = getattr(order, 'negotiation_id', '') or ''

            # Determine service type by service_id
            is_trust = TRUST_SERVICE_ID and service_id.startswith(TRUST_SERVICE_ID[:8])
            is_balance = BALANCE_SERVICE_ID and service_id.startswith(BALANCE_SERVICE_ID[:8])
            is_verify = VERIFY_SERVICE_ID and service_id.startswith(VERIFY_SERVICE_ID[:8])
            is_report = REPORT_SERVICE_ID and service_id.startswith(REPORT_SERVICE_ID[:8])

            try:
                if is_trust:
                    # Check if already in TrustScoreLookup
                    exists = await sync_to_async(TrustScoreLookup.objects.filter(order_id=order_id).exists)()
                    if exists:
                        skipped += 1
                        self.stdout.write(f'  [SKIP] {order_id[:12]} (trust lookup already in DB)')
                        continue

                    # Fetch negotiation to get target agent
                    target_agent_id = buyer_id
                    if negotiation_id:
                        try:
                            neg = await client.get_negotiation(negotiation_id)
                            raw_metadata = str(getattr(neg, 'metadata', '') or '{}')
                            meta_dict = json.loads(raw_metadata)
                            if 'target' in meta_dict:
                                target_agent_id = meta_dict['target']
                        except Exception as me:
                            logger.warning('Could not get negotiation %s: %s', negotiation_id, me)

                    self.stdout.write(
                        f'  [SYNC] trust lookup {order_id[:12]} buyer={buyer_id[:12]} target={target_agent_id[:12]}'
                    )
                    if not dry_run:
                        def _save_trust(oid, tid, bid):
                            report = compute_trust_score(tid)
                            report['order_id'] = oid
                            TrustScoreLookup.objects.update_or_create(
                                order_id=oid,
                                defaults=dict(
                                    target_agent_id=tid,
                                    requesting_buyer_id=bid,
                                    trust_score=report['trust_score'],
                                    result_json=json.dumps(report, default=str),
                                ),
                            )
                        await sync_to_async(_save_trust)(order_id, target_agent_id, buyer_id)
                    synced += 1

                else:
                    # Non-trust: check TransactionAuditLog
                    exists = await sync_to_async(TransactionAuditLog.objects.filter(order_id=order_id).exists)()
                    if exists:
                        skipped += 1
                        self.stdout.write(f'  [SKIP] {order_id[:12]} (already in TransactionAuditLog)')
                        continue

                    # Determine service label
                    if is_balance:
                        svc_label = 'balance_check'
                    elif is_verify:
                        svc_label = 'receipt_verify'
                    elif is_report:
                        svc_label = 'analytics_report'
                    else:
                        svc_label = 'transaction_logging'

                    self.stdout.write(
                        f'  [SYNC] {svc_label} {order_id[:12]} buyer={buyer_id[:12]} price={price}'
                    )
                    if not dry_run:
                        provider_agent_id = getattr(order, 'provider_agent_id', '') or ''

                        def _save_tx(oid, bid, amt, svc, neg_id, prov_id):
                            from decimal import Decimal
                            from ledger.models import verify_and_log_payment
                            try:
                                verify_and_log_payment(
                                    order_id=oid,
                                    buyer_id=bid,
                                    amount_usdc=Decimal(str(amt)) / Decimal('1000000'),
                                    target_agent_id=prov_id or bid,
                                    negotiation_id=neg_id,
                                    service_id=svc,
                                    provider_agent_id=prov_id,
                                )
                            except ValueError:
                                pass  # already exists (idempotent)

                        await sync_to_async(_save_tx)(
                            order_id, buyer_id, price, svc_label, negotiation_id, provider_agent_id
                        )
                    synced += 1

            except Exception as ex:
                errors += 1
                self.stderr.write(self.style.ERROR(f'  [ERROR] {order_id[:12]}: {ex}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done. Synced: {synced}  Skipped: {skipped}  Errors: {errors}'
        ))
        if dry_run:
            self.stdout.write(self.style.WARNING('(dry run — nothing was written to DB)'))

        await client.close()
