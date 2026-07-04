import asyncio
from croo import AgentClient, Config, ListOptions

async def main():
    cfg = Config(base_url='https://api.croo.network', ws_url='wss://api.croo.network/ws')
    client = AgentClient(cfg, 'croo_sk_94407e6d65d9e7e2e912359dcfb70931')
    orders = await client.list_orders(ListOptions(role='provider'))
    print(f'Total provider orders from CROO: {len(orders)}')
    statuses = {}
    for o in orders:
        statuses[o.status] = statuses.get(o.status, 0) + 1
    print('Status breakdown:', statuses)
    print()
    print('All orders (id, status, price, negotiation_id):')
    for o in orders:
        neg_id = getattr(o, 'negotiation_id', '') or ''
        svc_id = getattr(o, 'service_id', '') or ''
        price = getattr(o, 'price', 0) or 0
        buyer = getattr(o, 'requester_agent_id', '') or getattr(o, 'buyer_user_id', '') or '?'
        print(f'  [{o.status}] {o.order_id}  price={price}  buyer={str(buyer)[:12]}  svc={str(svc_id)[:8]}  neg={str(neg_id)[:8]}')

asyncio.run(main())
