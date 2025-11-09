# create_db.py
"""
Run from project root:
  python create_db.py
Optional:
  python create_db.py --seed scripts/transactions.csv
"""

import sys
import csv
import uuid
import argparse
from pathlib import Path

# 1) Load environment from .env so DATABASE_URL is available
try:
    from dotenv import load_dotenv  # pip install python-dotenv
    load_dotenv()
except Exception as e:
    print(f"[warn] python-dotenv not found or failed to load: {e}")

# 2) Import DB base/engine and models (MUST import models before create_all)
from app.db.session import engine, Base, SessionLocal

# --- Models your service owns ---
from app.models.transaction import Transaction
from app.models.daily_ledger import DailyTransferLedger
from app.models.idempotency import IdempotencyRecord  # if you added it

def create_tables() -> None:
    """Create all tables owned by the Transaction Service."""
    print("➡️  Creating tables ...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables are up to date.")

def seed_transactions(csv_path: Path) -> None:
    """Optional: seed Transactions from a CSV with columns:
       account_id, amount, txn_type, counterparty, reference
    """
    if not csv_path.exists():
        print(f"[seed] CSV not found: {csv_path}")
        return

    print(f"➡️  Seeding transactions from {csv_path}")
    count = 0
    db = SessionLocal()
    try:
        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    tx = Transaction(
                        account_id=uuid.UUID(row["account_id"]),
                        amount=float(row["amount"]),
                        txn_type=row["txn_type"].strip().upper(),  # 'DEBIT' or 'CREDIT'
                        counterparty=row.get("counterparty") or None,
                        reference=row.get("reference") or None,
                    )
                    db.add(tx)
                    count += 1
                except Exception as e:
                    print(f"[seed] skip row due to error: {e} | row={row}")
            db.commit()
        print(f"✅ Seeded {count} transactions.")
    finally:
        db.close()

def parse_args():
    ap = argparse.ArgumentParser(description="Create DB schema and optional seed for Transaction Service")
    ap.add_argument("--seed", type=str, help="Path to transactions CSV to seed")
    return ap.parse_args()

def main():
    # Safety check: ensure we can connect
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
    except Exception as e:
        print("❌ Could not connect to the database. Check DATABASE_URL in your .env.")
        print(f"   Error: {e}")
        sys.exit(1)

    create_tables()

    args = parse_args()
    if args.seed:
        seed_transactions(Path(args.seed))

if __name__ == "__main__":
    main()
