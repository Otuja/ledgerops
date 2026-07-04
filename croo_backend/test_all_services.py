import asyncio
import os
import json
from decouple import config
from croo import AgentClient, Config, NegotiateOrderRequest, DeliverableType

async def buy_all_services():
    print("=== Testing All LedgerOps Services ===")
    
    croo_cfg = Config(
        base_url=config('CROO_API_URL', default='https://api.croo.network'),
        ws_url=config('CROO_WS_URL', default='wss://api.croo.network/ws'),
    )
    
    # We will buy services AS the Secondary Buyer agent
    buyer_key = config('CROO_SECONDARY_BUYER_SDK_KEY')
    buyer_id = config('SECONDARY_BUYER_AGENT_ID')
    
    # Target Provider is LedgerOps
    provider_id = config('LEDGEROPS_AGENT_ID')
    
    buyer_client = AgentClient(croo_cfg, buyer_key)
    
    services = {
        'Automated Transaction Logging': (config('CROO_SERVICE_ID_DEFAULT'), 'default'),
        'Wallet Balance Retrieval': (config('CROO_SERVICE_ID_BALANCE'), 'balance'),
        'Receipt Verification': (config('CROO_SERVICE_ID_VERIFY'), 'verify'),
        'Transaction Analytics Report': (config('CROO_SERVICE_ID_REPORT'), 'report'),
        'Tax CSV Export': (config('CROO_SERVICE_ID_EXPORT'), 'export'),
    }
    
    for name, (svc_id, meta_key) in services.items():
        if not svc_id:
            print(f"Skipping {name} (no service ID configured)")
            continue
            
        print(f"\n[+] Purchasing: {name} ({svc_id[:8]}...)")
        try:
            # Metadata determines how run_agent.py routes the request
            metadata = {meta_key: "test_run"}
            
            # Step 1: Negotiate
            req = NegotiateOrderRequest(
                service_id=svc_id,
                metadata=json.dumps(metadata),
                requirements="{}"
            )
            neg = await buyer_client.negotiate_order(req)
            print(f"    Negotiation ID: {neg.negotiation_id} (Waiting for provider to accept...)")
            
            # Wait for provider (Render backend) to automatically accept
            await asyncio.sleep(8)
            
            # Check negotiation status
            neg_check = await buyer_client.get_negotiation(neg.negotiation_id)
            if neg_check.status != 'accepted':
                print(f"    [!] Provider did not accept in time. Current status: {neg_check.status}")
                continue
                
            # Find the order ID by querying list_orders
            from croo import ListOptions
            orders_res = await buyer_client.list_orders(ListOptions(role='buyer'))
            items = getattr(orders_res, 'data', getattr(orders_res, 'items', orders_res))
            if not isinstance(items, list): items = getattr(items, 'data', [])
            
            matching_order = next((o for o in items if getattr(o, 'negotiation_id', None) == neg.negotiation_id), None)
            if not matching_order:
                print(f"    [!] Could not find matching order for negotiation {neg.negotiation_id}")
                continue
                
            order_id = matching_order.order_id
            
            # Wait for order to officially be in 'created' status on the network
            for _ in range(15):
                order_check = await buyer_client.get_order(order_id)
                if getattr(order_check, 'status', '') == 'created':
                    break
                await asyncio.sleep(2)
            else:
                print(f"    [!] Order {order_id} never reached 'created' status. Current: {getattr(order_check, 'status', 'unknown')}")
                continue
            
            # Step 2: Pay
            print(f"    Provider accepted! Order ID: {order_id}. Paying 0.2 USDC...")
            pay_res = await buyer_client.pay_order(order_id)
            print(f"    Paid successfully. Tx Hash: {pay_res.tx_hash}")
            
            # Wait for delivery
            print(f"    Waiting for delivery...")
            await asyncio.sleep(10)
            
            order_check = await buyer_client.get_order(order_id)
            if order_check.status == 'completed':
                delivery = await buyer_client.get_delivery(order_id)
                print(f"    [SUCCESS] Delivered! Payload: {delivery.deliverable_text}")
            else:
                print(f"    [!] Order not completed yet. Status: {order_check.status}")
                
        except Exception as e:
            print(f"    [ERROR] Failed to test {name}: {e}")

    await buyer_client.close()
    print("\n=== All Tests Completed ===")

if __name__ == "__main__":
    asyncio.run(buy_all_services())
