import asyncio
import os
from decouple import Config as DecoupleConfig, RepositoryEnv
from croo import Config, AgentClient

env = DecoupleConfig(RepositoryEnv('croo_backend/.env'))

async def check():
    keys = {
        'LedgerOps': env('CROO_SDK_KEY', default=''),
        'Orchestrator': env('CROO_ORCHESTRATOR_SDK_KEY', default=''),
        'SecondaryBuyer': env('CROO_SECONDARY_BUYER_SDK_KEY', default='')
    }
    
    clients = {name: AgentClient(Config(base_url='https://api.croo.network', ws_url='wss://api.croo.network/ws'), key) for name, key in keys.items() if key}

    for name, client in clients.items():
        try:
            bal = await client.get_wallet_balance()
            print(f"{name}: {bal} USDC")
        except Exception as e:
            print(f"{name} Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
