# CROO Credit Bureau — Independent Agent Trust Infrastructure

Built for the **CROO Agent Protocol Hackathon** (DeFi / On-chain Ops Agents track + Data & Verification Agents).

> **"We built the credit bureau for the agent economy — independent, on-chain-verifiable trust scores so any agent can check a counterparty’s track record before paying them, the same anti-sybil signals CROO itself cares about, exposed as a paid service any agent can call."**

LedgerOps is an AI-to-AI service agent on the CROO network. Other agents hire it to:
- **Check trust scores** on any CROO agent before hiring them (completion rate, dispute rate, buyer diversity, sybil detection)
- Log and verify on-chain transactions into a tamper-evident audit ledger
- Check virtual wallet balances
- Verify payment receipts
- Generate analytics reports
- Export tax-ready CSV files

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    CROO Network                         │
│   (Negotiation → Order → Payment → Delivery on-chain)  │
└────────────────────────┬────────────────────────────────┘
                         │ WebSocket events
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Django Background Worker                   │
│         python manage.py run_agent                      │
│                                                         │
│  NEGOTIATION_CREATED → auto-accept → NegotiationLog     │
│  ORDER_PAID          → dispatch service → deliver        │
│  ORDER_COMPLETED/    → update audit log status          │
│  REJECTED/EXPIRED                                       │
└──────────────┬──────────────────────────────────────────┘
               │ Django ORM (SQLite / PostgreSQL)
               ▼
┌─────────────────────────────────────────────────────────┐
│                   Database Models                       │
│   TransactionAuditLog  VirtualWallet  NegotiationLog   │
└──────────────┬──────────────────────────────────────────┘
               │ Django REST Framework
               ▼
┌─────────────────────────────────────────────────────────┐
│              REST API  (port 8000)                      │
│   python manage.py runserver                            │
└──────────────┬──────────────────────────────────────────┘
               │ HTTP
               ▼
┌─────────────────────────────────────────────────────────┐
│           React Dashboard  (port 5173)                  │
│           npm run dev                                   │
└─────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend / Worker | Python 3.10+, Django, Django REST Framework |
| CROO Integration | `croo-sdk` (AgentClient, EventStream) |
| Database | SQLite (local dev) / PostgreSQL (production) |
| Frontend | React, Vite, Tailwind CSS |
| Config | `python-decouple` (`.env` file) |

---

## 1. Quick Start (Local Development)

### Prerequisites

- Python 3.10+
- Node.js & npm
- Git

### Clone & Configure

```bash
git clone <repo-url>
cd hackerthon
```

Copy and fill in the environment file:

```bash
cp croo_backend/.env.example croo_backend/.env  # if it exists, else edit .env directly
```

Required values in `croo_backend/.env`:

```ini
# Django
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# CORS (React dev server)
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Provider agent credentials
CROO_SDK_KEY=croo_sk_<your_provider_key>
CROO_API_URL=https://api.croo.network
CROO_WS_URL=wss://api.croo.network/ws
BASE_RPC_URL=https://mainnet.base.org

# Requester agent (for testing — second registered agent)
CROO_REQUESTER_SDK_KEY=croo_sk_<your_requester_key>

# Service IDs of this provider on the Croo network (one per service)
CROO_SERVICE_ID_DEFAULT=<your_default_service_id>
CROO_SERVICE_ID_BALANCE=<your_balance_service_id>
CROO_SERVICE_ID_VERIFY=<your_verify_service_id>
CROO_SERVICE_ID_REPORT=<your_report_service_id>
CROO_SERVICE_ID_EXPORT=<your_export_service_id>
```

### Backend Setup

```bash
cd croo_backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
```

### Run All Three Processes

Open **three separate terminals**, all from the repo root.

**Terminal 1 — Django API server:**
```bash
cd croo_backend
source venv/Scripts/activate   # Windows
python manage.py runserver 8000
```

**Terminal 2 — CROO background worker:**
```bash
cd croo_backend
source venv/Scripts/activate   # Windows
python manage.py run_agent
```

**Terminal 3 — React dashboard:**
```bash
cd croo_dashboard
npm install
npm run dev
```

Dashboard opens at `http://localhost:5173` · API at `http://localhost:8000/api/`

---

## 2. Services Offered

The agent auto-accepts all negotiations. The service delivered depends on the `metadata` field in the order:

### Counterparty Due-Diligence (check someone else)

| `metadata` keyword | Service | What is returned |
|---|---|---|
| `trust:<agent_id>` | **Trust Score Lookup** | Full trust report: score 0-100, completion rate, dispute rate, buyer diversity, flags, plain-English summary |

### Self-Service Tools (check your own status)

| `metadata` keyword | Service | What is returned |
|---|---|---|
| *(empty)* | **Transaction Logging** | Logs payment to audit ledger, credits virtual wallet, returns `TRANSACTION_LOGGED_SUCCESSFULLY` |
| `balance` | **Wallet Balance Check** | Returns the buyer’s current USDC balance across all recorded payments |
| `verify` | **Receipt Verification** | Returns details of the buyer’s most recent verified transaction |
| `report` | **Analytics Report** | Returns total USDC spent and transaction count for the buyer |
| `export` | **Tax CSV Export** | Returns a download link to a CSV of all the buyer’s transactions |

---

## 3. Event Handler Reference

Implemented in [`ledger/management/commands/run_agent.py`](croo_backend/ledger/management/commands/run_agent.py).

### `NEGOTIATION_CREATED`
1. Calls `client.accept_negotiation(negotiation_id)`
2. Writes a `NegotiationLog` record with status `accepted`
3. On failure: writes `NegotiationLog` with status `rejected`

### `ORDER_PAID`
1. Fetches the full `Order` via `client.get_order(order_id)`
2. Inspects `order.metadata` for a service keyword (see table above)
3. Executes the matching service
4. Calls `client.deliver_order(order_id, DeliverOrderRequest(...))`
5. Updates `TransactionAuditLog` with `tx_hash` and `delivered_at` (logging service only)

### `ORDER_COMPLETED`
Updates the `TransactionAuditLog` status to `completed`.

### `ORDER_REJECTED`
Updates the `TransactionAuditLog` status to `rejected`.

### `ORDER_EXPIRED`
Updates the `TransactionAuditLog` status to `expired`.

### `NEGOTIATION_REJECTED` / `NEGOTIATION_EXPIRED`
Updates the `NegotiationLog` status accordingly.

---

## 4. REST API Reference

Base URL: `http://localhost:8000/api/`

### Health

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health/` | Returns `{"status": "ok"}` |

### Transaction Audit Logs

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/logs/` | List all audit logs (newest first) |
| `GET` | `/api/logs/?status=verified` | Filter by status (`verified`, `failed`, `completed`, `rejected`, `expired`) |
| `GET` | `/api/logs/<order_id>/` | Get a single log by order ID |

**Log object:**
```json
{
  "order_id": "ord_abc123",
  "negotiation_id": "neg_xyz",
  "service_id": "0xaee...",
  "buyer_id": "agent_requester",
  "agent_id": "agent_provider",
  "amount_usdc": "100.000000",
  "tx_hash": "0xdeadbeef...",
  "status": "verified",
  "timestamp": "2026-06-16T12:00:00Z",
  "delivered_at": "2026-06-16T12:00:05Z"
}
```

### Wallets

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/wallet/` | Aggregate balance across all agent wallets |
| `GET` | `/api/wallets/` | List all individual agent wallets (ordered by balance desc) |

**Aggregate response:**
```json
{ "balance_usdc": "350.000000", "wallet_count": 2 }
```

### Negotiations

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/negotiations/` | List all negotiation logs |
| `GET` | `/api/negotiations/?status=accepted` | Filter by status |

### Dashboard Stats

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/stats/` | All aggregate stats for the dashboard |

**Response:**
```json
{
  "total_balance": "350.000000",
  "wallet_count": 2,
  "transaction_count": 5,
  "verified_count": 4,
  "pending_count": 0,
  "failed_count": 1,
  "completed_count": 0,
  "negotiation_count": 3,
  "negotiations_accepted": 3,
  "negotiations_pending": 0
}
```

### Tax Export

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/export/<agent_id>/` | Download a CSV of all transactions for `agent_id` |

CSV columns: `Order ID`, `Timestamp`, `Status`, `Amount (USDC)`, `Provider Agent ID`, `Service ID`, `Transaction Hash`

### Trust Score

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/trust-score/<agent_id>/` | Real-time trust report for any CROO agent ID |
| `GET` | `/api/trust-lookups/` | Audit log of all paid Trust Score Lookup orders |

---

## 5. Database Models

### `TransactionAuditLog`
Immutable audit record for every order processed.

| Field | Type | Notes |
|---|---|---|
| `order_id` | CharField (unique) | CROO order ID |
| `negotiation_id` | CharField | Linked negotiation |
| `service_id` | CharField | CROO service ID |
| `buyer_id` | CharField | Requester agent or user ID |
| `agent_id` | CharField | Provider agent ID |
| `amount_usdc` | DecimalField(20,6) | Payment amount |
| `tx_hash` | CharField | On-chain delivery tx hash |
| `status` | CharField | `pending` / `verified` / `completed` / `failed` / `rejected` / `expired` |
| `timestamp` | DateTimeField | Auto-set on creation |
| `delivered_at` | DateTimeField (nullable) | Set when delivery confirmed |

### `VirtualWallet`
One row per agent, tracks cumulative USDC received.

| Field | Type | Notes |
|---|---|---|
| `agent_id` | CharField (unique) | Provider agent ID |
| `balance_usdc` | DecimalField(20,6) | Running total |
| `last_updated` | DateTimeField | Auto-updated |

### `NegotiationLog`
Records every negotiation event from the CROO network.

| Field | Type | Notes |
|---|---|---|
| `negotiation_id` | CharField (unique) | |
| `service_id` | CharField | |
| `requester_agent_id` | CharField | |
| `provider_agent_id` | CharField | |
| `status` | CharField | `pending` / `accepted` / `rejected` / `expired` |
| `fund_amount` | CharField | For fund-transfer services |
| `fund_token` | CharField | ERC-20 token address |
| `metadata` | TextField | |
| `created_at` / `updated_at` | DateTimeField | |

### `TrustScoreLookup`
Audit record for every paid Trust Score Lookup order.

| Field | Type | Notes |
|---|---|---|
| `call_id` | UUIDField (unique) | Auto-generated per lookup |
| `order_id` | CharField | CROO order that triggered this lookup |
| `target_agent_id` | CharField | Agent being looked up |
| `requesting_buyer_id` | CharField | Agent that paid for the lookup |
| `trust_score` | IntegerField | 0–100 computed score |
| `result_json` | TextField | Full result dict as JSON (for auditability) |
| `created_at` | DateTimeField | Auto-set |

---

## 5a. Trust Score Scoring Formula

All metrics are computed from real aggregated data in `TransactionAuditLog` and `NegotiationLog`. No hardcoded scores, no LLM.

```
trust_score = round(100 * (
    0.40 * completion_rate                      # Most important: does the agent deliver?
    + 0.25 * (1 - dispute_rate)                 # Low disputes = trustworthy
    + 0.15 * min(1, unique_buyer_count / 10)    # Diverse buyers show organic demand
    + 0.10 * min(1, account_age_days / 14)      # Age ≥ 14 days = full maturity bonus
    + 0.10 * min(1, 60 / avg_delivery_secs)     # Fast delivery vs 60s SLA target
))
```

Clamped to `[0, 100]`. An agent with no transaction history at all returns `score = 0`.

### Flag thresholds

| Flag | Condition |
|---|---|
| `high_self_trade_concentration` | Single buyer > 50% of total volume (wash-trading risk) |
| `low_buyer_diversity` | Fewer than 3 unique buyers |
| `recent_account` | Account age < 2 days |
| `high_dispute_rate` | Dispute rate > 15% |

---

## 6. Testing

### Automated Tests

Run all tests from the `croo_backend` directory:

```bash
python manage.py test ledger
```

The test suite covers:
- `verify_and_log_payment` model helper (happy path, idempotency, accumulation)
- `NegotiationLog` model
- All REST API endpoints (logs, wallets, negotiations, stats, health)
- Agent worker handlers (`handle_order_paid`, `handle_negotiation_created`, `handle_status_update`) using mocked SDK

### End-to-End Testing with the Requester Agent

[`requester_agent.py`](croo_backend/requester_agent.py) is a standalone buyer agent that drives the full CROO flow against your running provider.

**Available services:**

```bash
# Test the default transaction-logging service
python requester_agent.py

# Test a specific service by name
python requester_agent.py balance       # wallet balance retrieval
python requester_agent.py verify        # receipt verification
python requester_agent.py report        # analytics report
python requester_agent.py export        # tax CSV export

# Trust Score Lookup — self-test (looks up provider's own record)
python requester_agent.py trust

# Trust Score Lookup on a specific target agent ID
python requester_agent.py trust agent_0xabc123
```

**Requirements:** `CROO_SERVICE_ID_TRUST` must be set in `.env` for the trust service.

**What it does, step by step:**

```
STEP 1 — Negotiate
  Sends a NegotiateOrderRequest to the Croo network targeting your service ID.
  The metadata field is set to the service keyword (e.g. "balance") so your
  provider's handle_order_paid handler knows which service to run.

STEP 2 — Wait for acceptance (up to 120s)
  Polls get_negotiation() every 3s until the provider accepts or it times out.

STEP 3 — Pay
  Calls pay_order(order_id). Requires USDC on Base mainnet. In sandbox,
  payment may still trigger ORDER_PAID on the provider even if this step fails.

STEP 4 — Wait for delivery (up to 180s)
  Polls get_order() every 3s until status is COMPLETED, then fetches and
  prints the delivery content.
```

**Example output:**

```
🤖  Croo Requester Agent — testing service: 'balance'
    API: https://api.croo.network

────────────────────────────────────────────────────────────────────────
  STEP 1 — Negotiating  (service='balance', service_id=0xaeE07b...)
────────────────────────────────────────────────────────────────────────
  ✓  Negotiation created: neg_abc123  (status=pending)

────────────────────────────────────────────────────────────────────────
  STEP 2 — Waiting for provider to accept  (timeout=120s)
────────────────────────────────────────────────────────────────────────
  … negotiation status = pending
  … negotiation status = accepted
  ✓  Accepted → order_id=ord_xyz456

────────────────────────────────────────────────────────────────────────
  STEP 3 — Paying order  (order_id=ord_xyz456)
────────────────────────────────────────────────────────────────────────
  ✓  Paid  (tx_hash=0xdeadbeef..., status=paying)

────────────────────────────────────────────────────────────────────────
  STEP 4 — Waiting for delivery  (timeout=180s)
────────────────────────────────────────────────────────────────────────
  … order status = paid
  … order status = completed

────────────────────────────────────────────────────────────────────────
  ✅  DELIVERY RECEIVED
────────────────────────────────────────────────────────────────────────
  delivery_id  : del_789
  type         : text
  status       : accepted
  content      :

    WALLET BALANCE: 350.000000 USDC
```

**Service → metadata keyword mapping:**

| CLI argument | `metadata` sent | Handler path triggered |
|---|---|---|
| `default` | *(empty)* | `verify_and_log_payment` → ledger + wallet credit |
| `balance` | `"balance"` | Queries `VirtualWallet` for buyer's balance |
| `verify` | `"verify"` | Fetches buyer's last `TransactionAuditLog` |
| `report` | `"report"` | Aggregates total USDC + tx count for buyer |
| `export` | `"export"` | Returns download URL: `/api/export/<buyer_id>/` |

---

## 7. Environment Variable Reference

All variables are read from `croo_backend/.env` via `python-decouple`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | ✅ | — | Django secret key |
| `DEBUG` | — | `False` | Enable Django debug mode |
| `ALLOWED_HOSTS` | ✅ | — | Comma-separated allowed hosts |
| `CORS_ALLOWED_ORIGINS` | — | — | Origins allowed to call the API |
| `CROO_SDK_KEY` | ✅ | — | Provider agent SDK key |
| `CROO_API_URL` | — | `https://api.croo.network` | Croo REST API base URL |
| `CROO_WS_URL` | — | `wss://api.croo.network/ws` | Croo WebSocket URL |
| `BASE_RPC_URL` | — | `https://mainnet.base.org` | Base chain RPC for balance checks |
| `CROO_REQUESTER_SDK_KEY` | — | — | Requester agent key (testing only) |
| `CROO_SERVICE_ID_DEFAULT`| — | — | Service ID for default transaction logging |
| `CROO_SERVICE_ID_BALANCE`| — | — | Service ID for wallet balance retrieval |
| `CROO_SERVICE_ID_VERIFY` | — | — | Service ID for receipt verification |
| `CROO_SERVICE_ID_REPORT` | — | — | Service ID for analytics report |
| `CROO_SERVICE_ID_EXPORT` | — | — | Service ID for tax CSV export |
| `CROO_SERVICE_ID_TRUST`  | — | — | Service ID for Trust Score Lookup |
| `DATABASE_URL` | — | SQLite | PostgreSQL connection string for production |

---

## 8. Production Deployment

### Required Environment Variables

```ini
DATABASE_URL=postgres://user:password@host:5432/croo_db
CROO_SDK_KEY=croo_sk_<production_key>
CROO_API_URL=https://api.croo.network
CROO_WS_URL=wss://api.croo.network/ws
DJANGO_SECRET_KEY=<strong-random-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
```

### Procfile (Render / Railway / Heroku)

```procfile
web: gunicorn croo_backend.wsgi --log-file -
worker: python manage.py run_agent
```

Scale `web` and `worker` as independent services on your PaaS.

---

## 9. Hackathon Submission Checklist

- [ ] **Listed on CROO Agent Store** — agent is discoverable by humans and other agents
- [ ] **CAP Integration** — `run_agent` worker handles all event types and settles on-chain
- [x] **Trust Score Lookup** — 6th service live, data-driven, tested against 3 distinct agent histories
- [x] **Dashboard Agent Lookup** — search any agent ID, see real score and flags
- [x] **Open Source License** — MIT License (see below)
- [ ] **Demo Video** — max 5-minute A2A composability + dashboard demo, link here: ___
- [ ] **DoraHacks Submission** — all required fields completed

**Track tags:** DeFi / On-chain Ops Agents (primary) · Data & Verification Agents (secondary)

---

*License: MIT*
