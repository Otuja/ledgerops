import asyncio
from croo import AgentClient, Config, ListOptions

async def fetch():
    cfg = Config(base_url='https://api.croo.network', ws_url='wss://api.croo.network/ws')
    c = AgentClient(cfg, 'croo_sk_94407e6d65d9e7e2e912359dcfb70931')
    
    all_orders = []
    page = 1
    while True:
        opts = ListOptions(role='provider', page=page, page_size=100)
        res = await c.list_orders(opts)
        items = getattr(res, 'data', None)
        if items is None:
            items = getattr(res, 'items', res)
            if not isinstance(items, list): items = items.data
        all_orders.extend(items)
        if len(items) < 100: break
        page += 1
        
    print(f"Total orders: {len(all_orders)}")
    for o in all_orders:
        if getattr(o, 'status', '') == 'completed':
            price = getattr(o, 'price', 'N/A')
            print(f"Order {o.order_id}, Price: {price}")

if __name__ == "__main__":
    asyncio.run(fetch())
