#!/usr/bin/env python3
"""Aggiorna una cache statica CoinMarketCap, evitando chiamate API dal browser."""
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://pro-api.coinmarketcap.com/public-api/v3/cryptocurrency/listings/latest"
OUT = Path("data/market/cmc-market.json")
HEADERS = {"Accept": "application/json", "User-Agent": "FinancePatternEngine/1.0"}
LIMIT = 100
PAGES = 3

def fetch_page(start):
    url = f"{BASE}?start={start}&limit={LIMIT}&convert=USD"
    last_error = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=25) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload.get("data"), list):
                status = payload.get("status") or {}
                raise RuntimeError(status.get("error_message") or "Risposta API senza data")
            return payload["data"]
        except Exception as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"CoinMarketCap start={start}: {last_error}")

def main():
    coins = []
    for page in range(PAGES):
        coins.extend(fetch_page(page * LIMIT + 1))
        if page < PAGES - 1:
            time.sleep(1)
    normalized = []
    for c in coins:
        quote = (c.get("quote") or {}).get("USD") or {}
        normalized.append({
            "id": c.get("slug"),
            "name": c.get("name"),
            "symbol": c.get("symbol"),
            "rank": c.get("cmc_rank"),
            "price": quote.get("price"),
            "change_24h": quote.get("percent_change_24h"),
            "change_7d": quote.get("percent_change_7d"),
            "change_30d": quote.get("percent_change_30d"),
            "market_cap": quote.get("market_cap"),
            "volume_24h": quote.get("volume_24h"),
            "circulating_supply": c.get("circulating_supply"),
            "total_supply": c.get("total_supply"),
            "max_supply": c.get("max_supply"),
            "last_updated": quote.get("last_updated") or c.get("last_updated"),
        })
    if len(normalized) < 250:
        raise RuntimeError(f"Cache incompleta: ricevuti solo {len(normalized)} asset")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "CoinMarketCap Keyless Public API",
        "count": len(normalized),
        "coins": normalized,
    }, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Updated {OUT}: {len(normalized)} assets")

if __name__ == "__main__":
    main()
