from rest_framework import serializers
from .models import TransactionAuditLog, VirtualWallet, NegotiationLog


class TransactionAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionAuditLog
        fields = [
            'order_id',
            'negotiation_id',
            'service_id',
            'buyer_id',
            'agent_id',
            'provider_agent_id',
            'amount_usdc',
            'tx_hash',
            'status',
            'timestamp',
            'delivered_at',
        ]


class VirtualWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = VirtualWallet
        fields = [
            'agent_id',
            'balance_usdc',
            'last_updated',
        ]


class NegotiationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NegotiationLog
        fields = [
            'negotiation_id',
            'service_id',
            'requester_agent_id',
            'provider_agent_id',
            'status',
            'fund_amount',
            'fund_token',
            'metadata',
            'created_at',
            'updated_at',
        ]


class DashboardSummarySerializer(serializers.Serializer):
    total_balance = serializers.CharField()
    wallet_count = serializers.IntegerField()
    transaction_count = serializers.IntegerField()
    verified_count = serializers.IntegerField()
    pending_count = serializers.IntegerField()
    failed_count = serializers.IntegerField()
    completed_count = serializers.IntegerField()
    negotiation_count = serializers.IntegerField()
    negotiations_accepted = serializers.IntegerField()
    negotiations_pending = serializers.IntegerField()
