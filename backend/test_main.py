"""
Tests for the Stock Market Service.
Run with: pytest test_main.py -v
"""

import pytest
from fastapi.testclient import TestClient

# Reset global state before each test
import main as app_module


@pytest.fixture(autouse=True)
def reset_state():
    """Wipe all in-memory state before every test."""
    app_module._bank.clear()
    app_module._wallets.clear()
    app_module._log.clear()
    yield


client = TestClient(app_module.app)


# ── /stocks ──────────────────────────────────────────────────────────────────

def test_get_stocks_empty():
    r = client.get("/stocks")
    assert r.status_code == 200
    assert r.json() == {"stocks": []}


def test_set_stocks():
    r = client.post("/stocks", json={"stocks": [{"name": "AAPL", "quantity": 10}]})
    assert r.status_code == 200
    r = client.get("/stocks")
    assert r.json() == {"stocks": [{"name": "AAPL", "quantity": 10}]}


def test_set_stocks_replaces_existing():
    client.post("/stocks", json={"stocks": [{"name": "AAPL", "quantity": 10}]})
    client.post("/stocks", json={"stocks": [{"name": "GOOG", "quantity": 5}]})
    r = client.get("/stocks")
    stocks = r.json()["stocks"]
    names = [s["name"] for s in stocks]
    assert "AAPL" not in names
    assert "GOOG" in names


# ── /wallets ─────────────────────────────────────────────────────────────────

def test_buy_creates_wallet():
    client.post("/stocks", json={"stocks": [{"name": "AAPL", "quantity": 5}]})
    r = client.post("/wallets/w1/stocks/AAPL", json={"type": "buy"})
    assert r.status_code == 200
    wallet = client.get("/wallets/w1").json()
    assert wallet["id"] == "w1"
    assert any(s["name"] == "AAPL" and s["quantity"] == 1 for s in wallet["stocks"])


def test_buy_reduces_bank():
    client.post("/stocks", json={"stocks": [{"name": "AAPL", "quantity": 3}]})
    client.post("/wallets/w1/stocks/AAPL", json={"type": "buy"})
    bank = client.get("/stocks").json()["stocks"]
    assert bank[0]["quantity"] == 2


def test_buy_nonexistent_stock_returns_404():
    r = client.post("/wallets/w1/stocks/FAKE", json={"type": "buy"})
    assert r.status_code == 404


def test_buy_empty_bank_returns_400():
    client.post("/stocks", json={"stocks": [{"name": "AAPL", "quantity": 0}]})
    r = client.post("/wallets/w1/stocks/AAPL", json={"type": "buy"})
    assert r.status_code == 400


def test_sell_nonexistent_stock_returns_404():
    r = client.post("/wallets/w1/stocks/FAKE", json={"type": "sell"})
    assert r.status_code == 404


def test_sell_without_holding_returns_400():
    client.post("/stocks", json={"stocks": [{"name": "AAPL", "quantity": 5}]})
    r = client.post("/wallets/w1/stocks/AAPL", json={"type": "sell"})
    assert r.status_code == 400


def test_sell_increases_bank():
    client.post("/stocks", json={"stocks": [{"name": "AAPL", "quantity": 5}]})
    client.post("/wallets/w1/stocks/AAPL", json={"type": "buy"})
    client.post("/wallets/w1/stocks/AAPL", json={"type": "sell"})
    bank = client.get("/stocks").json()["stocks"]
    assert bank[0]["quantity"] == 5


def test_get_wallet_stock_quantity():
    client.post("/stocks", json={"stocks": [{"name": "AAPL", "quantity": 5}]})
    client.post("/wallets/w1/stocks/AAPL", json={"type": "buy"})
    client.post("/wallets/w1/stocks/AAPL", json={"type": "buy"})
    r = client.get("/wallets/w1/stocks/AAPL")
    assert r.status_code == 200
    assert r.json() == 2


def test_get_wallet_stock_nonexistent_stock():
    r = client.get("/wallets/w1/stocks/FAKE")
    assert r.status_code == 404


# ── /log ─────────────────────────────────────────────────────────────────────

def test_log_records_successful_trades():
    client.post("/stocks", json={"stocks": [{"name": "AAPL", "quantity": 5}]})
    client.post("/wallets/w1/stocks/AAPL", json={"type": "buy"})
    client.post("/wallets/w1/stocks/AAPL", json={"type": "sell"})
    log = client.get("/log").json()["log"]
    assert len(log) == 2
    assert log[0] == {"type": "buy", "wallet_id": "w1", "stock_name": "AAPL"}
    assert log[1] == {"type": "sell", "wallet_id": "w1", "stock_name": "AAPL"}


def test_log_excludes_failed_trades():
    # attempt to buy non-existent stock – should not appear in log
    client.post("/wallets/w1/stocks/FAKE", json={"type": "buy"})
    log = client.get("/log").json()["log"]
    assert log == []


def test_log_order_preserved():
    client.post("/stocks", json={"stocks": [
        {"name": "AAPL", "quantity": 5},
        {"name": "GOOG", "quantity": 5},
    ]})
    client.post("/wallets/w1/stocks/AAPL", json={"type": "buy"})
    client.post("/wallets/w2/stocks/GOOG", json={"type": "buy"})
    log = client.get("/log").json()["log"]
    assert log[0]["stock_name"] == "AAPL"
    assert log[1]["stock_name"] == "GOOG"