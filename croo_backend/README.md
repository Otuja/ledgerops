# CROO Agent Protocol - Backend & Agent Worker

This is the Python/Django backend for the Automated Transaction Logging Agent.

## Architecture
- **Django**: Serves the REST API for the frontend dashboard to display transaction logs and aggregate balances.
- **SQLite / PostgreSQL**: Stores the `VirtualWallet` state and immutable `TransactionAuditLog` receipts.
- **Agent Worker**: A custom Django management command (`run_agent.py`) that uses `croo-sdk` to listen to WebSocket events and automatically update the database.

## Running the Web API
To serve the REST API for the frontend:
```bash
python manage.py runserver 8000
```

## Running the Agent Worker
To start the background agent that connects to the CROO network:
```bash
python manage.py run_agent
```

Ensure you have your environment variables set (`CROO_SDK_KEY`, `CROO_API_URL`, etc.) before running the agent worker.

## Core Files
- `ledger/models.py`: Contains the `VirtualWallet` and `TransactionAuditLog` models, plus the `verify_and_log_payment` transaction helper.
- `ledger/management/commands/run_agent.py`: The continuous background asyncio worker for the CROO Protocol.
