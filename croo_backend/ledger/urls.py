from django.urls import path
from . import views

urlpatterns = [
    path('logs/', views.list_logs, name='list-logs'),
    path('logs/<str:order_id>/', views.get_log, name='get-log'),
    path('wallet/', views.get_wallet, name='get-wallet'),
    path('wallets/', views.list_wallets, name='list-wallets'),
    path('negotiations/', views.list_negotiations, name='list-negotiations'),
    path('stats/', views.dashboard_stats, name='dashboard-stats'),
    path('health/', views.health_check, name='health-check'),
    path('export/<str:agent_id>/', views.export_taxes, name='export-taxes'),
    path('trust-score/<str:agent_id>/', views.get_trust_score, name='trust-score'),
    path('trust-lookups/', views.list_trust_lookups, name='trust-lookups'),
]
