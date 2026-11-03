#!/usr/bin/env python3
"""Archive real public spot prices in compact per-asset daily files."""
import concurrent.futures
import datetime as dt
import json
import math
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
    req = urllib.request.Request(url, headers={"User-Agent": "FinancePatternEngine/1.2"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_binance_price(symbol):
    hosts = (
        "api.binance.com", "api-gcp.binance.com", "api1.binance.com",
        "api2.binance.com", "api3.binance.com", "api4.binance.com",
        "data-api.binance.vision",
    )
    errors = []
    for host in hosts:
        try:
            data = get_json(f"https://{host}/api/v3/ticker/price?symbol={symbol}")
            price = float(data["price"])
            if not math.isfinite(price) or price <= 0:
                raise ValueError("prezzo non positivo o non valido")
            return price
        except Exception as exc:
            errors.append(f"{host}: {str(exc)[:75]}")
    raise RuntimeError("Host Binance non disponibili: " + " | ".join(errors))


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
        if not math.isfinite(price) or price <= 0:
            raise ValueError("prezzo non positivo o non valido")
        return price
    except Exception as exc:
        return {"error": str(exc)[:180]}


def build_tasks():
    return [
        (asset, exchange, symbols[index])
        for asset, symbols in ASSETS.items()
        for index, exchange in enumerate(EXCHANGES[:3])
    ] + [
        (asset, "kraken", KRAKEN_PAIRS.get(asset, ""))
        for asset in ASSETS
    ]


def _valid_quotes(values):
    return {
        exchange: price
        for exchange, price in (values or {}).items()
        if isinstance(price, (int, float))
        and not isinstance(price, bool)
        and math.isfinite(price)
        and price > 0
    }


def append_pair_archives(quotes, timestamp, root=Path("data/market")):
    """Write one compact daily JSONL per asset, so history loads only one asset."""
    stamp = timestamp.isoformat(timespec="seconds")
    date = timestamp.strftime("%Y-%m-%d")
    written = 0
    for asset, values in quotes.items():
        valid = _valid_quotes(values)
        if not valid:
            continue
        folder = Path(root) / "pairs" / asset
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{date}.jsonl"
        record = {
            "timestamp_utc": stamp,
            "source": "public_spot_ticker_apis",
            "quotes": {asset: valid},
        }
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n")
        written += 1
    return written


def migrate_legacy_archive(root=Path("data/market")):
    """Migrate old combined daily files once, preserving their original timestamps."""
    root = Path(root)
    pairs_root = root / "pairs"
    marker = pairs_root / ".legacy-migrated.json"
    if marker.exists():
        return 0
    pending = {}
    for source in sorted(root.glob("????-??-??.jsonl")):
        date = source.stem
        try:
            dt.date.fromisoformat(date)
        except ValueError:
            continue
        for line in source.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            stamp = record.get("timestamp_utc")
            if not stamp:
                continue
            for asset, values in (record.get("quotes") or {}).items():
                if asset not in ASSETS:
                    continue
                valid = _valid_quotes(values)
                if not valid:
                    continue
                path = pairs_root / asset / f"{date}.jsonl"
                pending.setdefault(path, []).append({
                    "timestamp_utc": stamp,
                    "source": "legacy_archive_migration",
                    "quotes": {asset: valid},
                })

    migrated = 0
    for path, records in pending.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = set()
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    existing.add(json.loads(line).get("timestamp_utc"))
                except (json.JSONDecodeError, TypeError):
                    continue
        with path.open("a", encoding="utf-8") as stream:
            for record in records:
                if record["timestamp_utc"] in existing:
                    continue
                stream.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n")
                existing.add(record["timestamp_utc"])
                migrated += 1

    pairs_root.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({
        "completed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "records_migrated": migrated,
    }) + "\n", encoding="utf-8")
    print(f"Legacy archive migration complete: {migrated} pair records")
    return migrated


def main():
    now = dt.datetime.now(dt.timezone.utc)
    migrate_legacy_archive()
    quotes = {asset: {} for asset in ASSETS}
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        for asset, exchange, price in pool.map(collect_one, build_tasks()):
            quotes[asset][exchange] = price

    written = append_pair_archives(quotes, now)
    successful = sum(len(_valid_quotes(values)) for values in quotes.values())
    failures = len(build_tasks()) - successful
    by_exchange = {
        exchange: sum(
            1 for asset_values in quotes.values()
            if not _valid_quotes({exchange: asset_values.get(exchange)})
        )
        for exchange in EXCHANGES
    }
    print(
        f"Archived {now.isoformat(timespec='seconds')}; "
        f"successful quotes: {successful}/120; failed: {failures}; "
        f"asset files updated: {written}; failures by exchange: {by_exchange}"
    )
    if successful == 0:
        raise SystemExit("No exchange returned a valid price; no market data was fabricated.")


def collect_one(task):
    asset, exchange, symbol = task
    return asset, exchange, fetch_price(exchange, symbol, asset)


if __name__ == "__main__":
    main()
