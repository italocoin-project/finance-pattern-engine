#!/usr/bin/env python3
"""Aggiorna una cache statica CoinMarketCap, evitando chiamate API dal browser."""
import json
import os
import time
import urllib.error
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

BASE_KEYLESS = "https://pro-api.coinmarketcap.com/public-api/v3/cryptocurrency/listings/latest"
BASE_AUTH = "https://pro-api.coinmarketcap.com/v3/cryptocurrency/listings/latest"
API_KEY = os.environ.get("CMC_API_KEY", "").strip()
GLOBAL_URL = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest?convert=USD"
OUT = Path("data/market/cmc-market.json")
HEADERS = {"Accept": "application/json", "User-Agent": "FinancePatternEngine/1.0"}
LIMIT = 100
PAGES = 3

def fetch_page(start):
    base = BASE_AUTH if API_KEY else BASE_KEYLESS
    url = f"{base}?start={start}&limit={LIMIT}&convert=USD"
    headers = dict(HEADERS)
    if API_KEY:
        headers["X-CMC_PRO_API_KEY"] = API_KEY
    last_error = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=headers)
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
    raise RuntimeError(f"CoinMarketCap start={start}: {last_error}. If the keyless endpoint is blocked, add a repository Actions secret named CMC_API_KEY.")

def fetch_bitcoin_dominance():
    if not API_KEY:
        return None
    req = urllib.request.Request(GLOBAL_URL, headers={**HEADERS, "X-CMC_PRO_API_KEY": API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            payload = json.loads(response.read().decode("utf-8"))
        data = payload.get("data") or {}
        value = data.get("btc_dominance")
        return float(value) if value is not None else None
    except Exception as exc:
        print(f"Warning: global metrics unavailable: {exc}")
        return None

def main():
    coins = []
    for page in range(PAGES):
        coins.extend(fetch_page(page * LIMIT + 1))
        if page < PAGES - 1:
            time.sleep(1)
    normalized = []
    for c in coins:
        raw_quote = c.get("quote") or {}
        if isinstance(raw_quote, list):
            quote = next((item for item in raw_quote if item.get("symbol") == "USD" or item.get("name") == "USD"), {})
        elif isinstance(raw_quote, dict):
            quote = raw_quote.get("USD") or raw_quote
        else:
            quote = {}
        normalized.append({
            "id": c.get("slug"),
            "cmc_id": c.get("id"),
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
    # Fetch 7 daily historical price points for the cached assets once per UTC day.
    # Reuse the existing cache on subsequent 30-minute refreshes to control API credits.
    today = datetime.now(timezone.utc).date().isoformat()
    previous = {}
    try:
        previous_payload = json.loads(OUT.read_text(encoding="utf-8"))
        previous = {str(c.get("id")): c for c in previous_payload.get("coins", [])}
    except (OSError, ValueError, TypeError):
        previous = {}
    if API_KEY:
        stale = [c for c in normalized if not (
            previous.get(str(c.get("id")), {}).get("history_date") == today
            and len(previous.get(str(c.get("id")), {}).get("history_7d", [])) >= 2
        )]
        ids = [str(c["cmc_id"]) for c in stale if c.get("cmc_id") is not None]
        if ids:
            params = urllib.parse.urlencode({
                "id": ",".join(ids), "count": "7", "interval": "1d", "convert": "USD"
            })
            req = urllib.request.Request(
                "https://pro-api.coinmarketcap.com/v3/cryptocurrency/quotes/historical?" + params,
                headers={**HEADERS, "X-CMC_PRO_API_KEY": API_KEY}
            )
            try:
                with urllib.request.urlopen(req, timeout=45) as response:
                    historical = json.loads(response.read().decode("utf-8"))
                status = historical.get("status") or {}
                if status.get("error_code", 0) != 0:
                    raise RuntimeError(status.get("error_message") or "CoinMarketCap historical API error")
                history_data = historical.get("data") or {}
                for c in stale:
                    key = str(c.get("cmc_id"))
                    record = history_data.get(key) or {}
                    quotes = record.get("quotes") or []
                    prices = []
                    for item in quotes:
                        quote = ((item.get("quote") or {}).get("USD") or {})
                        try:
                            stamp = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00")).timestamp() * 1000
                            price = float(quote["price"])
                            prices.append([int(stamp), price])
                        except (KeyError, TypeError, ValueError):
                            continue
                    if len(prices) >= 2:
                        c["history_7d"] = prices
                        c["history_date"] = today
                    else:
                        old = previous.get(str(c.get("id")), {})
                        if old.get("history_7d"):
                            c["history_7d"] = old["history_7d"]
                            c["history_date"] = old.get("history_date")
                print(f"CoinMarketCap historical quotes: {sum(1 for c in normalized if c.get('history_7d'))}/{len(normalized)} assets cached")
            except Exception as exc:
                print(f"Warning: historical quotes unavailable; preserving previous history where possible: {exc}")
                for c in normalized:
                    old = previous.get(str(c.get("id")), {})
                    if old.get("history_7d"):
                        c["history_7d"] = old["history_7d"]
                        c["history_date"] = old.get("history_date")
    else:
        for c in normalized:
            old = previous.get(str(c.get("id")), {})
            if old.get("history_7d"):
                c["history_7d"] = old["history_7d"]
                c["history_date"] = old.get("history_date")
    bitcoin_dominance = fetch_bitcoin_dominance()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "CoinMarketCap API",
        "count": len(normalized),
        "bitcoin_dominance": bitcoin_dominance,
        "coins": normalized,
    }, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Updated {OUT}: {len(normalized)} assets")

if __name__ == "__main__":
    main()
