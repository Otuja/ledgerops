from django.contrib import admin
from .models import TransactionAuditLog, VirtualWallet, NegotiationLog


@admin.register(TransactionAuditLog)
class TransactionAuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'order_id', 'buyer_id', 'agent_id', 'amount_usdc',
        'status', 'timestamp', 'delivered_at',
    ]
    list_filter = ['status', 'timestamp']
    search_fields = ['order_id', 'buyer_id', 'agent_id', 'tx_hash']
    readonly_fields = [
        'order_id', 'negotiation_id', 'service_id',
        'buyer_id', 'agent_id', 'provider_agent_id',
        'amount_usdc', 'tx_hash', 'timestamp', 'delivered_at',
    ]
    ordering = ['-timestamp']


@admin.register(VirtualWallet)
class VirtualWalletAdmin(admin.ModelAdmin):
    list_display = ['agent_id', 'balance_usdc', 'last_updated']
    search_fields = ['agent_id']
    readonly_fields = ['last_updated']
    ordering = ['-balance_usdc']


@admin.register(NegotiationLog)
class NegotiationLogAdmin(admin.ModelAdmin):
    list_display = [
        'negotiation_id', 'service_id',
        'requester_agent_id', 'provider_agent_id',
        'status', 'created_at',
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['negotiation_id', 'service_id', 'requester_agent_id']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
