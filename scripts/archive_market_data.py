#!/usr/bin/env python3
"""Collecte des prix spot publics de quatre exchanges et archive en JSONL."""
import datetime as dt
import json
import os
import urllib.request
from pathlib import Path

TIMEOUT = 15
ASSETS = {
    "BTC": {"binance": "BTCUSDT", "coinbase": "BTC-USD", "okx": "BTC-USDT", "bybit": "BTCUSDT"},
    "ETH": {"binance": "ETHUSDT", "coinbase": "ETH-USD", "okx": "ETH-USDT", "bybit": "ETHUSDT"},
    "SOL": {"binance": "SOLUSDT", "coinbase": "SOL-USD", "okx": "SOL-USDT", "bybit": "SOLUSDT"},
}

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "FinancePatternEngine/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))

def fetch_price(exchange, symbol):
    try:
        if exchange == "binance":
            data = get_json("https://api.binance.com/api/v3/ticker/price?symbol=" + symbol)
            return float(data["price"])
        if exchange == "coinbase":
            data = get_json("https://api.exchange.coinbase.com/products/" + symbol + "/ticker")
            return float(data["price"])
        if exchange == "okx":
            data = get_json("https://www.okx.com/api/v5/market/ticker?instId=" + symbol)
            return float(data["data"][0]["last"])
        if exchange == "bybit":
            data = get_json("https://api.bybit.com/v5/market/tickers?category=spot&symbol=" + symbol)
            return float(data["result"]["list"][0]["lastPrice"])
    except Exception as exc:
        return {"error": str(exc)[:180]}
    return {"error": "exchange non supportato"}

def main():
    now = dt.datetime.now(dt.timezone.utc)
    record = {
        "timestamp_utc": now.isoformat(timespec="seconds"),
        "source": "public_spot_ticker_apis",
        "quotes": {},
    }
    for asset, pairs in ASSETS.items():
        record["quotes"][asset] = {}
        for exchange, symbol in pairs.items():
            record["quotes"][asset][exchange] = fetch_price(exchange, symbol)

    outdir = Path("data/market")
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / (now.strftime("%Y-%m-%d") + ".jsonl")
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n")
    successful = sum(
        isinstance(price, (int, float))
        for asset_quotes in record["quotes"].values()
        for price in asset_quotes.values()
    )
    print(f"Archived {record['timestamp_utc']}; successful quotes: {successful}/12; file: {path}")

if __name__ == "__main__":
    main()
