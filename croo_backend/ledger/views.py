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
    """Return all activity — transaction audit logs merged with trust score lookups."""
    import json
    status_filter = request.query_params.get('status')

    # Regular transaction logs
    qs = TransactionAuditLog.objects.all()
    if status_filter:
        qs = qs.filter(status=status_filter)
    tx_data = TransactionAuditLogSerializer(qs, many=True).data

    # Trust score lookups — map to the same shape so the frontend table works
    if not status_filter or status_filter in ('completed', 'verified'):
        trust_lookups = TrustScoreLookup.objects.all()
        trust_rows = []
        for t in trust_lookups:
            trust_rows.append({
                'order_id': t.order_id or str(t.call_id),
                'negotiation_id': '',
                'service_id': 'trust_score_lookup',
                'buyer_id': t.requesting_buyer_id or 'unknown',
                'agent_id': t.target_agent_id,
                'provider_agent_id': '',
                'amount_usdc': '0.000000',
                'tx_hash': '',
                'status': 'completed',
                'timestamp': t.created_at,
                'delivered_at': t.created_at,
                'trust_score': t.trust_score,
            })
    else:
        trust_rows = []

    # Merge and sort by timestamp descending
    combined = list(tx_data) + trust_rows
    combined.sort(key=lambda x: str(x.get('timestamp', '')), reverse=True)

    return Response(combined, status=status.HTTP_200_OK)


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
    import asyncio
    from decouple import config as env
    from croo import AgentClient, Config, ListOptions

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

    # Include trust score lookups in the transaction count
    trust_count = TrustScoreLookup.objects.count()

    # --- Fetch real CROO on-chain earnings ---
    croo_earnings = 0.0
    croo_orders_completed = trust_count + tx_counts['completed']  # DB baseline
    try:
        sdk_key = env('CROO_SDK_KEY', default=env('CROO_API_KEY', default=''))
        if sdk_key:
            croo_cfg = Config(
                base_url=env('CROO_API_URL', default='https://api.croo.network'),
                ws_url=env('CROO_WS_URL', default='wss://api.croo.network/ws'),
            )
            async def _fetch():
                c = AgentClient(croo_cfg, sdk_key)
                all_orders = []
                page = 1
                while True:
                    opts = ListOptions(role='provider', page=page, page_size=100)
                    res = await c.list_orders(opts)
                    items = getattr(res, 'data', None)
                    if items is None:
                        items = getattr(res, 'items', res)
                        if not isinstance(items, list):
                            items = getattr(items, 'data', [])
                    all_orders.extend(items)
                    if len(items) < 100:
                        break
                    page += 1
                await c.close()
                return all_orders
            orders = asyncio.run(_fetch())
            completed_orders = [o for o in orders if o.status == 'completed']
            croo_orders_completed = len(completed_orders)
            
            # Use fee_amount to calculate actual on-chain volume transferred
            croo_earnings = sum(float(getattr(o, 'fee_amount', 0) or getattr(o, 'price', 0) or 0) for o in completed_orders) / 1_000_000
    except Exception as e:
        print("Error fetching CROO stats:", e)
        pass  # Fallback to DB baseline if CROO API unavailable

    # If CROO reports more completed orders than our DB, use CROO count
    final_completed = max(croo_orders_completed, trust_count + tx_counts['completed'])
    final_balance = max(total_balance, croo_earnings)

    data = {
        'total_balance': f"{final_balance:.6f}",
        'wallet_count': max(wallets.count(), 1) if final_completed > 0 else wallets.count(),
        'transaction_count': max(tx_counts['total'] + trust_count, final_completed),
        'verified_count': tx_counts['verified'],
        'pending_count': tx_counts['pending'],
        'failed_count': tx_counts['failed'],
        'completed_count': final_completed,
        'negotiation_count': neg_counts['total'],
        'negotiations_accepted': neg_counts['accepted'],
        'negotiations_pending': neg_counts['pending'],
    }
    serializer = DashboardSummarySerializer(data)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@api_view(['GET', 'HEAD'])
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


# ---------------------------------------------------------------------------
# Interactive Dashboard Services
# ---------------------------------------------------------------------------

@api_view(['POST'])
def execute_service(request):
    import asyncio
    import os
    import time
    from croo import AgentClient, Config
    from decouple import config as decouple_config
    import json
    
    service_type = request.data.get('service_type')
    target_agent_id = request.data.get('target_agent_id')
    
    if not service_type:
        return Response({'error': 'service_type is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Convert frontend service names to exact pure-JSON payloads the backend expects
    if service_type == 'trust':
        metadata_dict = {"trust": "true", "target": target_agent_id}
    elif service_type == 'tax':
        metadata_dict = {"export": "true"}
    elif service_type == 'analytics':
        metadata_dict = {"report": "true"}
    elif service_type == 'receipt':
        metadata_dict = {"verify": "true"}
    else:
        return Response({'error': 'invalid service_type'}, status=status.HTTP_400_BAD_REQUEST)

    def run_purchase():
        provider_agent_id = 'c1266046-1744-4cf6-a8a5-ba5eb35bccca' # LedgerOps
        buyer_key = decouple_config('CROO_SECONDARY_BUYER_SDK_KEY', default='')
        
        croo_config = Config(
            base_url=decouple_config('CROO_API_URL', default='https://api.croo.network'),
            ws_url=decouple_config('CROO_WS_URL', default='wss://api.croo.network/ws'),
            rpc_url=decouple_config('BASE_RPC_URL', default='https://mainnet.base.org'),
        )
        buyer_client = AgentClient(croo_config, buyer_key)
        
        async def do_buy():
            from croo.models import NegotiateOrderRequest, ServiceFilter
            try:
                # 1. Fetch provider's active service ID
                services = await buyer_client.get_services(query=ServiceFilter(agent_id=provider_agent_id))
                if not services:
                    return {"error": "Provider LedgerOps has no registered services."}
                target_service_id = services[0].service_id
                
                # 2. Negotiate with perfect JSON metadata
                req = NegotiateOrderRequest(
                    service_id=target_service_id,
                    metadata=json.dumps(metadata_dict)
                )
                neg = await buyer_client.negotiate_order(req)
                
                # 3. Wait for acceptance (timeout 30s)
                order_id = None
                for _ in range(30):
                    check = await buyer_client.get_negotiation(neg.negotiation_id)
                    if check.status == 'accepted':
                        order_id = check.order_id
                        break
                    elif check.status == 'rejected':
                        return {"error": f"Negotiation rejected by provider: {check.rejection_reason}"}
                    time.sleep(1)
                
                if not order_id:
                    return {"error": "Negotiation timed out."}
                
                # 4. Wait for order to be created
                for _ in range(30):
                    order = await buyer_client.get_order(order_id)
                    if order.status == 'created':
                        break
                    time.sleep(1)
                
                # 5. Pay for the order
                await buyer_client.pay_order(order_id)
                
                # 6. Wait for delivery
                for _ in range(60):
                    order = await buyer_client.get_order(order_id)
                    if order.status == 'delivered':
                        return {
                            "success": True, 
                            "order_id": order_id, 
                            "result": order.deliverable_text,
                            "tx_hash": getattr(order, 'tx_hash', None)
                        }
                    time.sleep(1)
                    
                return {"error": "Payment succeeded but provider timed out during delivery."}
                
            except Exception as ex:
                return {"error": str(ex)}
            finally:
                await buyer_client.close()
                
        return asyncio.run(do_buy())

    result = run_purchase()
    if "error" in result:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    return Response(result, status=status.HTTP_200_OK)
