import asyncio
from cross_calls.base_buyer import buy_service
from decouple import config

async def main():
    sdk_key = config('CROO_ORCHESTRATOR_SDK_KEY')
    service_id = config('CROO_SERVICE_ID_TRUST')
    metadata = f'{{"command": "trust", "target": "{config("SECONDARY_BUYER_AGENT_ID")}"}}'
    requirements = '{"task": "Testing trust lookup"}'
    
    print(f"Testing buy_service with metadata: {metadata}")
    try:
        from croo import AgentClient, Config
        from croo.agent_client import NegotiateOrderRequest
        c = AgentClient(Config(base_url='https://api.croo.network', rpc_url='https://mainnet.base.org'), sdk_key)
        
        print("1. Calling negotiate_order...")
        req = NegotiateOrderRequest(service_id=service_id, requirements=requirements, metadata=metadata)
        neg = await c.negotiate_order(req)
        print("Negotiation created:", neg.negotiation_id)
        
        print("2. Calling get_negotiation...")
        import time
        time.sleep(2)
        n = await c.get_negotiation(neg.negotiation_id)
        print("Got negotiation status:", n.status)
        
        if n.status == 'accepted':
            print("3. Calling pay_order...")
            await c.pay_order(n.order.order_id)
    except Exception as e:
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())
