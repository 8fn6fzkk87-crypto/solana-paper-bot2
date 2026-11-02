"""Solana paper trading only. No wallet connection or real orders."""
import json
import urllib.request
from pathlib import Path
from datetime import datetime, timezone, timedelta

STATE = Path("state.json")
REPORT = Path("REPORT.md")
FEE = 0.003
SLIPPAGE = 0.005
NETWORK_FEE = 0.01
TRADE_SIZE = 3.0

def get_price():
    request = urllib.request.Request(
        "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd",
        headers={"User-Agent": "solana-paper-bot2/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        value = float(json.load(response)["solana"]["usd"])
    if not 0 < value < 1000000:
        raise ValueError("Invalid price")
    return value

def main():
    now = datetime.now(timezone.utc)
    state = json.loads(STATE.read_text())
    if state["started_at"] is None:
        state["started_at"] = now.isoformat()
    start = datetime.fromisoformat(state["started_at"])
    price = get_price()
    cash = float(state["cash"])
    sol = float(state["sol"])
    equity = cash + sol * price
    if state["day"] != now.date().isoformat():
        state["day"] = now.date().isoformat()
        state["day_start_equity"] = equity
    decision = "HOLD"
    ended = now >= start + timedelta(hours=7)
    entry = state.get("entry_price")
    if sol > 0 and (ended or price >= entry * 1.03 or price <= entry * 0.97):
        proceeds = sol * price * (1 - FEE - SLIPPAGE) - NETWORK_FEE
        cash += max(0, proceeds)
        sol = 0.0
        state["entry_price"] = None
        state["trades"].append({"time": now.isoformat(), "side": "SELL", "price": price, "proceeds": round(proceeds, 5)})
        decision = "SELL"
    elif not ended and sol == 0 and equity > state["day_start_equity"] - 1.0:
        ref = state.get("reference_price")
        if ref is not None and price <= ref * 0.98 and cash >= TRADE_SIZE + NETWORK_FEE:
            cash -= TRADE_SIZE + NETWORK_FEE
            sol = TRADE_SIZE * (1 - FEE - SLIPPAGE) / price
            state["entry_price"] = price
            state["trades"].append({"time": now.isoformat(), "side": "BUY", "price": price, "spent": TRADE_SIZE + NETWORK_FEE})
            decision = "BUY"
    if sol == 0:
        ref = state.get("reference_price")
        state["reference_price"] = max(price, ref or 0) if not ended else price
    state["cash"] = cash
    state["sol"] = sol
    state["finished"] = ended
    state["last_scan"] = now.isoformat()
    state["trades"] = state["trades"][-100:]
    STATE.write_text(json.dumps(state, indent=2) + "\n")
    equity = cash + sol * price
    lines = ["# Solana paper trading report", "", f"Updated (UTC): {now.isoformat()}", f"Session finished: {ended}", f"Decision: {decision}", f"SOL price: ${price:.4f}", f"Cash: ${cash:.4f}", f"SOL (simulated): {sol:.8f}", f"Equity: ${equity:.4f}", f"P/L: ${equity-10:.4f}", "", "## Trades"]
    for trade in state["trades"]:
        lines.append(f"- {trade['time']}: {trade['side']} at ${trade['price']:.4f}")
    lines += ["", "Simulated only; 0.3% fee + 0.5% slippage per side, plus $0.01 network fee. No real orders."]
    REPORT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))

if __name__ == "__main__":
    main()
