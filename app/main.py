from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.transfer import router as transfer_router  # if you created earlier
from app.api.money import router as money_router
from app.api.ledger import router as ledger_router   # <-- add


app = FastAPI(title="Transaction Service", version="0.1.0")
app.include_router(health_router)
app.include_router(money_router)
app.include_router(ledger_router)
app.include_router(transfer_router)  # keep if present

@app.get("/health")
def _(): return {"ok": True}
