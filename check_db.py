import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'croo_backend.settings')
django.setup()

from ledger.models import TrustScoreLookup, TransactionAuditLog, VirtualWallet, NegotiationLog

print('=== TrustScoreLookup in DB ===')
for t in TrustScoreLookup.objects.all():
    oid = (t.order_id or '')[:8] or '(none)'
    print(f'  {oid} buyer={str(t.requesting_buyer_id)[:12]} target={str(t.target_agent_id)[:12]} score={t.trust_score}')

print()
print('=== TransactionAuditLog in DB ===')
for t in TransactionAuditLog.objects.all():
    print(f'  {t.order_id[:8]} amount={t.amount_usdc} status={t.status}')
if not TransactionAuditLog.objects.exists():
    print('  (empty)')

print()
print('=== VirtualWallet in DB ===')
for w in VirtualWallet.objects.all():
    print(f'  {str(w.agent_id)[:16]} balance={w.balance_usdc}')
if not VirtualWallet.objects.exists():
    print('  (empty)')
