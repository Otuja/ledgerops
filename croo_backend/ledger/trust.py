"""
ledger/trust.py — Trust Score computation for the CROO Credit Bureau service.

Public API
----------
    compute_trust_score(target_agent_id: str) -> dict

All metrics are derived from real aggregated data in TransactionAuditLog and
NegotiationLog.  No hardcoded scores — every number comes from DB queries.

Scoring Formula
---------------
trust_score = round(100 * (
    0.40 * completion_rate                     # most important: does the agent deliver?
    + 0.25 * (1 - dispute_rate)               # low disputes = trustworthy
    + 0.15 * min(1, unique_buyer_count / 10)  # buyer diversity shows organic demand
    + 0.10 * min(1, account_age_days / 14)    # age ≥ 14 days = full maturity bonus
    + 0.10 * min(1, 60 / avg_delivery_secs)   # fast delivery vs 60s SLA target
))

Edge cases:
- No transactions at all → all metrics 0, score 0, flag "recent_account"
- No completed deliveries → avg_delivery_vs_sla contribution = 0
- score is clamped to [0, 100]

Flag thresholds
---------------
    high_self_trade_concentration  → single buyer > 50 % of total volume
    low_buyer_diversity            → unique_buyer_count < 3
    recent_account                 → account_age_days < 2
    high_dispute_rate              → dispute_rate > 0.15
"""

import uuid
import logging
from decimal import Decimal
from django.db.models import Sum, Count, Q, Max, Min
from django.utils import timezone

logger = logging.getLogger('croo.agent')

# SLA target in seconds — matches the 0h 1m SLA registered on the CROO network.
SLA_SECONDS = 60.0

# Flag thresholds
SELF_TRADE_CONCENTRATION_THRESHOLD = 0.50   # top buyer > 50% of volume
LOW_BUYER_DIVERSITY_THRESHOLD = 3           # fewer than 3 unique buyers
RECENT_ACCOUNT_DAYS_THRESHOLD = 2           # account younger than 2 days
HIGH_DISPUTE_RATE_THRESHOLD = 0.15          # more than 15% disputed orders

# Score weight components (must sum to 1.0)
W_COMPLETION   = 0.40
W_NO_DISPUTE   = 0.25
W_DIVERSITY    = 0.15
W_AGE          = 0.10
W_DELIVERY_SPD = 0.10


def compute_trust_score(target_agent_id: str) -> dict:
    """
    Compute a comprehensive trust/reputation report for ``target_agent_id``.

    Queries the ``ledger`` app's existing models — no external calls.
    Returns a dict matching the Trust Score Lookup output schema exactly.
    """
    # Import here to avoid circular imports (models import from this module's callers)
    from ledger.models import TransactionAuditLog, NegotiationLog

    # ── 1. Pull all orders where this agent was the provider ─────────────────
    orders = TransactionAuditLog.objects.filter(agent_id=target_agent_id)
    total_orders = orders.count()

    # Short-circuit for completely unknown agents: no data = no score.
    # We still return the full schema with zeroed fields so callers always
    # get a machine-readable response. The only flag is 'recent_account'.
    if total_orders == 0 and not NegotiationLog.objects.filter(
        provider_agent_id=target_agent_id
    ).exists():
        call_id = str(uuid.uuid4())
        return {
            'target_agent_id': target_agent_id,
            'trust_score': 0,
            'completed_orders': 0,
            'disputed_or_refunded_orders': 0,
            'completion_rate': 0.0,
            'dispute_rate': 0.0,
            'avg_delivery_vs_sla': 1.0,
            'total_volume_usdc': 0.0,
            'unique_buyer_count': 0,
            'account_age_days': 0,
            'flags': ['recent_account'],
            'summary': (
                'No transaction history found for this agent. '
                'Exercise extreme caution — this agent has no verifiable track record on LedgerOps.'
            ),
            'call_id': call_id,
            'order_id': '',
        }

    # ── 2. Core counts ────────────────────────────────────────────────────────
    completed_orders = orders.filter(status__in=['completed', 'verified']).count()
    disputed_orders = orders.filter(
        Q(is_disputed=True) | Q(status='failed') | Q(status='rejected')
    ).count()

    # completion_rate: completed / (completed + disputed + other terminal states)
    # Abandoned = expired orders
    abandoned_orders = orders.filter(status='expired').count()
    denominator = completed_orders + disputed_orders + abandoned_orders
    completion_rate = (completed_orders / denominator) if denominator > 0 else 0.0

    # dispute_rate: disputed / total orders (all records, not just terminal)
    dispute_rate = (disputed_orders / total_orders) if total_orders > 0 else 0.0

    # ── 3. Volume ─────────────────────────────────────────────────────────────
    total_volume_result = orders.aggregate(total=Sum('amount_usdc'))['total']
    total_volume_usdc = float(total_volume_result or Decimal('0')) / 1000000.0

    # ── 4. Buyer diversity ────────────────────────────────────────────────────
    unique_buyer_count = orders.values('buyer_id').distinct().count()

    # ── 5. Account age ────────────────────────────────────────────────────────
    first_tx_ts = orders.aggregate(first=Min('timestamp'))['first']
    # Also check NegotiationLog as provider
    first_neg_ts = NegotiationLog.objects.filter(
        provider_agent_id=target_agent_id
    ).aggregate(first=Min('created_at'))['first']

    # Use whichever is earliest
    candidates = [ts for ts in (first_tx_ts, first_neg_ts) if ts is not None]
    if candidates:
        first_seen = min(candidates)
        account_age_days = max(0, (timezone.now() - first_seen).days)
    else:
        account_age_days = 0

    # ── 6. Delivery speed vs SLA ──────────────────────────────────────────────
    # avg_delivery_vs_sla = mean(actual_delivery_seconds / SLA_SECONDS)
    # Only consider orders that have both a timestamp and a delivered_at.
    delivered_orders = orders.exclude(delivered_at__isnull=True)
    delivery_deltas = []
    for order in delivered_orders.only('timestamp', 'delivered_at'):
        if order.delivered_at and order.timestamp:
            delta_secs = (order.delivered_at - order.timestamp).total_seconds()
            if delta_secs > 0:
                delivery_deltas.append(delta_secs / SLA_SECONDS)

    if delivery_deltas:
        avg_delivery_vs_sla = sum(delivery_deltas) / len(delivery_deltas)
    else:
        avg_delivery_vs_sla = 1.0  # neutral if no deliveries recorded yet

    # ── 7. Self-trade concentration ───────────────────────────────────────────
    # Find the single buyer with the largest share of total volume
    if total_volume_usdc > 0:
        buyer_volumes = (
            orders.values('buyer_id')
            .annotate(vol=Sum('amount_usdc'))
            .order_by('-vol')
        )
        first_buyer = buyer_volumes.first()
        if first_buyer:
            top_buyer_vol = float(first_buyer.get('vol') or 0)
            self_trade_ratio = top_buyer_vol / total_volume_usdc
        else:
            self_trade_ratio = 0.0
    else:
        self_trade_ratio = 0.0

    # ── 8. Flags ──────────────────────────────────────────────────────────────
    flags = []
    if self_trade_ratio > SELF_TRADE_CONCENTRATION_THRESHOLD:
        flags.append('high_self_trade_concentration')
    if unique_buyer_count < LOW_BUYER_DIVERSITY_THRESHOLD and total_orders > 0:
        flags.append('low_buyer_diversity')
    if account_age_days < RECENT_ACCOUNT_DAYS_THRESHOLD:
        flags.append('recent_account')
    if dispute_rate > HIGH_DISPUTE_RATE_THRESHOLD:
        flags.append('high_dispute_rate')

    # ── 9. Trust score ────────────────────────────────────────────────────────
    # Delivery speed component: reward agents who deliver faster than SLA.
    # If avg_delivery_vs_sla = 0.5, the agent delivers in half the SLA → full bonus.
    # Guard against division by zero (avg_delivery_vs_sla is always ≥ 0).
    if avg_delivery_vs_sla > 0:
        speed_component = min(1.0, 1.0 / avg_delivery_vs_sla)
    else:
        speed_component = 0.0

    raw_score = (
        W_COMPLETION   * completion_rate
        + W_NO_DISPUTE * (1.0 - dispute_rate)
        + W_DIVERSITY  * min(1.0, unique_buyer_count / 10.0)
        + W_AGE        * min(1.0, account_age_days / 14.0)
        + W_DELIVERY_SPD * speed_component
    )

    trust_score = max(0, min(100, round(raw_score * 100)))

    # ── 10. Summary (template-based, no LLM) ─────────────────────────────────
    summary = _generate_summary(trust_score, flags, completed_orders, total_orders, unique_buyer_count)

    # ── 11. Assemble result ───────────────────────────────────────────────────
    call_id = str(uuid.uuid4())

    result = {
        'target_agent_id': target_agent_id,
        'trust_score': trust_score,
        'completed_orders': completed_orders,
        'disputed_or_refunded_orders': disputed_orders,
        'completion_rate': round(completion_rate, 4),
        'dispute_rate': round(dispute_rate, 4),
        'avg_delivery_vs_sla': round(avg_delivery_vs_sla, 4),
        'total_volume_usdc': round(total_volume_usdc, 6),
        'unique_buyer_count': unique_buyer_count,
        'account_age_days': account_age_days,
        'flags': flags,
        'summary': summary,
        'call_id': call_id,
        'order_id': '',  # populated by the caller (worker or view) if applicable
    }

    logger.info(
        "Trust score computed: agent=%s score=%d flags=%s",
        target_agent_id, trust_score, flags,
    )
    return result


def _generate_summary(
    trust_score: int,
    flags: list[str],
    completed_orders: int,
    total_orders: int,
    unique_buyer_count: int,
) -> str:
    """Generate a plain-language 1-2 sentence trust assessment from the metrics."""

    if total_orders == 0:
        return (
            "No transaction history found for this agent. "
            "Exercise extreme caution — this agent has no verifiable track record on LedgerOps."
        )

    if trust_score >= 80:
        opener = "Strong track record"
        if not flags:
            detail = "high completion rate and diverse buyer base with no red flags detected."
        else:
            flag_str = _flag_to_text(flags[0])
            detail = f"high completion rate, though note: {flag_str}."
        return f"{opener}: {detail}"

    if trust_score >= 60:
        opener = "Moderate trust profile"
        if flags:
            flag_str = " and ".join(_flag_to_text(f) for f in flags[:2])
            detail = f"acceptable history but flagged for {flag_str} — verify independently before large engagements."
        else:
            detail = "solid history with room for improvement in diversity or volume."
        return f"{opener}: {detail}"

    if trust_score >= 40:
        opener = "Caution advised"
        if flags:
            flag_str = " and ".join(_flag_to_text(f) for f in flags[:2])
            detail = f"limited history with flags: {flag_str}. Start with small transactions."
        else:
            detail = "limited transaction history. Start with small test transactions."
        return f"{opener}: {detail}"

    # < 40
    opener = "High risk"
    if 'high_dispute_rate' in flags:
        detail = "elevated dispute rate and low reliability score — engage only with significant safeguards."
    elif flags:
        flag_str = " and ".join(_flag_to_text(f) for f in flags[:2])
        detail = f"flagged for {flag_str} with very limited verifiable history."
    else:
        detail = "very limited transaction history and low score — insufficient data to establish trust."
    return f"{opener}: {detail}"


def _flag_to_text(flag: str) -> str:
    """Convert a machine flag name to a readable phrase."""
    return {
        'high_self_trade_concentration': 'high self-trade concentration (wash trading risk)',
        'low_buyer_diversity': 'low buyer diversity (few unique counterparties)',
        'recent_account': 'recently created account (less than 2 days old)',
        'high_dispute_rate': 'elevated dispute/refund rate (>15%)',
    }.get(flag, flag)
