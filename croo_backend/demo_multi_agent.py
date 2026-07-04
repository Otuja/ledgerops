import asyncio
import json
import random
from decouple import config as env
from croo import AgentClient, Config, ListOptions, NegotiateOrderRequest

async def buy_service(client, name, service_id, provider_id, metadata):
    print(f"[{name}] Purchasing service {service_id[:8]} from {provider_id[:8]}...")
    
    req = NegotiateOrderRequest(
        service_id=service_id,
        metadata=json.dumps(metadata),
        requirements="{}"
    )
    neg = await client.negotiate_order(req)
    
    # Wait for provider to accept
    await asyncio.sleep(4)
    neg_check = await client.get_negotiation(neg.negotiation_id)
    if neg_check.status != 'accepted':
        print(f"[{name}] Provider did not accept. Status: {neg_check.status}")
        return
        
    print(f"[{name}] Negotiation accepted! Waiting for order to generate...")
    await asyncio.sleep(5)
    
    # Find order
    orders_res = await client.list_orders(ListOptions(role='buyer', page_size=100))
    items = getattr(orders_res, 'data', getattr(orders_res, 'items', orders_res))
    if not isinstance(items, list): items = getattr(items, 'data', [])
    
    matching_order = next((o for o in items if getattr(o, 'negotiation_id', None) == neg.negotiation_id), None)
    if not matching_order:
        print(f"[{name}] Could not find order for negotiation.")
        return
        
    order_id = matching_order.order_id
    
    # Wait for created
    for _ in range(5):
        order_check = await client.get_order(order_id)
        if getattr(order_check, 'status', '') == 'created':
            break
        await asyncio.sleep(2)
        
    print(f"[{name}] Paying order {order_id[:8]}...")
    try:
        await client.pay_order(order_id)
        print(f"[{name}] Paid successfully!")
    except Exception as e:
        print(f"[{name}] Payment failed: {e}")


async def main():
    cfg = Config(base_url='https://api.croo.network', ws_url='wss://api.croo.network/ws')
    
    buyer1 = AgentClient(cfg, env('CROO_SECONDARY_BUYER_SDK_KEY'))
    buyer2 = AgentClient(cfg, env('CROO_ORCHESTRATOR_SDK_KEY'))
    
    provider_id = env('LEDGEROPS_AGENT_ID')
    
    # We will buy Analytics and Tax Exports rapidly
    services = [
        (env('CROO_SERVICE_ID_EXPORT'), {"tax_export": "demo"}),
        (env('CROO_SERVICE_ID_ANALYTICS'), {"analytics": "demo"})
    ]
    
    print("=== Starting Real Multi-Agent Demo Activity ===")
    
    # Run 4 parallel purchases (2 from each agent)
    tasks = []
    
    for i in range(2):
        svc_id, meta = random.choice(services)
        tasks.append(buy_service(buyer1, f"Secondary Buyer {i+1}", svc_id, provider_id, meta))
        
        svc_id2, meta2 = random.choice(services)
        tasks.append(buy_service(buyer2, f"Orchestrator {i+1}", svc_id2, provider_id, meta2))
        
    await asyncio.gather(*tasks)
    print("\n=== Demo Script Complete ===")

if __name__ == "__main__":
    asyncio.run(main())
