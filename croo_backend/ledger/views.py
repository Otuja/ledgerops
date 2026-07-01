from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count, Q
from django.http import HttpResponse
import csv

from .models import TransactionAuditLog, VirtualWallet, NegotiationLog, TrustScoreLookup
from .trust import compute_trust_score
from .serializers import (
    TransactionAuditLogSerializer,
    VirtualWalletSerializer,
    NegotiationLogSerializer,
    DashboardSummarySerializer,
)


# ---------------------------------------------------------------------------
# Transaction Audit Logs
# ---------------------------------------------------------------------------

@api_view(['GET'])
def list_logs(request):
    """Return all transaction audit logs, optionally filtered by status."""
    qs = TransactionAuditLog.objects.all()

    status_filter = request.query_params.get('status')
    if status_filter:
        qs = qs.filter(status=status_filter)

    serializer = TransactionAuditLogSerializer(qs, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_log(request, order_id):
    """Return a single transaction audit log by order_id."""
    try:
        log = TransactionAuditLog.objects.get(order_id=order_id)
    except TransactionAuditLog.DoesNotExist:
        return Response(
            {'detail': f'Transaction {order_id} not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = TransactionAuditLogSerializer(log)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def export_taxes(request, agent_id):
    """Dynamically generate and return a CSV file of an agent's transactions."""
    transactions = TransactionAuditLog.objects.filter(buyer_id=agent_id).order_by('-timestamp')
    
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="ledgerops_tax_export_{agent_id}.csv"'},
    )
    
    writer = csv.writer(response)
    # Write CSV Header
    writer.writerow(['Order ID', 'Timestamp', 'Status', 'Amount (USDC)', 'Provider Agent ID', 'Service ID', 'Transaction Hash'])
    
    # Write data rows
    for tx in transactions:
        writer.writerow([
            tx.order_id,
            tx.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
            tx.status,
            f"{(tx.amount_usdc / 1000000):.6f}",
            tx.provider_agent_id,
            tx.service_id,
            tx.tx_hash,
        ])
        
    return response


# ---------------------------------------------------------------------------
# Wallets
# ---------------------------------------------------------------------------

@api_view(['GET'])
def get_wallet(request):
    """Return the aggregate wallet balance for the dashboard."""
    wallets = VirtualWallet.objects.all()
    total_balance = wallets.aggregate(total=Sum('balance_usdc'))['total'] or 0
    return Response({
        'balance_usdc': f"{total_balance:.6f}",
        'wallet_count': wallets.count(),
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def list_wallets(request):
    """Return all individual agent wallets."""
    qs = VirtualWallet.objects.all()
    serializer = VirtualWalletSerializer(qs, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Negotiations
# ---------------------------------------------------------------------------

@api_view(['GET'])
def list_negotiations(request):
    """Return all negotiation logs, optionally filtered by status."""
    qs = NegotiationLog.objects.all()

    status_filter = request.query_params.get('status')
    if status_filter:
        qs = qs.filter(status=status_filter)

    serializer = NegotiationLogSerializer(qs, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Dashboard Stats
# ---------------------------------------------------------------------------

@api_view(['GET'])
def dashboard_stats(request):
    """Aggregate statistics for the dashboard stat cards."""
    wallets = VirtualWallet.objects.all()
    total_balance = wallets.aggregate(total=Sum('balance_usdc'))['total'] or 0

    tx_counts = TransactionAuditLog.objects.aggregate(
        total=Count('id'),
        verified=Count('id', filter=Q(status='verified')),
        pending=Count('id', filter=Q(status='pending')),
        failed=Count('id', filter=Q(status='failed')),
        completed=Count('id', filter=Q(status='completed')),
    )

    neg_counts = NegotiationLog.objects.aggregate(
        total=Count('id'),
        accepted=Count('id', filter=Q(status='accepted')),
        pending=Count('id', filter=Q(status='pending')),
    )

    data = {
        'total_balance': f"{total_balance:.6f}",
        'wallet_count': wallets.count(),
        'transaction_count': tx_counts['total'],
        'verified_count': tx_counts['verified'],
        'pending_count': tx_counts['pending'],
        'failed_count': tx_counts['failed'],
        'completed_count': tx_counts['completed'],
        'negotiation_count': neg_counts['total'],
        'negotiations_accepted': neg_counts['accepted'],
        'negotiations_pending': neg_counts['pending'],
    }
    serializer = DashboardSummarySerializer(data)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@api_view(['GET'])
def health_check(request):
    """Simple health-check for uptime monitoring."""
    return Response({'status': 'ok'}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Trust Score Lookup
# ---------------------------------------------------------------------------

@api_view(['GET'])
def get_trust_score(request, agent_id):
    """
    Compute and return a real-time trust report for any agent ID.
    Returns a 200 with zeroed metrics for unknown agents (not a 404),
    so callers always get a machine-readable response.
    """
    report = compute_trust_score(agent_id)
    return Response(report, status=status.HTTP_200_OK)


@api_view(['GET'])
def list_trust_lookups(request):
    """Return the audit log of all paid Trust Score Lookup orders."""
    import json
    lookups = TrustScoreLookup.objects.all()
    data = []
    for lookup in lookups:
        data.append({
            'call_id': str(lookup.call_id),
            'order_id': lookup.order_id,
            'target_agent_id': lookup.target_agent_id,
            'requesting_buyer_id': lookup.requesting_buyer_id,
            'trust_score': lookup.trust_score,
            'created_at': lookup.created_at,
        })
    return Response(data, status=status.HTTP_200_OK)
