import asyncio
import os
from decouple import Config as DecoupleConfig, RepositoryEnv
from croo import Config, AgentClient, NegotiateOrderRequest
import json

env = DecoupleConfig(RepositoryEnv('croo_backend/.env'))

async def main():
    client = AgentClient(Config(base_url='https://api.croo.network', ws_url='wss://api.croo.network/ws'), env('CROO_ORCHESTRATOR_SDK_KEY'))
    service_id = env('CROO_SERVICE_ID_TRUST')
    print(f"Negotiating for service {service_id}")
    try:
        req = NegotiateOrderRequest(
            service_id=service_id,
            requirements='{"test":"test"}',
            metadata='{"test":"test"}'
        )
        neg = await client.negotiate_order(req)
        print(f"Negotiation created: {neg.negotiation_id}")
    except Exception as e:
        print(f"Error during negotiation: {e}")

if __name__ == "__main__":
    asyncio.run(main())
