import React, { useState, useEffect, useCallback } from "react";

const API = process.env.REACT_APP_API_URL || "";

async function apiFetch(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

// ── tiny UI primitives ────────────────────────────────────────────────────

const Card = ({ title, children }) => (
  <div style={styles.card}>
    <h3 style={styles.cardTitle}>{title}</h3>
    {children}
  </div>
);

const Btn = ({ onClick, children, color = "#2563eb", disabled }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    style={{ ...styles.btn, background: disabled ? "#94a3b8" : color }}
  >
    {children}
  </button>
);

const Input = ({ value, onChange, placeholder, style }) => (
  <input
    value={value}
    onChange={(e) => onChange(e.target.value)}
    placeholder={placeholder}
    style={{ ...styles.input, ...style }}
  />
);

const Toast = ({ msg, type }) =>
  msg ? (
    <div style={{ ...styles.toast, background: type === "error" ? "#dc2626" : "#16a34a" }}>
      {msg}
    </div>
  ) : null;

// ── sections ──────────────────────────────────────────────────────────────

function BankSection({ onRefresh }) {
  const [stocks, setStocks] = useState([]);
  const [newName, setNewName] = useState("");
  const [newQty, setNewQty] = useState("");
  const [pending, setPending] = useState([]);
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = "ok") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const load = useCallback(async () => {
    try {
      const data = await apiFetch("/stocks");
      setStocks(data.stocks);
      setPending(data.stocks.map((s) => ({ ...s })));
    } catch (e) {
      showToast(e.message, "error");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const addRow = () => {
    if (!newName.trim() || isNaN(parseInt(newQty))) return;
    setPending((p) => [...p, { name: newName.trim(), quantity: parseInt(newQty) }]);
    setNewName("");
    setNewQty("");
  };

  const removeRow = (i) => setPending((p) => p.filter((_, idx) => idx !== i));

  const save = async () => {
    try {
      await apiFetch("/stocks", { method: "POST", body: JSON.stringify({ stocks: pending }) });
      showToast("Bank updated ✓");
      load();
      onRefresh();
    } catch (e) {
      showToast(e.message, "error");
    }
  };

  return (
    <Card title="🏦 Bank — Stock Inventory">
      <Toast msg={toast?.msg} type={toast?.type} />
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>Stock</th>
            <th style={styles.th}>Qty (bank)</th>
            <th style={styles.th}></th>
          </tr>
        </thead>
        <tbody>
          {pending.map((s, i) => (
            <tr key={i}>
              <td style={styles.td}>{s.name}</td>
              <td style={styles.td}>{s.quantity}</td>
              <td style={styles.td}>
                <Btn color="#dc2626" onClick={() => removeRow(i)}>✕</Btn>
              </td>
            </tr>
          ))}
          <tr>
            <td style={styles.td}>
              <Input value={newName} onChange={setNewName} placeholder="stock name" />
            </td>
            <td style={styles.td}>
              <Input value={newQty} onChange={setNewQty} placeholder="qty" style={{ width: 60 }} />
            </td>
            <td style={styles.td}>
              <Btn color="#16a34a" onClick={addRow}>＋ Add</Btn>
            </td>
          </tr>
        </tbody>
      </table>
      <Btn onClick={save}>Save to Bank</Btn>
    </Card>
  );
}

function TradeSection({ onRefresh }) {
  const [walletId, setWalletId] = useState("");
  const [stockName, setStockName] = useState("");
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = "ok") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const trade = async (type) => {
    if (!walletId.trim() || !stockName.trim()) {
      showToast("Fill wallet ID and stock name", "error");
      return;
    }
    try {
      await apiFetch(`/wallets/${walletId.trim()}/stocks/${stockName.trim()}`, {
        method: "POST",
        body: JSON.stringify({ type }),
      });
      showToast(`${type.toUpperCase()} successful ✓`);
      onRefresh();
    } catch (e) {
      showToast(e.message, "error");
    }
  };

  return (
    <Card title="⚡ Trade">
      <Toast msg={toast?.msg} type={toast?.type} />
      <div style={styles.row}>
        <Input value={walletId} onChange={setWalletId} placeholder="Wallet ID" />
        <Input value={stockName} onChange={setStockName} placeholder="Stock name" />
      </div>
      <div style={styles.row}>
        <Btn color="#16a34a" onClick={() => trade("buy")}>Buy 1</Btn>
        <Btn color="#dc2626" onClick={() => trade("sell")}>Sell 1</Btn>
      </div>
    </Card>
  );
}

function WalletSection({ refresh }) {
  const [walletId, setWalletId] = useState("");
  const [wallet, setWallet] = useState(null);
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = "ok") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  useEffect(() => {
    if (wallet) lookup();
  }, [refresh]);

  const lookup = async () => {
    if (!walletId.trim()) return;
    try {
      const data = await apiFetch(`/wallets/${walletId.trim()}`);
      setWallet(data);
    } catch (e) {
      showToast(e.message, "error");
    }
  };

  return (
    <Card title="👛 Wallet Lookup">
      <Toast msg={toast?.msg} type={toast?.type} />
      <div style={styles.row}>
        <Input value={walletId} onChange={setWalletId} placeholder="Wallet ID" />
        <Btn onClick={lookup}>Look up</Btn>
      </div>
      {wallet && (
        <div style={{ marginTop: 12 }}>
          <strong>ID:</strong> {wallet.id}
          {wallet.stocks.length === 0 ? (
            <p style={{ color: "#64748b" }}>Empty wallet</p>
          ) : (
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>Stock</th>
                  <th style={styles.th}>Qty</th>
                </tr>
              </thead>
              <tbody>
                {wallet.stocks.map((s) => (
                  <tr key={s.name}>
                    <td style={styles.td}>{s.name}</td>
                    <td style={styles.td}>{s.quantity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </Card>
  );
}

function LogSection({ refresh }) {
  const [log, setLog] = useState([]);

  const load = useCallback(async () => {
    try {
      const data = await apiFetch("/log");
      setLog(data.log);
    } catch (_) {}
  }, []);

  useEffect(() => {
    load();
  }, [load, refresh]);

  return (
    <Card title="📋 Audit Log">
      {log.length === 0 ? (
        <p style={{ color: "#64748b" }}>No operations yet.</p>
      ) : (
        <div style={{ maxHeight: 260, overflowY: "auto" }}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>#</th>
                <th style={styles.th}>Type</th>
                <th style={styles.th}>Wallet</th>
                <th style={styles.th}>Stock</th>
              </tr>
            </thead>
            <tbody>
              {log.map((entry, i) => (
                <tr key={i}>
                  <td style={styles.td}>{i + 1}</td>
                  <td style={{ ...styles.td, color: entry.type === "buy" ? "#16a34a" : "#dc2626", fontWeight: 600 }}>
                    {entry.type.toUpperCase()}
                  </td>
                  <td style={styles.td}>{entry.wallet_id}</td>
                  <td style={styles.td}>{entry.stock_name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function ChaosSection() {
  const [toast, setToast] = useState(null);
  const showToast = (msg, type = "ok") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  };
  const fire = async () => {
    try {
      await apiFetch("/chaos", { method: "POST" });
      showToast("Instance killed — other instances still running ✓");
    } catch (_) {
      showToast("Instance killed (connection closed as expected) ✓");
    }
  };
  return (
    <Card title="💥 Chaos Engineering">
      <Toast msg={toast?.msg} type={toast?.type} />
      <p style={{ color: "#64748b", marginBottom: 8 }}>
        Kills the instance that handles this request. Other instances keep running.
      </p>
      <Btn color="#7c3aed" onClick={fire}>POST /chaos</Btn>
    </Card>
  );
}

// ── App ───────────────────────────────────────────────────────────────────

export default function App() {
  const [refresh, setRefresh] = useState(0);
  const bump = () => setRefresh((r) => r + 1);

  return (
    <div style={styles.page}>
      <h1 style={styles.h1}>📈 Stock Market Simulator</h1>
      <div style={styles.grid}>
        <BankSection onRefresh={bump} />
        <TradeSection onRefresh={bump} />
        <WalletSection refresh={refresh} />
        <LogSection refresh={refresh} />
        <ChaosSection />
      </div>
    </div>
  );
}

// ── styles ────────────────────────────────────────────────────────────────

const styles = {
  page: { fontFamily: "system-ui, sans-serif", maxWidth: 960, margin: "0 auto", padding: 24 },
  h1: { fontSize: 28, marginBottom: 24, color: "#0f172a" },
  grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 },
  card: { background: "#fff", border: "1px solid #e2e8f0", borderRadius: 10, padding: 20, boxShadow: "0 1px 3px rgba(0,0,0,.08)" },
  cardTitle: { margin: "0 0 14px", fontSize: 16, fontWeight: 700, color: "#1e293b" },
  btn: { padding: "7px 14px", borderRadius: 6, border: "none", color: "#fff", cursor: "pointer", fontSize: 14, marginRight: 6 },
  input: { padding: "7px 10px", borderRadius: 6, border: "1px solid #cbd5e1", fontSize: 14, marginRight: 6, width: 140 },
  row: { display: "flex", alignItems: "center", flexWrap: "wrap", gap: 6, marginBottom: 10 },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 14 },
  th: { textAlign: "left", padding: "6px 8px", background: "#f8fafc", borderBottom: "1px solid #e2e8f0", color: "#475569" },
  td: { padding: "6px 8px", borderBottom: "1px solid #f1f5f9" },
  toast: { padding: "8px 12px", borderRadius: 6, color: "#fff", marginBottom: 10, fontSize: 14 },
};