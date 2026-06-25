from django.db import models, transaction
from django.utils import timezone
from decimal import Decimal
import uuid


class NegotiationLog(models.Model):
    """Tracks every negotiation event received from the CROO network."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    negotiation_id = models.CharField(max_length=255, unique=True)
    service_id = models.CharField(max_length=255, blank=True, default='')
    requester_agent_id = models.CharField(max_length=255, blank=True, default='')
    provider_agent_id = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    fund_amount = models.CharField(max_length=255, blank=True, default='')
    fund_token = models.CharField(max_length=255, blank=True, default='')
    metadata = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.negotiation_id} — {self.status}"


class VirtualWallet(models.Model):
    """Virtual USDC wallet per agent."""

    agent_id = models.CharField(max_length=255, unique=True)
    balance_usdc = models.DecimalField(
        max_digits=20, decimal_places=6, default=Decimal('0.000000'),
    )
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-balance_usdc']

    def __str__(self):
        return f"{self.agent_id} — {self.balance_usdc} USDC"


class TransactionAuditLog(models.Model):
    """
    Immutable audit record for every order processed through the agent.
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    order_id = models.CharField(max_length=255, unique=True)
    negotiation_id = models.CharField(max_length=255, blank=True, default='')
    service_id = models.CharField(max_length=255, blank=True, default='')
    buyer_id = models.CharField(max_length=255)
    agent_id = models.CharField(max_length=255, blank=True, default='')
    provider_agent_id = models.CharField(max_length=255, blank=True, default='')
    amount_usdc = models.DecimalField(max_digits=20, decimal_places=6)
    tx_hash = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    # is_disputed: set to True if the buyer raises a dispute / requests a refund.
    # Used by compute_trust_score() to calculate the provider agent's dispute_rate.
    is_disputed = models.BooleanField(default=False, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.order_id} — {self.status}"


class TrustScoreLookup(models.Model):
    """
    Audit record for every paid Trust Score Lookup order.
    Stores the full computed report so lookups are reproducible and inspectable.
    """
    call_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    order_id = models.CharField(max_length=255, blank=True, default='')
    target_agent_id = models.CharField(max_length=255)
    requesting_buyer_id = models.CharField(max_length=255, blank=True, default='')
    trust_score = models.IntegerField(default=0)
    # Full JSON-serialisable result dict stored as text for auditability
    result_json = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"TrustLookup {self.call_id} — {self.target_agent_id} (score={self.trust_score})"


def verify_and_log_payment(order_id, buyer_id, amount_usdc, target_agent_id,
                           negotiation_id='', service_id='', provider_agent_id=''):
    """
    Atomically verifies a payment, updates the target agent's wallet balance,
    and logs the transaction.  Idempotent — raises ValueError on duplicate order_id.
    """
    with transaction.atomic():  # type: ignore[attr-defined]
        # 1. Ensure the target agent wallet exists and lock the row
        wallet, _created = VirtualWallet.objects.select_for_update().get_or_create(
            agent_id=target_agent_id,
        )

        # 2. Idempotency check
        if TransactionAuditLog.objects.filter(order_id=order_id).exists():
            raise ValueError(f"Transaction with order_id {order_id} already exists.")

        # 3. Create the audit log as 'verified'
        audit_log = TransactionAuditLog.objects.create(
            order_id=order_id,
            buyer_id=buyer_id,
            amount_usdc=Decimal(str(amount_usdc)),
            agent_id=target_agent_id,
            negotiation_id=negotiation_id,
            service_id=service_id,
            provider_agent_id=provider_agent_id,
            status='verified',
        )

        # 4. Credit the wallet
        wallet.balance_usdc += Decimal(str(amount_usdc))
        wallet.save()

        return audit_log
