import asyncio
import json
from croo import AgentClient, Config, ListOptions
from decouple import config as env

async def test_service(buyer_client, service_id, service_name, metadata_dict=None):
    print(f"\n[+] Purchasing: {service_name}")
    metadata_str = json.dumps(metadata_dict) if metadata_dict else ""
    
    from croo import NegotiateOrderRequest
    req = NegotiateOrderRequest(
        service_id=service_id,
        metadata=metadata_str,
        requirements="{}"
    )
    neg = await buyer_client.negotiate_order(req)
    print(f"    Negotiation created... Waiting for LedgerOps to accept...")
    
    # Wait for provider to accept
    for _ in range(15):
        await asyncio.sleep(2)
        neg_check = await buyer_client.get_negotiation(neg.negotiation_id)
        if neg_check.status == 'accepted':
            break
    else:
        print(f"    [!] Provider did not accept in time.")
        return
        
    print("    LedgerOps accepted! Waiting for blockchain to generate order...")
    await asyncio.sleep(5)
        
    # Find the order ID
    orders_res = await buyer_client.list_orders(ListOptions(role='buyer', page_size=100))
    items = getattr(orders_res, 'data', getattr(orders_res, 'items', orders_res))
    if not isinstance(items, list): items = getattr(items, 'data', [])
    
    matching_order = next((o for o in items if getattr(o, 'negotiation_id', None) == neg.negotiation_id), None)
    if not matching_order:
        print("    [!] Could not find resulting order.")
        return
        
    order_id = matching_order.order_id
    
    # Wait for 'created' status
    for _ in range(15):
        order_check = await buyer_client.get_order(order_id)
        if getattr(order_check, 'status', '') == 'created':
            break
        await asyncio.sleep(2)
    
    # Pay
    print(f"    Order {order_id} ready! Paying on Base blockchain...")
    try:
        pay_res = await buyer_client.pay_order(order_id)
        print(f"    ✅ Paid successfully. Tx Hash: {getattr(pay_res, 'tx_hash', 'unknown')}")
        
        # Wait a few seconds for delivery
        print(f"    Waiting for LedgerOps to deliver the final result...")
        await asyncio.sleep(15)
        print(f"    Done!")
    except Exception as e:
        print(f"    [ERROR] Failed to test {service_name}: {e}")

async def run_tests():
    cfg = Config(base_url='https://api.croo.network', ws_url='wss://api.croo.network/ws')
    buyer_client = AgentClient(cfg, env('CROO_REQUESTER_SDK_KEY'))
    
    ledgerops_agent_id = env('LEDGEROPS_AGENT_ID')
    
    print("=== LEDGEROPS DEMO SCRIPT ===")
    print("This script will execute two automated on-chain purchases.")
    
    # 1. Automated Transaction Logging
    # We log a transaction which builds up LedgerOps's own trust score!
    await test_service(
        buyer_client, 
        env('CROO_SERVICE_ID_DEFAULT'), 
        "Automated Transaction Logging",
        metadata_dict={"service": "log"}
    )
    
    # 2. Trust Score Lookup on LedgerOps itself!
    print(f"\n[INFO] We just completed a transaction, so LedgerOps's Trust Score should reflect it!")
    await test_service(
        buyer_client, 
        env('CROO_SERVICE_ID_TRUST'), 
        "Trust Score Lookup",
        metadata_dict={"service": "trust", "target": ledgerops_agent_id}
    )

    print("\n=== Demo Completed ===")
    print("Check your LedgerOps server logs to see the deliveries!")
    await buyer_client.close()

if __name__ == "__main__":
    asyncio.run(run_tests())
