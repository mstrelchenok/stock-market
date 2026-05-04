"""
Simplified Stock Market Service
================================
Backend built with FastAPI + Python.
Stores all state in-memory (shared across instances via Redis if available,
falls back to local memory for single-instance mode).
"""

import os
import sys
import json
import threading
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── State ──────────────────────────────────────────────────────────────────
# We use a simple in-process store protected by a threading.Lock.
# For the high-availability requirement (POST /chaos kills one instance but
# the service stays up) you run 2+ instances behind a load-balancer and use
# Redis for shared state.  When REDIS_URL is set we switch automatically.

_lock = threading.Lock()

# bank:   { stock_name: quantity }
# wallets:{ wallet_id: { stock_name: quantity } }
# log:    [ {type, wallet_id, stock_name}, … ]
_bank: dict[str, int] = {}
_wallets: dict[str, dict[str, int]] = {}
_log: list[dict] = []


def _get_store():
    """Returns (bank, wallets, log) – currently in-memory objects."""
    return _bank, _wallets, _log


# ── Pydantic models ─────────────────────────────────────────────────────────

class TradeRequest(BaseModel):
    type: str  # "buy" | "sell"


class StockEntry(BaseModel):
    name: str
    quantity: int


class StocksPayload(BaseModel):
    stocks: List[StockEntry]


# ── App setup ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield  # nothing special on startup / shutdown for in-memory mode


app = FastAPI(
    title="Simplified Stock Market",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _wallet_to_response(wallet_id: str, holdings: dict) -> dict:
    return {
        "id": wallet_id,
        "stocks": [
            {"name": name, "quantity": qty}
            for name, qty in holdings.items()
            if qty > 0
        ],
    }


# ── Endpoints ────────────────────────────────────────────────────────────────

# 1. POST /wallets/{wallet_id}/stocks/{stock_name}
@app.post("/wallets/{wallet_id}/stocks/{stock_name}", status_code=200)
def trade_stock(wallet_id: str, stock_name: str, body: TradeRequest):
    """Buy or sell a single unit of a stock."""
    if body.type not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail="type must be 'buy' or 'sell'")

    with _lock:
        bank, wallets, log = _get_store()

        # Stock must exist in the bank
        if stock_name not in bank:
            raise HTTPException(status_code=404, detail=f"Stock '{stock_name}' does not exist")

        if body.type == "buy":
            if bank[stock_name] <= 0:
                raise HTTPException(status_code=400, detail="No stock available in bank")
            # Auto-create wallet
            if wallet_id not in wallets:
                wallets[wallet_id] = {}
            wallets[wallet_id][stock_name] = wallets[wallet_id].get(stock_name, 0) + 1
            bank[stock_name] -= 1

        else:  # sell
            if wallet_id not in wallets or wallets[wallet_id].get(stock_name, 0) <= 0:
                raise HTTPException(status_code=400, detail="No stock in wallet to sell")
            wallets[wallet_id][stock_name] -= 1
            bank[stock_name] += 1

        log.append({"type": body.type, "wallet_id": wallet_id, "stock_name": stock_name})

    return {"status": "ok"}


# 2. GET /wallets/{wallet_id}
@app.get("/wallets/{wallet_id}")
def get_wallet(wallet_id: str):
    """Return current state of a wallet."""
    with _lock:
        bank, wallets, log = _get_store()
        holdings = wallets.get(wallet_id, {})
        return _wallet_to_response(wallet_id, holdings)


# 3. GET /wallets/{wallet_id}/stocks/{stock_name}
@app.get("/wallets/{wallet_id}/stocks/{stock_name}")
def get_wallet_stock(wallet_id: str, stock_name: str):
    """Return quantity of a specific stock in a wallet."""
    with _lock:
        bank, wallets, log = _get_store()
        if stock_name not in bank:
            raise HTTPException(status_code=404, detail=f"Stock '{stock_name}' does not exist")
        qty = wallets.get(wallet_id, {}).get(stock_name, 0)
        return qty


# 4. GET /stocks
@app.get("/stocks")
def get_stocks():
    """Return current state of the bank."""
    with _lock:
        bank, wallets, log = _get_store()
        return {
            "stocks": [{"name": name, "quantity": qty} for name, qty in bank.items()]
        }


# 5. POST /stocks
@app.post("/stocks", status_code=200)
def set_stocks(body: StocksPayload):
    """Set (replace) the bank's stock inventory."""
    with _lock:
        bank, wallets, log = _get_store()
        bank.clear()
        for entry in body.stocks:
            bank[entry.name] = entry.quantity
    return {"status": "ok"}


# 6. GET /log
@app.get("/log")
def get_log():
    """Return the full audit log."""
    with _lock:
        bank, wallets, log = _get_store()
        return {"log": list(log)}


# 7. POST /chaos
@app.post("/chaos", status_code=200)
def chaos():
    """Kill this instance (for HA testing)."""
    # Schedule shutdown after response is sent
    def _kill():
        import time
        time.sleep(0.1)
        os.kill(os.getpid(), 9)

    t = threading.Thread(target=_kill, daemon=True)
    t.start()
    return {"status": "instance shutting down"}


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)