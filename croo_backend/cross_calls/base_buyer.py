"""
cross_calls/base_buyer.py — Reusable async negotiate→pay→deliver coroutine.

Extracted from requester_agent.py so all cross-agent scripts share one
implementation.  Returns a structured CallResult dict rather than printing
to stdout, so the orchestrator can aggregate results.
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

from croo import (
    AgentClient,
    Config,
    NegotiateOrderRequest,
    NegotiationStatus,
    OrderStatus,
    APIError,
    ListOptions,
)

logger = logging.getLogger('croo.cross_calls')

# ── Timing constants ──────────────────────────────────────────────────────────

POLL_INTERVAL       =   3   # seconds between status polls
NEGOTIATION_TIMEOUT = 120   # seconds to wait for provider acceptance
ORDER_TIMEOUT       = 180   # seconds to wait for delivery after paying


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class CallResult:
    """
    Outcome of a single negotiate→pay→deliver cycle.
    status values:
        'ok'      — delivery received
        'timeout' — provider didn't accept or deliver within timeout
        'error'   — API or unexpected exception
        'skipped' — call was not attempted (e.g. missing config)
    """
    status: str = 'error'                 # 'ok' | 'timeout' | 'error' | 'skipped'
    order_id: str = ''
    negotiation_id: str = ''
    amount_usdc: str = ''
    delivery_text: str = ''
    error_detail: str = ''
    skip_reason: str = ''


# ── Core coroutine ────────────────────────────────────────────────────────────

async def buy_service(
    *,
    buyer_label:  str,
    sdk_key:      str,
    service_id:   str,
    metadata:     str,
    requirements: str,
    api_url:      str = 'https://api.croo.network',
    rpc_url:      str = 'https://mainnet.base.org',
    verbose:      bool = True,
) -> CallResult:
    """
    Execute one full negotiate→pay→deliver cycle as the given buyer.

    Parameters
    ----------
    buyer_label   : Human-readable name for logging (e.g. "Orchestrator")
    sdk_key       : The buyer's CROO SDK key
    service_id    : The target service's on-chain ID (0x…)
    metadata      : Metadata string forwarded to the provider
    requirements  : Requirements string (shown to provider during negotiation)
    api_url       : CROO REST API base URL
    rpc_url       : Base chain RPC URL
    verbose       : If True, prints progress to stdout
    """

    def _log(msg: str) -> None:
        if verbose:
            print(f"  [{buyer_label}] {msg}")

    result = CallResult()
    croo_config = Config(base_url=api_url, rpc_url=rpc_url)
    client = AgentClient(croo_config, sdk_key)

    try:
        # ── Step 1: Negotiate ────────────────────────────────────────────────
        _log(f"Negotiating → service_id={service_id[:10]}…  metadata={metadata!r}")
        req = NegotiateOrderRequest(
            service_id=service_id,
            requirements=requirements,
            metadata=metadata,
        )
        negotiation = await client.negotiate_order(req)
        neg_id = negotiation.negotiation_id
        result.negotiation_id = neg_id
        _log(f"Negotiation created: {neg_id}  (status={negotiation.status})")

        # ── Step 2: Wait for provider acceptance ─────────────────────────────
        deadline = time.monotonic() + NEGOTIATION_TIMEOUT
        order_id: Optional[str] = None

        while time.monotonic() < deadline:
            neg = await client.get_negotiation(neg_id)

            if neg.status == NegotiationStatus.ACCEPTED:
                orders = await client.list_orders(ListOptions(role='buyer'))
                for o in orders:
                    if o.negotiation_id == neg_id:
                        order_id = o.order_id
                        break
                if order_id:
                    result.order_id = order_id
                    _log(f"Accepted → order_id={order_id}")
                    break
                await asyncio.sleep(POLL_INTERVAL)
                continue

            if neg.status in (NegotiationStatus.REJECTED, NegotiationStatus.EXPIRED):
                msg = f"Negotiation ended with status={neg.status}"
                _log(f"❌ {msg}")
                result.status = 'error'
                result.error_detail = msg
                return result

            await asyncio.sleep(POLL_INTERVAL)
        else:
            msg = f"Provider did not accept within {NEGOTIATION_TIMEOUT}s"
            _log(f"⏱ {msg}")
            result.status = 'timeout'
            result.error_detail = msg
            return result

        # ── Step 3: Pay ───────────────────────────────────────────────────────
        try:
            pay_result = await client.pay_order(order_id)
            paid_price = getattr(pay_result.order, 'price', '')
            result.amount_usdc = paid_price
            _log(f"Paid  (tx_hash={pay_result.tx_hash or 'pending'}  price={paid_price})")
        except APIError as err:
            _log(f"⚠ Pay error (continuing — network may still fire ORDER_PAID): {err}")
            # Don't abort — sandbox/staging environments may still deliver

        # ── Step 4: Wait for delivery ─────────────────────────────────────────
        deadline = time.monotonic() + ORDER_TIMEOUT

        while time.monotonic() < deadline:
            try:
                order = await client.get_order(order_id)
                _log(f"… order status = {order.status}")

                if order.status == OrderStatus.COMPLETED:
                    delivery = await client.get_delivery(order_id)
                    text = delivery.deliverable_text or ''
                    result.status = 'ok'
                    result.delivery_text = text
                    result.amount_usdc = result.amount_usdc or getattr(order, 'price', '')
                    _log(f"✅ Delivered: {text[:120].strip()!r}…")
                    return result

                if order.status in (
                    OrderStatus.REJECTED, OrderStatus.EXPIRED,
                    OrderStatus.DELIVER_FAILED, OrderStatus.PAY_FAILED,
                ):
                    msg = f"Order ended with status={order.status}"
                    if getattr(order, 'reject_reason', ''):
                        msg += f" — {order.reject_reason}"
                    _log(f"❌ {msg}")
                    result.status = 'error'
                    result.error_detail = msg
                    return result

            except APIError as err:
                _log(f"⚠ Could not fetch order: {err}")

            await asyncio.sleep(POLL_INTERVAL)

        msg = f"No delivery within {ORDER_TIMEOUT}s"
        _log(f"⏱ {msg}")
        result.status = 'timeout'
        result.error_detail = msg
        return result

    except APIError as err:
        msg = f"APIError: {err}"
        _log(f"❌ {msg}")
        result.status = 'error'
        result.error_detail = msg
        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        result.status = 'error'
        result.error_detail = f"{type(e).__name__}: {str(e)}"
        _log(f"❌ {result.error_detail}")
        return result

    finally:
        await client.close()
