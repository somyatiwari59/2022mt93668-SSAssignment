Transaction Service (Banking Microservice)

FastAPI service that records deposits, withdrawals, and transfers with business rules (no overdraft on BASIC, daily debit limit, frozen status checks, idempotent transfers).
Backed by PostgreSQL via SQLAlchemy.

Features

Deposit / Withdraw

Transfer (double-entry: DEBIT source + CREDIT destination)

Daily debit limit (default ₹200,000) with atomic ledger updates

Idempotency for /transfer via Idempotency-Key header

Health check

Read APIs for daily ledger and same-day transactions (IST-aware)

Mock Account API for local dev (thread-safe with RLock)

API (current)
Method	Path
GET	/health
POST	/deposit
POST	/withdraw
POST	/transfer (requires Idempotency-Key header)
GET	/accounts/{account_id}/daily-ledger
GET	/accounts/{account_id}/daily-ledger/transactions?date=&tz=&limit=&offset=&order=

Notes

daily-ledger returns debits-only summary (used for limit).

daily-ledger/transactions returns all transactions (debits + credits) for that day, with totals.

Timezone defaults to Asia/Kolkata for day windows.

Data Model (service-owned)
transactions

txn_id (UUID, PK)

account_id (UUID)

amount (NUMERIC)

txn_type (DEBIT | CREDIT)

counterparty (TEXT, nullable)

reference (TEXT, nullable)

created_at (TIMESTAMPTZ, default now)

daily_transfer_ledger (debits aggregation for daily limit)

account_id (UUID, PK part)

yyyymmdd (DATE, PK part)

debited (NUMERIC)

idempotency_records

key (TEXT, PK) — Idempotency-Key

response (JSON)

created_at (TIMESTAMPTZ)

Requirements

Python 3.9+ (working now with typing.Optional, not | None)

PostgreSQL (local on 5432 or hosted)

macOS: Postgres.app is fine (no Docker needed)

Environment

Create .env in project root:

# PostgreSQL
DATABASE_URL=postgresql+psycopg://postgres@localhost:5432/txdb

# Account Service integration
# Use "mock" for local dev OR set a base URL like http://localhost:8082
ACCOUNT_API=mock
ACCOUNT_API_TIMEOUT=1.0

# Behavior
DAILY_LIMIT=200000
HIGH_VALUE_THRESHOLD=50000

# Server (optional)
SERVICE_PORT=8083


.env is loaded by app/db/session.py (via python-dotenv).

Install & Run

From project root:

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
# minimal set if you don’t have a file:
# pip install fastapi uvicorn sqlalchemy "psycopg[binary]" python-dotenv pydantic tenacity


Create tables:

python create_db.py


Start API:

uvicorn app.main:app --reload --port 8083
# Swagger: http://localhost:8083/docs

Quick Smoke Tests

Health:

curl -s http://localhost:8083/health


Deposit:

curl -s -X POST http://localhost:8083/deposit \
  -H 'Content-Type: application/json' \
  -d '{"account_id":"11111111-1111-1111-1111-111111111111","amount":1500,"reference":"seed"}'


Withdraw (checks BASIC no-overdraft + daily limit):

curl -s -X POST http://localhost:8083/withdraw \
  -H 'Content-Type: application/json' \
  -d '{"account_id":"11111111-1111-1111-1111-111111111111","amount":500,"reference":"atm"}'


Transfer (idempotent):

curl -s -X POST http://localhost:8083/transfer \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demo-1' \
  -d '{"source_account_id":"11111111-1111-1111-1111-111111111111","dest_account_id":"22222222-2222-2222-2222-222222222222","amount":1000,"reference":"test"}'


Daily ledger (debits summary):

curl -s "http://localhost:8083/accounts/11111111-1111-1111-1111-111111111111/daily-ledger"


Daily ledger + transactions (IST by default):

curl -s "http://localhost:8083/accounts/11111111-1111-1111-1111-111111111111/daily-ledger/transactions?date=2025-11-09"

Project Structure
transaction-service/
├─ app/
│  ├─ api/
│  │  ├─ health.py
│  │  ├─ money.py          # deposit/withdraw
│  │  ├─ transfer.py       # transfer + idempotency
│  │  └─ ledger.py         # summaries + daily transactions
│  ├─ db/
│  │  └─ session.py
│  ├─ models/
│  │  ├─ transaction.py
│  │  ├─ daily_ledger.py
│  │  └─ idempotency.py
│  ├─ services/
│  │  ├─ account_client.py # mock + real client (RLock for mock)
│  │  └─ ledger.py         # atomic ledger helpers
│  └─ main.py
├─ create_db.py
├─ requirements.txt
├─ .env            # not committed
├─ .gitignore
└─ README.md

Notes / Decisions

Daily limit applies to debits only (withdraw + transfer-out).

Credits (deposit + transfer-in) are visible in /daily-ledger/transactions and the transactions table, but don’t affect the daily limit.

Mock Account API uses RLock to avoid deadlock when nested get/update run in the same thread.

Real Account API uses ACCOUNT_API base URL; tune ACCOUNT_API_TIMEOUT/retries as needed.

Next (CI/CD & Deploy)

Dockerize service

Push image to registry

GitHub Actions: lint, test, build, push

Minikube manifests (Deployment, Service, ConfigMap/Secret)

Basic metrics/logging

License

Educational / internal use.