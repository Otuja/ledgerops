import asyncio
import json
from decouple import config as env
from croo import AgentClient, Config, ListOptions, NegotiateOrderRequest

async def buy_service(client, buyer_name, service_name, service_id, metadata_dict):
    print(f"\n[{buyer_name}] Purchasing {service_name}...")
    
    req = NegotiateOrderRequest(
        service_id=service_id,
        metadata=json.dumps(metadata_dict),
        requirements="{}"
    )
    
    try:
        neg = await client.negotiate_order(req)
        
        # Wait for provider to accept
        for _ in range(15):
            await asyncio.sleep(2)
            neg_check = await client.get_negotiation(neg.negotiation_id)
            if neg_check.status == 'accepted':
                break
        else:
            print(f"[{buyer_name}] Provider did not accept in time.")
            return
            
        print(f"[{buyer_name}] Accepted! Waiting for order to generate...")
        await asyncio.sleep(6)
        
        # Find order
        orders_res = await client.list_orders(ListOptions(role='buyer', page_size=100))
        items = getattr(orders_res, 'data', getattr(orders_res, 'items', orders_res))
        if not isinstance(items, list): items = getattr(items, 'data', [])
        
        matching_order = next((o for o in items if getattr(o, 'negotiation_id', None) == neg.negotiation_id), None)
        if not matching_order:
            print(f"[{buyer_name}] Could not find order for negotiation.")
            return
            
        order_id = matching_order.order_id
        
        # Wait for created
        for _ in range(15):
            order_check = await client.get_order(order_id)
            if getattr(order_check, 'status', '') == 'created':
                break
            await asyncio.sleep(2)
            
        print(f"[{buyer_name}] Paying order {order_id[:8]} on Base...")
        await client.pay_order(order_id)
        print(f"[{buyer_name}] ✅ Paid successfully!")
        
    except Exception as e:
        print(f"[{buyer_name}] ❌ Payment failed: {e}")

async def main():
    cfg = Config(base_url='https://api.croo.network', ws_url='wss://api.croo.network/ws')
    
    # 2 Distinct Buyer Agents
    agent1 = AgentClient(cfg, env('CROO_ORCHESTRATOR_SDK_KEY'))
    agent2 = AgentClient(cfg, env('CROO_SECONDARY_BUYER_SDK_KEY'))
    
    print("=== STARTING MASS LEDGEROPS DEMO ===")
    
    tasks = []
    
    # Orchestrator buys Transaction Logging, Analytics, and Receipt Verification
    tasks.append(buy_service(
        agent1, "Orchestrator", 
        "Automated Transaction Logging", env('CROO_SERVICE_ID_DEFAULT'), {"service": "log"}
    ))
    tasks.append(buy_service(
        agent1, "Orchestrator", 
        "Analytics Report", env('CROO_SERVICE_ID_REPORT'), {"service": "report"}
    ))
    tasks.append(buy_service(
        agent1, "Orchestrator", 
        "Receipt Verification", env('CROO_SERVICE_ID_VERIFY'), {"service": "verify"}
    ))
    
    # Secondary Buyer buys Tax Export, Balance Check, and Trust Score (targeting LedgerOps)
    tasks.append(buy_service(
        agent2, "Secondary Buyer", 
        "Tax CSV Export", env('CROO_SERVICE_ID_EXPORT'), {"service": "export"}
    ))
    tasks.append(buy_service(
        agent2, "Secondary Buyer", 
        "Wallet Balance", env('CROO_SERVICE_ID_BALANCE'), {"service": "balance"}
    ))
    tasks.append(buy_service(
        agent2, "Secondary Buyer", 
        "Trust Score Lookup", env('CROO_SERVICE_ID_TRUST'), {"service": "trust", "target": env('LEDGEROPS_AGENT_ID')}
    ))

    # Run everything in parallel!
    await asyncio.gather(*tasks)
    
    await agent1.close()
    await agent2.close()
    
    print("\n=== DEMO COMPLETE! All 6 LedgerOps services executed across 2 Agents ===")

if __name__ == "__main__":
    asyncio.run(main())
