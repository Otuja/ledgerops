"""
requester_agent.py — Test-buyer agent for the Croo provider.

Run from the croo_backend directory (with venv active):
    python requester_agent.py [service] [target_agent_id]

Available services:
    default   — triggers the default transaction-logging service
    balance   — requests wallet balance retrieval
    verify    — requests receipt verification
    report    — requests analytics report
    export    — requests tax CSV export
    trust     — requests a Trust Score Lookup on [target_agent_id]
                (defaults to the provider agent ID if not supplied)

If no service is specified, 'default' is used.

Requirements in .env:
    CROO_REQUESTER_SDK_KEY   — the requester (buyer) agent's SDK key
    CROO_SERVICE_ID_DEFAULT  — the service ID for default logging
    CROO_SERVICE_ID_BALANCE  — the service ID for balance check
    CROO_SERVICE_ID_VERIFY   — the service ID for receipt verification
    CROO_SERVICE_ID_REPORT   — the service ID for analytics report
    CROO_SERVICE_ID_EXPORT   — the service ID for tax CSV export
    CROO_SERVICE_ID_TRUST    — the service ID for Trust Score Lookup
    CROO_API_URL             — Croo API base URL  (default: https://api.croo.network)
"""

import asyncio
import sys
import time

from decouple import config

from croo import (
    AgentClient,
    Config,
    NegotiateOrderRequest,
    NegotiationStatus,
    OrderStatus,
    APIError,
)

# ── Config ────────────────────────────────────────────────────────────────────

REQUESTER_SDK_KEY = config('CROO_REQUESTER_SDK_KEY', default='')
API_URL           = config('CROO_API_URL', default='https://api.croo.network')
RPC_URL           = config('BASE_RPC_URL',  default='https://mainnet.base.org')

# How long (seconds) to poll waiting for the provider to accept / pay receipt
POLL_INTERVAL       = 3    # seconds between status checks
NEGOTIATION_TIMEOUT = 120  # seconds to wait for provider to accept
ORDER_TIMEOUT       = 180  # seconds to wait for delivery after paying

# ── Service metadata ──────────────────────────────────────────────────────────

# These map the CLI service name to the associated metadata string
# and the corresponding environment variable containing its service ID.
SERVICE_CONFIG = {
    'default': {'metadata': '',          'env_var': 'CROO_SERVICE_ID_DEFAULT'},
    'balance': {'metadata': 'balance',   'env_var': 'CROO_SERVICE_ID_BALANCE'},
    'verify':  {'metadata': 'verify',    'env_var': 'CROO_SERVICE_ID_VERIFY'},
    'report':  {'metadata': 'report',    'env_var': 'CROO_SERVICE_ID_REPORT'},
    'export':  {'metadata': 'export',    'env_var': 'CROO_SERVICE_ID_EXPORT'},
    # Trust Score Lookup — metadata carries the target agent ID after the colon
    # The actual metadata value is built dynamically in run_test() below
    'trust':   {'metadata': None,        'env_var': 'CROO_SERVICE_ID_TRUST'},
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _banner(msg: str) -> None:
    width = 72
    print('\n' + '─' * width)
    print(f'  {msg}')
    print('─' * width)


def _check_config(service_key: str) -> str:
    errors = []
    if not REQUESTER_SDK_KEY:
        errors.append('CROO_REQUESTER_SDK_KEY is not set in .env')
    
    env_var = SERVICE_CONFIG[service_key]['env_var']
    service_id = config(env_var, default='')
    
    if not service_id:
        errors.append(
            f'{env_var} is not set in .env — '
            f'find it on the Croo dashboard under your {service_key} service listing'
        )
    if errors:
        print('\n❌  Missing configuration:')
        for e in errors:
            print(f'    • {e}')
        sys.exit(1)
        
    return service_id


# ── Core flow ─────────────────────────────────────────────────────────────────

async def run_test(service: str, trust_target: str = '') -> None:
    if service not in SERVICE_CONFIG:
        print(f'❌  Unknown service "{service}". '
              f'Choose from: {", ".join(SERVICE_CONFIG.keys())}')
        sys.exit(1)

    service_id = _check_config(service)

    # For the trust service, build metadata as "trust:<target_agent_id>"
    if service == 'trust':
        target_id = trust_target or config('CROO_SDK_KEY', default='unknown_provider')
        metadata = f'trust:{target_id}'
        print(f'  ℹ  Looking up trust score for agent: {target_id}')
    else:
        metadata = SERVICE_CONFIG[service]['metadata']

    requirements = f'Test request for service: {service}'

    croo_config = Config(
        base_url=API_URL,
        rpc_url=RPC_URL,
    )
    client = AgentClient(croo_config, REQUESTER_SDK_KEY)

    try:
        # ── Step 1: Negotiate ────────────────────────────────────────────────
        _banner(f'STEP 1 — Negotiating  (service={service!r}, service_id={service_id})')
        req = NegotiateOrderRequest(
            service_id=service_id,
            requirements=requirements,
            metadata=metadata,
        )
        negotiation = await client.negotiate_order(req)
        neg_id = negotiation.negotiation_id
        print(f'  ✓  Negotiation created: {neg_id}  (status={negotiation.status})')

        # ── Step 2: Wait for provider to accept ──────────────────────────────
        _banner(f'STEP 2 — Waiting for provider to accept  (timeout={NEGOTIATION_TIMEOUT}s)')
        deadline = time.monotonic() + NEGOTIATION_TIMEOUT
        order_id: str | None = None

        while time.monotonic() < deadline:
            neg = await client.get_negotiation(neg_id)
            print(f'  … negotiation status = {neg.status}')

            if neg.status == NegotiationStatus.ACCEPTED:
                # The accept call returns the order — fetch it via list
                orders = await client.list_orders()
                # Find the order linked to this negotiation
                for o in orders:
                    if o.negotiation_id == neg_id:
                        order_id = o.order_id
                        break
                if order_id:
                    print(f'  ✓  Accepted → order_id={order_id}')
                    break
                # If not found yet, give the network a moment
                await asyncio.sleep(POLL_INTERVAL)
                continue

            if neg.status in (NegotiationStatus.REJECTED, NegotiationStatus.EXPIRED):
                print(f'\n❌  Negotiation {neg.status} — provider refused or it timed out.')
                return

            await asyncio.sleep(POLL_INTERVAL)
        else:
            print(f'\n❌  Provider did not accept within {NEGOTIATION_TIMEOUT}s.')
            return

        # ── Step 3: Pay ───────────────────────────────────────────────────────
        _banner(f'STEP 3 — Paying order  (order_id={order_id})')
        try:
            pay_result = await client.pay_order(order_id)
            print(f'  ✓  Paid  (tx_hash={pay_result.tx_hash or "pending"}, '
                  f'status={pay_result.order.status})')
        except APIError as err:
            print(f'\n❌  Pay failed: {err}')
            print('    (This is normal in sandbox/staging if wallet has no real USDC balance)')
            print('    The provider agent will still receive ORDER_PAID once the network processes it.')
            # Don't exit — in test environments the event may still fire

        # ── Step 4: Wait for delivery ─────────────────────────────────────────
        _banner(f'STEP 4 — Waiting for delivery  (timeout={ORDER_TIMEOUT}s)')
        deadline = time.monotonic() + ORDER_TIMEOUT

        while time.monotonic() < deadline:
            try:
                order = await client.get_order(order_id)
                print(f'  … order status = {order.status}')

                if order.status == OrderStatus.COMPLETED:
                    delivery = await client.get_delivery(order_id)
                    _banner('✅  DELIVERY RECEIVED')
                    print(f'  delivery_id  : {delivery.delivery_id}')
                    print(f'  type         : {delivery.deliverable_type}')
                    print(f'  status       : {delivery.status}')
                    print(f'  content      :\n\n    {delivery.deliverable_text}\n')
                    return

                if order.status in (OrderStatus.REJECTED, OrderStatus.EXPIRED,
                                    OrderStatus.DELIVER_FAILED, OrderStatus.PAY_FAILED):
                    print(f'\n❌  Order ended with status: {order.status}')
                    if order.reject_reason:
                        print(f'    Reason: {order.reject_reason}')
                    return

            except APIError as err:
                print(f'  ⚠  Could not fetch order: {err}')

            await asyncio.sleep(POLL_INTERVAL)
        else:
            print(f'\n⏱  No delivery received within {ORDER_TIMEOUT}s.')

    except APIError as err:
        print(f'\n❌  API error: {err}')
    finally:
        await client.close()


# ── Entry point ────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    service = sys.argv[1] if len(sys.argv) > 1 else 'default'
    trust_target = sys.argv[2] if len(sys.argv) > 2 else ''
    print(f'\n🤖  Croo Requester Agent — testing service: {service!r}')
    print(f'    API: {API_URL}')
    asyncio.run(run_test(service, trust_target))
