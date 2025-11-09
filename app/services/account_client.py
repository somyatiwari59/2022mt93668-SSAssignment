import os, uuid, threading
from typing import Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

ACCOUNT_API = os.getenv("ACCOUNT_API", "mock").strip().lower()
TIMEOUT = float(os.getenv("ACCOUNT_API_TIMEOUT", "2.0"))

class AccountError(RuntimeError): ...
class AccountConflict(RuntimeError): ...

# ---- DEV MOCK (in-process) ----
# BASIC ACTIVE with evolving balances per account_id
_MOCK_LOCK = threading.RLock()
_MOCK_ACCOUNTS = {}  # {uuid: {"type": "BASIC", "status": "ACTIVE", "balance": float}}

def _mock_get_or_create(account_id: uuid.UUID):
    with _MOCK_LOCK:
        if account_id not in _MOCK_ACCOUNTS:
            _MOCK_ACCOUNTS[account_id] = {
                "account_id": str(account_id),
                "type": "BASIC",
                "status": "ACTIVE",
                "balance": 500_000.00,
            }
        return _MOCK_ACCOUNTS[account_id]

def _mock_get_account(account_id: uuid.UUID):
    return _mock_get_or_create(account_id).copy()

def _mock_update_amount(account_id: uuid.UUID, delta: float):
    with _MOCK_LOCK:
        acc = _mock_get_or_create(account_id)
        acc["balance"] = float(acc["balance"] + delta)
        return {"ok": True, "balance": acc["balance"]}

# ---- HTTP helpers ----
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.2, min=0.2, max=1.5),
       retry=retry_if_exception_type(httpx.HTTPError))
def _get(url: str):
    with httpx.Client(timeout=TIMEOUT) as c:
        r = c.get(url)
        r.raise_for_status()
        return r.json()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.2, min=0.2, max=1.5),
       retry=retry_if_exception_type(httpx.HTTPError))
def _post(url: str, json: dict):
    with httpx.Client(timeout=TIMEOUT) as c:
        r = c.post(url, json=json)
        if r.status_code == 409:
            raise AccountConflict(r.text or "Account conflict")
        r.raise_for_status()
        return r.json() if r.content else {}

# ---- Public API ----
def get_account(account_id: uuid.UUID) -> dict:
    if ACCOUNT_API == "mock":
        return _mock_get_account(account_id)
    data = _get(f"{ACCOUNT_API}/accounts/{account_id}")
    # normalize keys in case your real API names differ
    return {
        "account_id": str(data["account_id"]),
        "type": data["type"] if "type" in data else data.get("account_type"),
        "status": data["status"],
        "balance": float(data["balance"]),
    }

def update_amount(account_id: uuid.UUID, delta: float, idempotency_key: Optional[str] = None) -> dict:
    if ACCOUNT_API == "mock":
        return _mock_update_amount(account_id, delta)
    payload = {"delta": float(delta)}
    if idempotency_key:
        payload["idempotency_key"] = idempotency_key
    return _post(f"{ACCOUNT_API}/internal/accounts/{account_id}/update-amount", payload)
