import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'croo_backend.settings')
django.setup()
from django.apps import apps

NegotiationLog = apps.get_model('ledger', 'NegotiationLog')
TransactionAuditLog = apps.get_model('ledger', 'TransactionAuditLog')

print("=== Service IDs from NegotiationLog ===")
for row in NegotiationLog.objects.values('service_id', 'metadata').distinct():
    sid = row['service_id']
    meta = row['metadata']
    print(f"  service_id={sid}  metadata={meta}")

print()
print("=== Service IDs from TransactionAuditLog ===")
for row in TransactionAuditLog.objects.values('service_id').distinct():
    sid = row['service_id']
    print(f"  service_id={sid}")

if not NegotiationLog.objects.exists() and not TransactionAuditLog.objects.exists():
    print("No records yet in DB.")
