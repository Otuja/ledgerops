from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import TransactionTestCase
from rest_framework.test import APITransactionTestCase
from rest_framework import status

from .models import (
    TransactionAuditLog,
    VirtualWallet,
    NegotiationLog,
    TrustScoreLookup,
    verify_and_log_payment,
)
from .trust import compute_trust_score


# ========================================================================
# Model Tests
# ========================================================================

class VerifyAndLogPaymentTests(TransactionTestCase):
    """Tests for the verify_and_log_payment atomic helper."""

    def test_happy_path(self):
        """Creates audit log and credits wallet on first call."""
        log = verify_and_log_payment(
            order_id='ord_001',
            buyer_id='buyer_0x1',
            amount_usdc='100.500000',
            target_agent_id='agent_A',
        )
        self.assertEqual(log.order_id, 'ord_001')
        self.assertEqual(log.buyer_id, 'buyer_0x1')
        self.assertEqual(log.status, 'verified')
        self.assertEqual(log.agent_id, 'agent_A')
        self.assertEqual(log.amount_usdc, Decimal('100.500000'))

        wallet = VirtualWallet.objects.get(agent_id='agent_A')
        self.assertEqual(wallet.balance_usdc, Decimal('100.500000'))

    def test_idempotency_raises_on_duplicate(self):
        """Second call with same order_id raises ValueError."""
        verify_and_log_payment('ord_dup', 'buyer', '50', 'agent_B')

        with self.assertRaises(ValueError) as ctx:
            verify_and_log_payment('ord_dup', 'buyer', '50', 'agent_B')
        self.assertIn('already exists', str(ctx.exception))

    def test_wallet_accumulation(self):
        """Multiple payments to the same agent accumulate balance."""
        verify_and_log_payment('ord_1', 'buyer', '100', 'agent_C')
        verify_and_log_payment('ord_2', 'buyer', '200.50', 'agent_C')
        verify_and_log_payment('ord_3', 'buyer', '0.50', 'agent_C')

        wallet = VirtualWallet.objects.get(agent_id='agent_C')
        self.assertEqual(wallet.balance_usdc, Decimal('301.000000'))

    def test_zero_amount(self):
        """Zero amount is accepted (free transactions)."""
        log = verify_and_log_payment('ord_zero', 'buyer', '0', 'agent_D')
        self.assertEqual(log.amount_usdc, Decimal('0'))

        wallet = VirtualWallet.objects.get(agent_id='agent_D')
        self.assertEqual(wallet.balance_usdc, Decimal('0'))

    def test_extra_fields_stored(self):
        """negotiation_id, service_id, provider_agent_id are persisted."""
        log = verify_and_log_payment(
            order_id='ord_extra',
            buyer_id='buyer',
            amount_usdc='10',
            target_agent_id='agent_E',
            negotiation_id='neg_123',
            service_id='svc_abc',
            provider_agent_id='provider_xyz',
        )
        self.assertEqual(log.negotiation_id, 'neg_123')
        self.assertEqual(log.service_id, 'svc_abc')
        self.assertEqual(log.provider_agent_id, 'provider_xyz')


class NegotiationLogTests(TransactionTestCase):
    """Tests for the NegotiationLog model."""

    def test_create_and_str(self):
        neg = NegotiationLog.objects.create(
            negotiation_id='neg_001',
            service_id='svc_1',
            status='accepted',
        )
        self.assertIn('neg_001', str(neg))
        self.assertIn('accepted', str(neg))

    def test_default_ordering(self):
        NegotiationLog.objects.create(negotiation_id='neg_a', status='pending')
        NegotiationLog.objects.create(negotiation_id='neg_b', status='accepted')
        negs = list(NegotiationLog.objects.values_list('negotiation_id', flat=True))
        # Most recent first
        self.assertEqual(negs[0], 'neg_b')


# ========================================================================
# API Tests
# ========================================================================

class HealthCheckAPITests(APITransactionTestCase):
    def test_health_check(self):
        resp = self.client.get('/api/health/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()['status'], 'ok')


class LogsAPITests(APITransactionTestCase):
    def setUp(self):
        verify_and_log_payment('ord_api_1', 'buyer_1', '100', 'agent_1')
        verify_and_log_payment('ord_api_2', 'buyer_2', '200', 'agent_2')
        # Create a failed record manually
        TransactionAuditLog.objects.create(
            order_id='ord_api_3', buyer_id='buyer_3',
            amount_usdc='50', status='failed',
        )

    def test_list_logs_returns_all(self):
        resp = self.client.get('/api/logs/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.json()), 3)

    def test_list_logs_filter_by_status(self):
        resp = self.client.get('/api/logs/', {'status': 'verified'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(len(data), 2)
        for item in data:
            self.assertEqual(item['status'], 'verified')

    def test_list_logs_filter_failed(self):
        resp = self.client.get('/api/logs/', {'status': 'failed'})
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['order_id'], 'ord_api_3')

    def test_get_log_detail(self):
        resp = self.client.get('/api/logs/ord_api_1/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()['order_id'], 'ord_api_1')
        self.assertEqual(resp.json()['amount_usdc'], '100.000000')

    def test_get_log_detail_404(self):
        resp = self.client.get('/api/logs/nonexistent/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_logs_ordered_by_timestamp_desc(self):
        resp = self.client.get('/api/logs/')
        data = resp.json()
        # Most recent first
        self.assertEqual(data[0]['order_id'], 'ord_api_3')


class WalletAPITests(APITransactionTestCase):
    def setUp(self):
        verify_and_log_payment('ord_w1', 'buyer', '100', 'agent_X')
        verify_and_log_payment('ord_w2', 'buyer', '250', 'agent_Y')
        verify_and_log_payment('ord_w3', 'buyer', '50', 'agent_X')

    def test_get_wallet_aggregate(self):
        resp = self.client.get('/api/wallet/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(data['balance_usdc'], '400.000000')
        self.assertEqual(data['wallet_count'], 2)

    def test_list_wallets(self):
        resp = self.client.get('/api/wallets/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(len(data), 2)
        # Ordered by balance desc
        self.assertEqual(data[0]['agent_id'], 'agent_Y')
        self.assertEqual(data[0]['balance_usdc'], '250.000000')
        self.assertEqual(data[1]['agent_id'], 'agent_X')
        self.assertEqual(data[1]['balance_usdc'], '150.000000')


class NegotiationsAPITests(APITransactionTestCase):
    def setUp(self):
        NegotiationLog.objects.create(
            negotiation_id='neg_1', service_id='svc_1',
            requester_agent_id='req_1', provider_agent_id='prov_1',
            status='accepted',
        )
        NegotiationLog.objects.create(
            negotiation_id='neg_2', service_id='svc_2',
            status='pending',
        )

    def test_list_negotiations(self):
        resp = self.client.get('/api/negotiations/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.json()), 2)

    def test_list_negotiations_filter_by_status(self):
        resp = self.client.get('/api/negotiations/', {'status': 'accepted'})
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['negotiation_id'], 'neg_1')


class DashboardStatsAPITests(APITransactionTestCase):
    def setUp(self):
        verify_and_log_payment('ord_s1', 'buyer', '100', 'agent_1')
        verify_and_log_payment('ord_s2', 'buyer', '200', 'agent_2')
        TransactionAuditLog.objects.create(
            order_id='ord_s3', buyer_id='buyer', amount_usdc='50', status='failed',
        )
        NegotiationLog.objects.create(negotiation_id='neg_s1', status='accepted')
        NegotiationLog.objects.create(negotiation_id='neg_s2', status='pending')

    def test_dashboard_stats(self):
        resp = self.client.get('/api/stats/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(data['total_balance'], '300.000000')
        self.assertEqual(data['wallet_count'], 2)
        self.assertEqual(data['transaction_count'], 3)
        self.assertEqual(data['verified_count'], 2)
        self.assertEqual(data['failed_count'], 1)
        self.assertEqual(data['negotiation_count'], 2)
        self.assertEqual(data['negotiations_accepted'], 1)
        self.assertEqual(data['negotiations_pending'], 1)


# ========================================================================
# Agent Worker Tests (mock the SDK)
# ========================================================================

class AgentWorkerTests(TransactionTestCase):
    """Tests for the agent worker command handlers using mocked SDK."""

    def _make_command(self):
        """Create a Command instance with stdout/stderr mocked."""
        from ledger.management.commands.run_agent import Command
        cmd = Command()
        cmd.stdout = MagicMock()
        cmd.stderr = MagicMock()
        return cmd

    def _make_event(self, **kwargs):
        """Create a mock Event with the given fields."""
        from croo import Event
        return Event(**kwargs)

    @patch('ledger.management.commands.run_agent.AgentClient')
    def test_handle_order_paid_happy_path(self, MockClient):
        """ORDER_PAID handler creates audit log and calls deliver_order."""
        import asyncio
        from croo import Order, DeliverOrderResult, Delivery

        mock_client = AsyncMock()
        mock_client.get_order = AsyncMock(return_value=Order(
            order_id='ord_test',
            buyer_user_id='buyer_test',
            requester_agent_id='req_agent',
            provider_agent_id='prov_agent',
            price='500.000000',
            negotiation_id='neg_test',
            service_id='svc_test',
        ))
        mock_client.deliver_order = AsyncMock(return_value=DeliverOrderResult(
            order=Order(order_id='ord_test'),
            delivery=Delivery(),
            tx_hash='0xabc123',
        ))

        cmd = self._make_command()
        event = self._make_event(order_id='ord_test')

        asyncio.run(cmd.handle_order_paid(mock_client, event))

        # Verify audit log was created
        log = TransactionAuditLog.objects.get(order_id='ord_test')
        self.assertEqual(log.status, 'verified')
        self.assertEqual(log.amount_usdc, Decimal('500.000000'))
        self.assertEqual(log.buyer_id, 'buyer_test')
        self.assertEqual(log.agent_id, 'prov_agent')
        self.assertEqual(log.tx_hash, '0xabc123')
        self.assertIsNotNone(log.delivered_at)

        # Verify wallet was credited
        wallet = VirtualWallet.objects.get(agent_id='prov_agent')
        self.assertEqual(wallet.balance_usdc, Decimal('500.000000'))

        # Verify deliver_order was called
        mock_client.deliver_order.assert_called_once()

    @patch('ledger.management.commands.run_agent.AgentClient')
    def test_handle_order_paid_marks_failed_on_api_error(self, MockClient):
        """ORDER_PAID handler marks the log as 'failed' on APIError."""
        import asyncio
        from croo import Order, APIError

        mock_client = AsyncMock()
        mock_client.get_order = AsyncMock(return_value=Order(
            order_id='ord_fail',
            buyer_user_id='buyer',
            provider_agent_id='agent',
            price='100',
        ))
        mock_client.deliver_order = AsyncMock(
            side_effect=APIError(500, 500, 'server_error', 'Internal error'),
        )

        cmd = self._make_command()
        event = self._make_event(order_id='ord_fail')

        asyncio.run(cmd.handle_order_paid(mock_client, event))

        log = TransactionAuditLog.objects.get(order_id='ord_fail')
        self.assertEqual(log.status, 'failed')

    @patch('ledger.management.commands.run_agent.AgentClient')
    def test_handle_negotiation_created(self, MockClient):
        """NEGOTIATION_CREATED handler auto-accepts and logs."""
        import asyncio
        from croo import AcceptNegotiationResult, Negotiation, Order

        mock_client = AsyncMock()
        mock_client.accept_negotiation = AsyncMock(
            return_value=AcceptNegotiationResult(
                negotiation=Negotiation(negotiation_id='neg_auto'),
                order=Order(order_id='ord_from_neg'),
            )
        )

        cmd = self._make_command()
        event = self._make_event(
            negotiation_id='neg_auto',
            service_id='svc_1',
            requester_agent_id='req_a',
            provider_agent_id='prov_a',
        )

        asyncio.run(cmd.handle_negotiation_created(mock_client, event))

        mock_client.accept_negotiation.assert_called_once_with('neg_auto')
        neg_log = NegotiationLog.objects.get(negotiation_id='neg_auto')
        self.assertEqual(neg_log.status, 'accepted')
        self.assertEqual(neg_log.service_id, 'svc_1')

    def test_handle_status_update(self):
        """Status update handler changes audit log status."""
        import asyncio

        TransactionAuditLog.objects.create(
            order_id='ord_status', buyer_id='buyer',
            amount_usdc='100', status='verified',
        )

        cmd = self._make_command()
        event = self._make_event(order_id='ord_status')

        asyncio.run(cmd.handle_status_update(event, 'completed'))

        log = TransactionAuditLog.objects.get(order_id='ord_status')
        self.assertEqual(log.status, 'completed')

    def test_handle_status_update_unknown_order(self):
        """Status update for unknown order does not raise."""
        import asyncio

        cmd = self._make_command()
        event = self._make_event(order_id='ord_unknown')

        # Should not raise
        asyncio.run(cmd.handle_status_update(event, 'expired'))


# ========================================================================
# Trust Score Unit Tests
# ========================================================================

class ComputeTrustScoreTests(TransactionTestCase):
    """Unit tests for compute_trust_score() covering the key agent archetypes."""

    def _make_completed_order(self, order_id, buyer_id, agent_id, amount='100',
                              delivered=True, disputed=False):
        """Helper: create a completed TransactionAuditLog with optional delivery."""
        from django.utils import timezone
        import datetime
        now = timezone.now()
        log = TransactionAuditLog.objects.create(
            order_id=order_id,
            buyer_id=buyer_id,
            agent_id=agent_id,
            amount_usdc=Decimal(amount),
            status='completed' if not disputed else 'failed',
            is_disputed=disputed,
            timestamp=now - datetime.timedelta(seconds=30),
            delivered_at=now if delivered else None,
        )
        return log

    def test_perfect_agent(self):
        """Agent with many diverse buyers, no disputes, fast delivery → high score, no flags."""
        for i in range(10):
            self._make_completed_order(
                order_id=f'ord_perf_{i}',
                buyer_id=f'buyer_{i}',
                agent_id='agent_perfect',
                amount='100',
                delivered=True,
                disputed=False,
            )

        result = compute_trust_score('agent_perfect')

        self.assertEqual(result['target_agent_id'], 'agent_perfect')
        self.assertGreaterEqual(result['trust_score'], 70, "Perfect agent should score ≥ 70")
        self.assertEqual(result['disputed_or_refunded_orders'], 0)
        self.assertEqual(result['unique_buyer_count'], 10)
        self.assertNotIn('high_dispute_rate', result['flags'])
        self.assertNotIn('low_buyer_diversity', result['flags'])
        self.assertIn('call_id', result)

    def test_disputed_agent(self):
        """Agent with >15% dispute rate → high_dispute_rate flag, reduced score."""
        # 2 clean orders, 1 disputed order (33% dispute rate)
        self._make_completed_order('ord_d1', 'buyer_a', 'agent_disputed')
        self._make_completed_order('ord_d2', 'buyer_b', 'agent_disputed')
        self._make_completed_order('ord_d3', 'buyer_c', 'agent_disputed', disputed=True)

        result = compute_trust_score('agent_disputed')

        self.assertIn('high_dispute_rate', result['flags'])
        self.assertGreater(result['dispute_rate'], 0.15)
        self.assertLess(result['trust_score'], 80)

    def test_low_diversity_agent(self):
        """Agent with fewer than 3 unique buyers → low_buyer_diversity flag."""
        # 5 orders all from the same buyer
        for i in range(5):
            self._make_completed_order(
                order_id=f'ord_low_{i}',
                buyer_id='sole_buyer',
                agent_id='agent_low_div',
            )

        result = compute_trust_score('agent_low_div')

        self.assertIn('low_buyer_diversity', result['flags'])
        self.assertEqual(result['unique_buyer_count'], 1)

    def test_brand_new_agent(self):
        """Agent with no transactions → recent_account flag, score = 0."""
        result = compute_trust_score('agent_brand_new_xyz_no_data')

        self.assertIn('recent_account', result['flags'])
        self.assertEqual(result['trust_score'], 0)
        self.assertEqual(result['completed_orders'], 0)
        self.assertEqual(result['total_volume_usdc'], 0.0)

    def test_self_trade_concentration(self):
        """Single buyer accounts for >50% of volume → high_self_trade_concentration flag."""
        # 1 dominant buyer with 80% of the volume
        self._make_completed_order('ord_conc1', 'whale_buyer', 'agent_conc', amount='800')
        self._make_completed_order('ord_conc2', 'other_buyer', 'agent_conc', amount='100')
        self._make_completed_order('ord_conc3', 'another_buyer', 'agent_conc', amount='100')

        result = compute_trust_score('agent_conc')

        self.assertIn('high_self_trade_concentration', result['flags'])

    def test_score_clamped_to_100(self):
        """Trust score is always in [0, 100] regardless of input."""
        for i in range(20):
            self._make_completed_order(
                order_id=f'ord_clamp_{i}',
                buyer_id=f'buyer_{i}',
                agent_id='agent_clamp',
            )
        result = compute_trust_score('agent_clamp')
        self.assertGreaterEqual(result['trust_score'], 0)
        self.assertLessEqual(result['trust_score'], 100)

    def test_result_has_all_required_fields(self):
        """Result dict contains all fields specified in the output schema."""
        required = [
            'target_agent_id', 'trust_score', 'completed_orders',
            'disputed_or_refunded_orders', 'completion_rate', 'dispute_rate',
            'avg_delivery_vs_sla', 'total_volume_usdc', 'unique_buyer_count',
            'account_age_days', 'flags', 'summary', 'call_id', 'order_id',
        ]
        result = compute_trust_score('any_agent')
        for field in required:
            self.assertIn(field, result, f"Missing required field: {field}")


# ========================================================================
# Trust Score API Tests
# ========================================================================

class TrustScoreAPITests(APITransactionTestCase):
    """Integration tests for the /api/trust-score/<agent_id>/ endpoint."""

    def setUp(self):
        # Seed some data for a known agent
        verify_and_log_payment('ord_api_t1', 'buyer_1', '100', 'agent_known')
        verify_and_log_payment('ord_api_t2', 'buyer_2', '200', 'agent_known')

    def test_trust_score_known_agent_returns_200(self):
        resp = self.client.get('/api/trust-score/agent_known/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(data['target_agent_id'], 'agent_known')
        self.assertIn('trust_score', data)
        self.assertIn('flags', data)
        self.assertIn('summary', data)
        self.assertIsInstance(data['trust_score'], int)
        self.assertIsInstance(data['flags'], list)

    def test_trust_score_unknown_agent_returns_200_with_zero_score(self):
        """Unknown agent should return 200 with zeroed metrics, not a 404."""
        resp = self.client.get('/api/trust-score/totally_unknown_agent_id/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(data['trust_score'], 0)
        self.assertEqual(data['completed_orders'], 0)
        self.assertEqual(data['total_volume_usdc'], 0.0)

    def test_trust_score_response_has_all_schema_fields(self):
        resp = self.client.get('/api/trust-score/agent_known/')
        data = resp.json()
        for field in ['target_agent_id', 'trust_score', 'completed_orders',
                      'disputed_or_refunded_orders', 'completion_rate', 'dispute_rate',
                      'avg_delivery_vs_sla', 'total_volume_usdc', 'unique_buyer_count',
                      'account_age_days', 'flags', 'summary', 'call_id']:
            self.assertIn(field, data, f"Missing field in API response: {field}")


# ========================================================================
# Trust Score Worker Tests
# ========================================================================

class TrustScoreWorkerTests(TransactionTestCase):
    """Tests for the trust service branch in the agent worker."""

    def _make_command(self):
        from ledger.management.commands.run_agent import Command
        cmd = Command()
        cmd.stdout = MagicMock()
        cmd.stderr = MagicMock()
        return cmd

    def _make_event(self, **kwargs):
        from croo import Event
        return Event(**kwargs)

    @patch('ledger.management.commands.run_agent.AgentClient')
    def test_handle_order_paid_trust_lookup(self, MockClient):
        """ORDER_PAID with trust metadata creates TrustScoreLookup and delivers score."""
        import asyncio
        from croo import Order, DeliverOrderResult, Delivery

        # Seed some data for the target agent
        verify_and_log_payment('ord_seed_t1', 'buyer_x', '50', 'target_agent_for_test')
        verify_and_log_payment('ord_seed_t2', 'buyer_y', '50', 'target_agent_for_test')

        mock_client = AsyncMock()

        # Use a MagicMock for order since the real Order dataclass has no 'metadata' field —
        # the worker reads it via getattr(order, 'metadata', ''), so a MagicMock works fine.
        mock_order = MagicMock()
        mock_order.order_id = 'ord_trust_1'
        mock_order.buyer_user_id = 'requester_buyer'
        mock_order.requester_agent_id = 'req_agent'
        mock_order.provider_agent_id = 'prov_agent'
        mock_order.price = '0.050000'
        mock_order.negotiation_id = 'neg_trust'
        mock_order.service_id = 'svc_trust'
        mock_order.metadata = 'trust:target_agent_for_test'

        mock_client.get_order = AsyncMock(return_value=mock_order)
        from croo import Order, DeliverOrderResult, Delivery
        mock_client.deliver_order = AsyncMock(return_value=DeliverOrderResult(
            order=Order(order_id='ord_trust_1'),
            delivery=Delivery(),
            tx_hash='0xtrustdelivery',
        ))

        cmd = self._make_command()
        event = self._make_event(order_id='ord_trust_1')

        asyncio.run(cmd.handle_order_paid(mock_client, event))

        # TrustScoreLookup record should be created
        lookups = TrustScoreLookup.objects.filter(
            target_agent_id='target_agent_for_test',
            order_id='ord_trust_1',
        )
        self.assertTrue(lookups.exists(), "TrustScoreLookup record was not created")
        lookup = lookups.first()
        self.assertIsInstance(lookup.trust_score, int)
        self.assertGreaterEqual(lookup.trust_score, 0)
        self.assertLessEqual(lookup.trust_score, 100)

        # deliver_order should have been called with the trust report text
        mock_client.deliver_order.assert_called_once()
        call_args = mock_client.deliver_order.call_args
        deliver_text = call_args[0][1].deliverable_text
        self.assertIn('TRUST SCORE REPORT', deliver_text)
        self.assertIn('target_agent_for_test', deliver_text)

