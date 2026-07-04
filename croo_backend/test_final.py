import asyncio
import json
from decimal import Decimal
from croo import AgentClient, Config, ListOptions
from decouple import config as env

async def test_service(buyer_client, service_id, provider_agent_id, service_name, metadata_dict=None):
    print(f"\n[+] Purchasing: {service_name} ({service_id[:8]}...)")
    metadata_str = json.dumps(metadata_dict) if metadata_dict else ""
    
    from croo import NegotiateOrderRequest
    req = NegotiateOrderRequest(
        service_id=service_id,
        metadata=metadata_str,
        requirements="{}"
    )
    neg = await buyer_client.negotiate_order(req)
    print(f"    Negotiation ID: {neg.negotiation_id} (Waiting for provider to accept...)")
    
    # Wait for provider to accept
    for _ in range(15):
        await asyncio.sleep(2)
        neg_check = await buyer_client.get_negotiation(neg.negotiation_id)
        if neg_check.status == 'accepted':
            break
    else:
        print(f"    [!] Provider did not accept in time. Current status: {neg_check.status}")
        return
        
    print("    Provider accepted! Waiting for blockchain to generate order...")
    await asyncio.sleep(5)
        
    # Find the order ID
    orders_res = await buyer_client.list_orders(ListOptions(role='buyer', page_size=100))
    items = getattr(orders_res, 'data', getattr(orders_res, 'items', orders_res))
    if not isinstance(items, list): items = getattr(items, 'data', [])
    
    matching_order = next((o for o in items if getattr(o, 'negotiation_id', None) == neg.negotiation_id), None)
    if not matching_order:
        print("    [!] Could not find resulting order in list_orders.")
        return
        
    order_id = matching_order.order_id
    
    # Wait for 'created' status
    for _ in range(15):
        order_check = await buyer_client.get_order(order_id)
        if getattr(order_check, 'status', '') == 'created':
            break
        await asyncio.sleep(2)
    else:
        print(f"    [!] Order {order_id} never reached 'created' status.")
        return
    
    # 2. Pay
    print(f"    Provider accepted! Order ID: {order_id}. Paying 0.2 USDC...")
    try:
        pay_res = await buyer_client.pay_order(order_id)
        print(f"    Paid successfully. Tx Hash: {getattr(pay_res, 'tx_hash', 'unknown')}")
    except Exception as e:
        print(f"    [ERROR] Failed to test {service_name}: {e}")

async def run_tests():
    cfg = Config(base_url='https://api.croo.network', ws_url='wss://api.croo.network/ws')
    buyer_client = AgentClient(cfg, env('CROO_SECONDARY_BUYER_SDK_KEY'))
    provider_agent_id = env('LEDGEROPS_AGENT_ID')
    
    print("=== Testing Remaining LedgerOps Services ===")

    # 1. Tax CSV Export (Already tested successfully)
    # await test_service(
    #     buyer_client, 
    #     env('CROO_SERVICE_ID_EXPORT'), 
    #     provider_agent_id, 
    #     "Tax CSV Export"
    # )
    
    # 2. Trust Score Lookup
    # Target our own test agent so we can see its score based on the transactions it just did!
    target_id = env('SECONDARY_BUYER_AGENT_ID')
    await test_service(
        buyer_client, 
        env('CROO_SERVICE_ID_TRUST'), 
        provider_agent_id, 
        "Trust Score Lookup",
        metadata_dict={"trust_lookup": "test_run", "target": target_id}
    )

    print("\n=== Tests Completed ===")

if __name__ == "__main__":
    asyncio.run(run_tests())
