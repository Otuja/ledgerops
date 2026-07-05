import asyncio
import logging
import signal

from decouple import config
from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand
from django.utils import timezone

from croo import (
    AgentClient, Config, EventType, Event,
    DeliverOrderRequest, DeliverableType,
    APIError,
    is_not_found,
    is_unauthorized,
    is_invalid_params,
    is_invalid_status,
    is_forbidden,
    is_insufficient_balance,
)
from django.db.models import Sum

from ledger.models import (
    verify_and_log_payment,
    TransactionAuditLog,
    NegotiationLog,
    VirtualWallet,
    TrustScoreLookup,
)
from ledger.trust import compute_trust_score

logger = logging.getLogger('croo.agent')


class Command(BaseCommand):
    help = 'Runs the CROO Agent Worker — listens for events and processes orders'

    def handle(self, *args, **options):
        try:
            asyncio.run(self.run_agent_loop())
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("Agent loop stopped manually."))

    async def run_agent_loop(self):
        self.stdout.write(self.style.SUCCESS("Starting CROO Agent Worker..."))

        # Build SDK config — matches official CROO SDK documentation exactly
        # rpc_url is optional per docs, defaults to Base mainnet
        croo_config = Config(
            base_url=config('CROO_API_URL', default='https://api.croo.network'),
            ws_url=config('CROO_WS_URL', default='wss://api.croo.network/ws'),
            rpc_url=config('BASE_RPC_URL', default='https://mainnet.base.org'),
        )
        # CROO_SDK_KEY is the canonical env var name per official docs
        sdk_key = config('CROO_SDK_KEY', default=config('CROO_API_KEY', default=''))

        client = AgentClient(croo_config, sdk_key)

        # Connect WebSocket event stream
        stream = await client.connect_websocket()

        # ------------------------------------------------------------------
        # Register event handlers
        # ------------------------------------------------------------------

        def on_negotiation_created(e: Event):
            asyncio.create_task(self.handle_negotiation_created(client, e))

        def on_negotiation_rejected(e: Event):
            asyncio.create_task(self.handle_negotiation_status(e, 'rejected'))

        def on_negotiation_expired(e: Event):
            asyncio.create_task(self.handle_negotiation_status(e, 'expired'))

        def on_order_paid(e: Event):
            asyncio.create_task(self.handle_order_paid(client, e))

        def on_order_completed(e: Event):
            asyncio.create_task(self.handle_status_update(e, 'completed'))

        def on_order_rejected(e: Event):
            asyncio.create_task(self.handle_status_update(e, 'rejected'))

        def on_order_expired(e: Event):
            asyncio.create_task(self.handle_status_update(e, 'expired'))

        # All event types listed in official CROO SDK docs
        stream.on(EventType.NEGOTIATION_CREATED, on_negotiation_created)
        stream.on(EventType.NEGOTIATION_REJECTED, on_negotiation_rejected)
        stream.on(EventType.NEGOTIATION_EXPIRED, on_negotiation_expired)
        stream.on(EventType.ORDER_PAID, on_order_paid)
        stream.on(EventType.ORDER_COMPLETED, on_order_completed)
        stream.on(EventType.ORDER_REJECTED, on_order_rejected)
        stream.on(EventType.ORDER_EXPIRED, on_order_expired)

        self.stdout.write(self.style.SUCCESS(
            "Agent connected — listening for events "
            "(NEGOTIATION_CREATED, ORDER_PAID, ORDER_COMPLETED, ORDER_REJECTED, ORDER_EXPIRED)"
        ))

        # Graceful shutdown on SIGINT / SIGTERM
        loop = asyncio.get_running_loop()
        stop_event = asyncio.Event()

        def _signal_handler():
            self.stdout.write(self.style.WARNING("\nShutdown signal received, closing..."))
            stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _signal_handler)
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                pass

        # Keep alive until closed
        try:
            await stop_event.wait()
        except asyncio.CancelledError:
            pass
        finally:
            await stream.close()
            await client.close()
            self.stdout.write(self.style.SUCCESS("Agent shut down cleanly."))

    # ------------------------------------------------------------------
    # NEGOTIATION_CREATED  →  auto-accept + log
    # ------------------------------------------------------------------

    async def handle_negotiation_created(self, client: AgentClient, e: Event):
        logger.info("NEGOTIATION_CREATED: negotiation_id=%s", e.negotiation_id)
        self.stdout.write(f"Received NEGOTIATION_CREATED: {e.negotiation_id}")

        try:
            # First, fetch the negotiation to validate metadata BEFORE accepting
            neg = await client.get_negotiation(e.negotiation_id)
            metadata_str = str(getattr(neg, 'metadata', '')).lower()
            valid_keywords = ['trust', 'balance', 'verify', 'report', 'export', 'log']
            
            if not any(kw in metadata_str for kw in valid_keywords):
                # Reject the negotiation instantly so the buyer isn't charged
                reason = "Invalid metadata format. Must contain a valid service keyword."
                await client.reject_negotiation(e.negotiation_id, reason)
                self.stdout.write(self.style.WARNING(f"Rejected negotiation {e.negotiation_id}: {reason}"))
                await sync_to_async(NegotiationLog.objects.update_or_create)(
                    negotiation_id=e.negotiation_id,
                    defaults={
                        'service_id': e.service_id,
                        'requester_agent_id': e.requester_agent_id,
                        'provider_agent_id': e.provider_agent_id,
                        'status': 'rejected',
                    },
                )
                return

            result = await client.accept_negotiation(e.negotiation_id)
            logger.info(
                "Negotiation accepted: negotiation_id=%s  order_id=%s",
                e.negotiation_id, result.order.order_id,
            )

            # Persist to DB
            await sync_to_async(NegotiationLog.objects.update_or_create)(
                negotiation_id=e.negotiation_id,
                defaults={
                    'service_id': e.service_id,
                    'requester_agent_id': e.requester_agent_id,
                    'provider_agent_id': e.provider_agent_id,
                    'status': 'accepted',
                },
            )
            self.stdout.write(self.style.SUCCESS(
                f"Negotiation {e.negotiation_id} accepted → order {result.order.order_id}"
            ))

        except APIError as err:
            logger.error("Failed to accept negotiation %s: %s", e.negotiation_id, err)
            self.stderr.write(self.style.ERROR(
                f"Failed to accept negotiation {e.negotiation_id}: {err}"
            ))
            await sync_to_async(NegotiationLog.objects.update_or_create)(
                negotiation_id=e.negotiation_id,
                defaults={
                    'service_id': e.service_id,
                    'requester_agent_id': e.requester_agent_id,
                    'provider_agent_id': e.provider_agent_id,
                    'status': 'rejected',
                },
            )
        except Exception as ex:
            logger.exception("Unexpected error handling negotiation %s", e.negotiation_id)
            self.stderr.write(self.style.ERROR(
                f"Unexpected error for negotiation {e.negotiation_id}: {ex}"
            ))

    # ------------------------------------------------------------------
    # NEGOTIATION_REJECTED / NEGOTIATION_EXPIRED  →  update log
    # ------------------------------------------------------------------

    async def handle_negotiation_status(self, e: Event, new_status: str):
        """Update NegotiationLog when a negotiation is rejected or expired by the network."""
        logger.info("Negotiation %s → %s", e.negotiation_id, new_status)
        self.stdout.write(f"Negotiation {e.negotiation_id} → {new_status}")

        def _update():
            try:
                log = NegotiationLog.objects.get(negotiation_id=e.negotiation_id)
                log.status = new_status
                log.save(update_fields=['status'])
            except NegotiationLog.DoesNotExist:
                # May not exist if we never accepted it — create a record anyway
                NegotiationLog.objects.create(
                    negotiation_id=e.negotiation_id,
                    status=new_status,
                )

        await sync_to_async(_update)()

    # ------------------------------------------------------------------
    # ORDER_PAID  →  verify + log + deliver
    # ------------------------------------------------------------------

    async def handle_order_paid(self, client: AgentClient, e: Event):
        logger.info("ORDER_PAID: order_id=%s", e.order_id)
        self.stdout.write(f"Received ORDER_PAID: {e.order_id}")

        try:
            # Fetch full order details — returns an Order dataclass
            order = await client.get_order(e.order_id)

            # Extract fields from the dataclass (NOT a dict)
            buyer_id = order.buyer_user_id or order.requester_agent_id or 'unknown'
            raw_amount = float(getattr(order, 'fee_amount', 0) or getattr(order, 'price', 0) or 0)
            amount_usdc = str(raw_amount / 1000000) if raw_amount else '0'
            target_agent_id = order.provider_agent_id or 'default_agent'

            # Order dataclass has no 'metadata' field — fetch it from the Negotiation
            metadata_str = ''
            if order.negotiation_id:
                try:
                    neg = await client.get_negotiation(order.negotiation_id)
                    metadata_str = str(getattr(neg, 'metadata', '')).lower()
                    logger.debug("Fetched metadata from negotiation %s: %r", order.negotiation_id, metadata_str)
                except Exception as neg_err:
                    logger.warning("Could not fetch negotiation %s for metadata: %s", order.negotiation_id, neg_err)

            if 'balance' in metadata_str:
                # Service: Wallet Balance Retrieval
                def _get_balance():
                    wallet = VirtualWallet.objects.filter(agent_id=buyer_id).first()
                    return wallet.balance_usdc if wallet else '0.000000'
                
                bal = await sync_to_async(_get_balance)()
                formatted_bal = float(bal) / 1000000 if bal else 0
                deliver_text = f"WALLET BALANCE: {formatted_bal:.6f} USDC"
                self.stdout.write(self.style.SUCCESS(f"Delivered balance check for {buyer_id}"))

            elif 'verify' in metadata_str:
                # Service: Receipt Verification
                def _get_last_tx():
                    return TransactionAuditLog.objects.filter(buyer_id=buyer_id).first()
                
                last_tx = await sync_to_async(_get_last_tx)()
                if last_tx:
                    formatted_amt = float(last_tx.amount_usdc) / 1000000 if last_tx.amount_usdc else 0
                    deliver_text = f"VERIFIED. Last order {last_tx.order_id} was {formatted_amt:.6f} USDC. Status: {last_tx.status}."
                else:
                    deliver_text = "INVALID. No verified transactions found for this agent."
                self.stdout.write(self.style.SUCCESS(f"Delivered receipt verification for {buyer_id}"))

            elif 'report' in metadata_str:
                # Service: Transaction Summary Report
                def _get_report():
                    total = TransactionAuditLog.objects.filter(buyer_id=buyer_id).aggregate(Sum('amount_usdc'))['amount_usdc__sum']
                    count = TransactionAuditLog.objects.filter(buyer_id=buyer_id).count()
                    return total or 0, count

                total_spent, tx_count = await sync_to_async(_get_report)()
                formatted_total = float(total_spent) / 1000000 if total_spent else 0
                deliver_text = f"ANALYTICS REPORT: Total spent = {formatted_total:.6f} USDC across {tx_count} transactions."
                self.stdout.write(self.style.SUCCESS(f"Delivered analytics report for {buyer_id}"))

            elif 'trust' in metadata_str:
                # Service: Trust Score Lookup
                # metadata_str comes from the negotiation — parse JSON target from it
                target_agent_id_lookup = buyer_id  # safe default
                import json
                
                if order.negotiation_id:
                    try:
                        # metadata_str is lowercased, so load from the raw negotiation metadata
                        neg_raw = await client.get_negotiation(order.negotiation_id)
                        raw_metadata = str(getattr(neg_raw, 'metadata', '') or '{}')
                        meta_dict = json.loads(raw_metadata)
                        
                        # 1. Handle official CROO dashboard's nested "text" wrapper
                        if 'text' in meta_dict and isinstance(meta_dict['text'], str):
                            try:
                                inner_meta = json.loads(meta_dict['text'])
                                if 'target' in inner_meta:
                                    target_agent_id_lookup = inner_meta['target']
                            except Exception:
                                pass # Inner string isn't JSON, rely on fallback
                                
                        # 2. Handle pure un-nested JSON (like from our React UI)
                        if target_agent_id_lookup == buyer_id and 'target' in meta_dict:
                            target_agent_id_lookup = meta_dict['target']
                    except Exception as me:
                        logger.warning("Could not parse trust target from JSON metadata: %s", me)
                        
                # 3. Final fallback: try extracting directly from lowercased metadata_str
                if target_agent_id_lookup == buyer_id:
                    parts = metadata_str.split('target', 1)
                    if len(parts) > 1:
                        # grab the UUID-like value after 'target': '
                        candidate = parts[1].strip().lstrip(':').strip().strip('"').strip("'").split('"')[0].split("'")[0].split('}')[0].strip()
                        if candidate and len(candidate) > 8:
                            target_agent_id_lookup = candidate

                def _compute_and_save(target_id, order_id_str, buyer):
                    report = compute_trust_score(target_id)
                    report['order_id'] = order_id_str
                    import json
                    TrustScoreLookup.objects.update_or_create(
                        order_id=order_id_str,
                        defaults=dict(
                            target_agent_id=target_id,
                            requesting_buyer_id=buyer,
                            trust_score=report['trust_score'],
                            result_json=json.dumps(report, default=str),
                        ),
                    )
                    return report

                report = await sync_to_async(_compute_and_save)(
                    target_agent_id_lookup, e.order_id, buyer_id
                )

                # Format a human-readable delivery string
                flags_str = ', '.join(report['flags']) if report['flags'] else 'none'
                deliver_text = (
                    f"TRUST SCORE REPORT\n"
                    f"==================\n"
                    f"Target Agent   : {report['target_agent_id']}\n"
                    f"Trust Score    : {report['trust_score']} / 100\n"
                    f"Completed Orders: {report['completed_orders']}\n"
                    f"Disputed Orders : {report['disputed_or_refunded_orders']}\n"
                    f"Completion Rate : {report['completion_rate']:.1%}\n"
                    f"Dispute Rate    : {report['dispute_rate']:.1%}\n"
                    f"Avg Delivery vs SLA: {report['avg_delivery_vs_sla']:.2f}x\n"
                    f"Total Volume   : {report['total_volume_usdc']} USDC\n"
                    f"Unique Buyers  : {report['unique_buyer_count']}\n"
                    f"Account Age    : {report['account_age_days']} days\n"
                    f"Flags          : {flags_str}\n"
                    f"Summary        : {report['summary']}\n"
                    f"Call ID        : {report['call_id']}\n"
                )
                self.stdout.write(self.style.SUCCESS(
                    f"Delivered trust score lookup for {target_agent_id_lookup} "
                    f"(score={report['trust_score']}) to {buyer_id}"
                ))

            elif 'export' in metadata_str:
                # Service: Tax CSV Export
                domain = config('ALLOWED_HOSTS').split(',')[0] if config('ALLOWED_HOSTS') else '127.0.0.1'
                protocol = "http" if domain in ['localhost', '127.0.0.1'] else "https"
                download_link = f"{protocol}://{domain}:8000/api/export/{buyer_id}/" if protocol == "http" else f"{protocol}://{domain}/api/export/{buyer_id}/"
                
                deliver_text = f"TAX EXPORT READY. Download your CSV here: {download_link}"
                self.stdout.write(self.style.SUCCESS(f"Delivered tax export link for {buyer_id}"))

            elif 'log' in metadata_str:
                # Service: Automated Transaction Logging
                verify_func = sync_to_async(verify_and_log_payment)
                audit_log = await verify_func(
                    order_id=e.order_id,
                    buyer_id=buyer_id,
                    amount_usdc=amount_usdc,
                    target_agent_id=target_agent_id,
                    negotiation_id=order.negotiation_id,
                    service_id=order.service_id,
                    provider_agent_id=order.provider_agent_id,
                )

                self.stdout.write(self.style.SUCCESS(
                    f"Ledger verified for order {e.order_id} — {amount_usdc} USDC"
                ))
                deliver_text = "TRANSACTION_LOGGED_SUCCESSFULLY"

            else:
                # This should be impossible since we rejected invalid metadata earlier,
                # but if it happens, return an error text instead of charging them for a log.
                deliver_text = "ERROR: UNKNOWN SERVICE REQUESTED"

            # Deliver the order on-chain
            deliver_req = DeliverOrderRequest(
                deliverable_type=DeliverableType.TEXT,
                deliverable_text=deliver_text,
            )
            result = await client.deliver_order(e.order_id, deliver_req)

            # Update the audit log with tx_hash and delivered_at (only for logging service)
            non_logging_services = ('balance', 'verify', 'report', 'export', 'trust')
            if not any(svc in metadata_str for svc in non_logging_services):
                def _mark_delivered():
                    log = TransactionAuditLog.objects.get(order_id=e.order_id)
                    log.tx_hash = result.tx_hash
                    log.delivered_at = timezone.now()
                    log.save(update_fields=['tx_hash', 'delivered_at'])

                await sync_to_async(_mark_delivered)()

            self.stdout.write(self.style.SUCCESS(
                f"Order {e.order_id} delivered — tx_hash={result.tx_hash}"
            ))

        except ValueError as ve:
            # Idempotency: order already processed
            logger.warning("Duplicate order %s: %s", e.order_id, ve)
            self.stderr.write(self.style.WARNING(f"Duplicate order {e.order_id}: {ve}"))

        except APIError as err:
            if is_not_found(err):
                logger.error("Order %s not found: %s", e.order_id, err)
                self.stderr.write(self.style.ERROR(f"Order {e.order_id} not found: {err}"))
            elif is_insufficient_balance(err):
                logger.error("Insufficient balance to process order %s: %s", e.order_id, err)
                self.stderr.write(self.style.ERROR(f"Insufficient balance for order {e.order_id}: {err}"))
            elif is_unauthorized(err):
                logger.error("Auth failure for order %s: %s", e.order_id, err)
                self.stderr.write(self.style.ERROR(f"Auth failure for order {e.order_id}: {err}"))
            elif is_forbidden(err):
                logger.error("Forbidden: order %s: %s", e.order_id, err)
                self.stderr.write(self.style.ERROR(f"Forbidden for order {e.order_id}: {err}"))
            elif is_invalid_status(err):
                logger.warning("Invalid status transition for order %s: %s", e.order_id, err)
                self.stderr.write(self.style.WARNING(f"Invalid status for order {e.order_id}: {err}"))
            else:
                logger.error("API error for order %s: %s", e.order_id, err)
                self.stderr.write(self.style.ERROR(f"API error for order {e.order_id}: {err}"))
            await self._mark_order_failed(e.order_id)

        except Exception as ex:
            logger.exception("Unexpected error processing order %s", e.order_id)
            self.stderr.write(self.style.ERROR(
                f"Unexpected error for order {e.order_id}: {ex}"
            ))
            await self._mark_order_failed(e.order_id)

    # ------------------------------------------------------------------
    # ORDER_COMPLETED / REJECTED / EXPIRED  →  status update
    # ------------------------------------------------------------------

    async def handle_status_update(self, e: Event, new_status: str):
        logger.info("Order status update: order_id=%s → %s", e.order_id, new_status)

        def _update():
            try:
                log = TransactionAuditLog.objects.get(order_id=e.order_id)
                log.status = new_status
                log.save(update_fields=['status'])
            except TransactionAuditLog.DoesNotExist:
                logger.warning(
                    "Status update for unknown order %s (status=%s)",
                    e.order_id, new_status,
                )

        await sync_to_async(_update)()
        self.stdout.write(f"Order {e.order_id} → {new_status}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _mark_order_failed(self, order_id: str):
        """Set audit log status to 'failed' if it exists."""
        def _fail():
            try:
                log = TransactionAuditLog.objects.get(order_id=order_id)
                log.status = 'failed'
                log.save(update_fields=['status'])
            except TransactionAuditLog.DoesNotExist:
                pass

        await sync_to_async(_fail)()
