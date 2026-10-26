#!/usr/bin/env python3
"""Archive prezzi spot pubblici, senza inventare quotazioni mancanti."""
import concurrent.futures
import datetime as dt
import json
import urllib.error
import urllib.request
from pathlib import Path

TIMEOUT = 12
ASSETS = {
    "BTC": ("BTCUSDT", "BTC-USD", "BTC-USDT", "BTCUSDT"),
    "ETH": ("ETHUSDT", "ETH-USD", "ETH-USDT", "ETHUSDT"),
    "BNB": ("BNBUSDT", "BNB-USD", "BNB-USDT", "BNBUSDT"),
    "SOL": ("SOLUSDT", "SOL-USD", "SOL-USDT", "SOLUSDT"),
    "XRP": ("XRPUSDT", "XRP-USD", "XRP-USDT", "XRPUSDT"),
    "ADA": ("ADAUSDT", "ADA-USD", "ADA-USDT", "ADAUSDT"),
    "DOGE": ("DOGEUSDT", "DOGE-USD", "DOGE-USDT", "DOGEUSDT"),
    "TRX": ("TRXUSDT", "TRX-USD", "TRX-USDT", "TRXUSDT"),
    "TON": ("TONUSDT", "TON-USD", "TON-USDT", "TONUSDT"),
    "AVAX": ("AVAXUSDT", "AVAX-USD", "AVAX-USDT", "AVAXUSDT"),
    "LINK": ("LINKUSDT", "LINK-USD", "LINK-USDT", "LINKUSDT"),
    "DOT": ("DOTUSDT", "DOT-USD", "DOT-USDT", "DOTUSDT"),
    "LTC": ("LTCUSDT", "LTC-USD", "LTC-USDT", "LTCUSDT"),
    "BCH": ("BCHUSDT", "BCH-USD", "BCH-USDT", "BCHUSDT"),
    "XLM": ("XLMUSDT", "XLM-USD", "XLM-USDT", "XLMUSDT"),
    "UNI": ("UNIUSDT", "UNI-USD", "UNI-USDT", "UNIUSDT"),
    "AAVE": ("AAVEUSDT", "AAVE-USD", "AAVE-USDT", "AAVEUSDT"),
    "NEAR": ("NEARUSDT", "NEAR-USD", "NEAR-USDT", "NEARUSDT"),
    "ETC": ("ETCUSDT", "ETC-USD", "ETC-USDT", "ETCUSDT"),
    "FIL": ("FILUSDT", "FIL-USD", "FIL-USDT", "FILUSDT"),
    "ICP": ("ICPUSDT", "ICP-USD", "ICP-USDT", "ICPUSDT"),
    "ATOM": ("ATOMUSDT", "ATOM-USD", "ATOM-USDT", "ATOMUSDT"),
    "ARB": ("ARBUSDT", "ARB-USD", "ARB-USDT", "ARBUSDT"),
    "OP": ("OPUSDT", "OP-USD", "OP-USDT", "OPUSDT"),
    "SUI": ("SUIUSDT", "SUI-USD", "SUI-USDT", "SUIUSDT"),
    "SHIB": ("SHIBUSDT", "SHIB-USD", "SHIB-USDT", "SHIBUSDT"),
    "PEPE": ("PEPEUSDT", "PEPE-USD", "PEPE-USDT", "PEPEUSDT"),
    "INJ": ("INJUSDT", "INJ-USD", "INJ-USDT", "INJUSDT"),
    "SEI": ("SEIUSDT", "SEI-USD", "SEI-USDT", "SEIUSDT"),
    "HBAR": ("HBARUSDT", "HBAR-USD", "HBAR-USDT", "HBARUSDT"),
}
EXCHANGES = ("binance", "coinbase", "okx", "kraken")
KRAKEN_PAIRS = {
    "BTC": "XBTUSD", "ETH": "ETHUSD", "SOL": "SOLUSD", "XRP": "XRPUSD",
    "ADA": "ADAUSD", "DOGE": "DOGEUSD", "TRX": "TRXUSD", "AVAX": "AVAXUSD",
    "LINK": "LINKUSD", "DOT": "DOTUSD", "LTC": "LTCUSD", "BCH": "BCHUSD",
    "XLM": "XLMUSD", "UNI": "UNIUSD", "AAVE": "AAVEUSD", "NEAR": "NEARUSD",
    "ETC": "ETCUSD", "FIL": "FILUSD", "ICP": "ICPUSD", "ATOM": "ATOMUSD",
    "ARB": "ARBUSD", "OP": "OPUSD", "SUI": "SUIUSD", "SHIB": "SHIBUSD",
    "PEPE": "PEPEUSD", "INJ": "INJUSD", "SEI": "SEIUSD", "HBAR": "HBARUSD",
}


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "FinancePatternEngine/1.1"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_binance_price(symbol):
    # Prova in sequenza gli host API ufficiali Binance.
    hosts = (
        "api.binance.com",
        "api-gcp.binance.com",
        "api1.binance.com",
        "api2.binance.com",
        "api3.binance.com",
        "api4.binance.com",
        "data-api.binance.vision",
    )
    errors = []
    for host in hosts:
        url = f"https://{host}/api/v3/ticker/price?symbol={symbol}"
        try:
            data = get_json(url)
            price = float(data["price"])
            if price <= 0:
                raise ValueError("prezzo non positivo")
            return price
        except Exception as exc:
            errors.append(f"{host}: {str(exc)[:100]}")
    raise RuntimeError("Tutti gli host Binance hanno fallito: " + " | ".join(errors))


def fetch_price(exchange, symbol, asset=None):
    try:
        if exchange == "binance":
            price = fetch_binance_price(symbol)
        elif exchange == "coinbase":
            data = get_json("https://api.exchange.coinbase.com/products/" + symbol + "/ticker")
            price = float(data["price"])
        elif exchange == "okx":
            data = get_json("https://www.okx.com/api/v5/market/ticker?instId=" + symbol)
            price = float(data["data"][0]["last"])
        else:
            pair = KRAKEN_PAIRS.get(asset or "")
            if not pair:
                raise ValueError("Coppia USD non configurata su Kraken")
            data = get_json("https://api.kraken.com/0/public/Ticker?pair=" + pair)
            if data.get("error"):
                raise ValueError("; ".join(data["error"]))
            result = data.get("result") or {}
            if not result:
                raise ValueError("Nessuna coppia restituita da Kraken")
            price = float(next(iter(result.values()))["c"][0])
        if not price > 0:
            raise ValueError("prezzo non positivo")
        return price
    except Exception as exc:
        return {"error": str(exc)[:180]}


def collect_one(task):
    asset, exchange, symbol = task
    return asset, exchange, fetch_price(exchange, symbol, asset)


def main():
    now = dt.datetime.now(dt.timezone.utc)
    tasks = [
        (asset, exchange, symbols[i])
        for asset, symbols in ASSETS.items()
        for i, exchange in enumerate(EXCHANGES[:3])
    ] + [
        (asset, "kraken", KRAKEN_PAIRS.get(asset, ""))
        for asset in ASSETS
    ]
    quotes = {asset: {} for asset in ASSETS}
    # Chiamate concorrenti: il job periodico non deve impiegare minuti per ogni asset.
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        for asset, exchange, price in pool.map(collect_one, tasks):
            quotes[asset][exchange] = price

    record = {
        "timestamp_utc": now.isoformat(timespec="seconds"),
        "source": "public_spot_ticker_apis",
        "quotes": quotes,
    }
    outdir = Path("data/market")
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / (now.strftime("%Y-%m-%d") + ".jsonl")
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n")
    successful = sum(
        isinstance(price, (int, float))
        for asset_quotes in quotes.values()
        for price in asset_quotes.values()
    )
    print(f"Archived {record['timestamp_utc']}; successful quotes: {successful}/{len(tasks)}; file: {path}")
    if successful == 0:
        raise SystemExit("No exchange returned a valid price; archive contains diagnostics only.")


if __name__ == "__main__":
    main()
