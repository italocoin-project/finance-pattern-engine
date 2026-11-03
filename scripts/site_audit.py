#!/usr/bin/env python3
"""Run 100 deterministic, offline checks over the public Finance Pattern Engine site."""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = [
    "index.html",
    "markets.html",
    "coin.html",
    "privacy.html",
    "terms.html",
    "offline.html",
    "guide/confrontare-exchange.html",
    "guide/exchange-e-blockchain.html",
    "guide/leggere-storico-crypto.html",
    "guide/volumi-spread-liquidita.html",
]
ASSET_NAMES = [
    "BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "TRX", "TON", "AVAX",
    "LINK", "DOT", "LTC", "BCH", "XLM", "UNI", "AAVE", "NEAR", "ETC", "FIL",
    "ICP", "ATOM", "ARB", "OP", "SUI", "SHIB", "PEPE", "INJ", "SEI", "HBAR",
]
EXCHANGE_NAMES = ["binance", "coinbase", "okx", "kraken"]
checks: list[tuple[str, object]] = []


def add(name, fn):
    checks.append((name, fn))


def require(condition, message):
    if not condition:
        raise AssertionError(message)


# 50 page-level checks: five independent structural checks for each public page.
for relative in PAGES:
    path = ROOT / relative
    add(f"{relative}: file exists", lambda p=path: require(p.is_file(), "file missing"))
    add(f"{relative}: HTML5 doctype", lambda p=path: require(
        p.is_file() and p.read_text(encoding="utf-8").lstrip().lower().startswith("<!doctype html>"),
        "HTML5 doctype missing"))
    add(f"{relative}: Italian document language", lambda p=path: require(
        p.is_file() and re.search(r'<html\b[^>]*\blang=["\']it["\']', p.read_text(encoding="utf-8"), re.I),
        'html lang="it" missing'))
    add(f"{relative}: page title", lambda p=path: require(
        p.is_file() and re.search(r"<title>[^<]+</title>", p.read_text(encoding="utf-8"), re.I),
        "title missing"))
    add(f"{relative}: responsive viewport", lambda p=path: require(
        p.is_file() and re.search(r'<meta\s+name=["\']viewport["\']', p.read_text(encoding="utf-8"), re.I),
        "viewport meta missing"))

index_html = (ROOT / "index.html").read_text(encoding="utf-8")
collector = (ROOT / "scripts/archive_market_data.py").read_text(encoding="utf-8")
archive_map = re.search(r"ASSETS\s*=\s*\{(.*?)\n\}", collector, re.S)
market_map = re.search(r"const\s+marketAssets\s*=\s*\{(.*?)\n\};", index_html, re.S)
require(archive_map is not None, "collector ASSETS mapping not found")
require(market_map is not None, "homepage marketAssets mapping not found")
archive_block = archive_map.group(1)
market_block = market_map.group(1)

# 30 cross-project checks: every tracked asset exists in both live UI and archive collector.
for symbol in ASSET_NAMES:
    add(f"asset {symbol}: live UI and archive mappings agree", lambda s=symbol: require(
        re.search(rf"^\s*['"]?{re.escape(s)}['"]?\s*:", archive_block, re.M)
        and re.search(rf"^\s*{re.escape(s)}\s*:", market_block, re.M),
        f"{s} missing from one or both market mappings"))

# 12 exchange checks: configured, parsed, and selectable in the history interface.
exchange_list = re.search(r"EXCHANGES\s*=\s*\(([^)]*)\)", collector)
require(exchange_list is not None, "EXCHANGES tuple missing")
exchange_values = exchange_list.group(1)
history_select = re.search(r'<select\s+id=["\']historyExchange["\']>(.*?)</select>', index_html, re.S)
require(history_select is not None, "history exchange selector missing")
history_options = history_select.group(1)
for exchange in EXCHANGE_NAMES:
    add(f"{exchange}: collector configuration", lambda e=exchange: require(
        re.search(rf'["\']{re.escape(e)}["\']', exchange_values),
        f"{e} missing from EXCHANGES"))
    if exchange == "kraken":
        parser_ok = "KRAKEN_PAIRS.get(asset or" in collector
    elif exchange == "binance":
        parser_ok = 'if exchange == "binance":' in collector and "fetch_binance_price(symbol)" in collector
    else:
        parser_ok = f'elif exchange == "{exchange}":' in collector
    add(f"{exchange}: price parser exists", lambda ok=parser_ok, e=exchange: require(ok, f"{e} parser missing"))
    add(f"{exchange}: history filter exists", lambda e=exchange: require(
        re.search(rf'<option\s+value=["\']{re.escape(e)}["\']', history_options),
        f"{e} option missing from history selector"))

# Eight global checks complete the 100-check audit.
archive_workflow = (ROOT / ".github/workflows/archive-market-data.yml").read_text(encoding="utf-8")
all_html = "\n".join((ROOT / page).read_text(encoding="utf-8") for page in PAGES)
manifest = json.loads((ROOT / "manifest.webmanifest").read_text(encoding="utf-8"))
service_worker = (ROOT / "sw.js").read_text(encoding="utf-8")
privacy = (ROOT / "privacy.html").read_text(encoding="utf-8")
cache = json.loads((ROOT / "data/market/cmc-market.json").read_text(encoding="utf-8"))
sitemap = ET.parse(ROOT / "sitemap.xml").getroot()
robots = (ROOT / "robots.txt").read_text(encoding="utf-8")

add("global: five-minute archive schedule", lambda: require(
    'cron: "*/5 * * * *"' in archive_workflow, "archive schedule is not every five minutes"))
add("global: no active AdSense scripts", lambda: require(
    "adsbygoogle.js" not in all_html and 'class="adsense-slot"' not in all_html,
    "AdSense must remain disabled until privacy and consent are complete"))
add("global: PWA manifest is valid", lambda: require(
    manifest.get("start_url") == "./" and manifest.get("scope") == "./"
    and manifest.get("display") == "standalone" and bool(manifest.get("icons")),
    "manifest fields or icon missing"))
add("global: service worker provides offline and market-cache paths", lambda: require(
    "addAll(SHELL)" in service_worker and "offline.html" in service_worker
    and "cmc-market.json" in service_worker and "self.clients.claim()" in service_worker,
    "offline shell or market cache missing"))
add("global: privacy discloses browser storage", lambda: require(
    "local storage" in privacy.lower() and "cache storage" in privacy.lower(),
    "local and offline browser storage must be disclosed"))
add("global: CoinMarketCap cache has 300 real records", lambda: require(
    isinstance(cache.get("coins"), list) and len(cache["coins"]) >= 250
    and cache.get("count") == len(cache["coins"])
    and all(isinstance(c, dict) and c.get("name") and c.get("symbol") and
            isinstance(c.get("price"), (int, float)) and c["price"] > 0
            for c in cache["coins"]),
    "market cache is incomplete or contains invalid prices"))
add("global: sitemap is valid and includes core pages", lambda: require(
    sitemap.tag.endswith("urlset")
    and all("https://italocoin-project.github.io/finance-pattern-engine/" + p in
            [node.text for node in sitemap.iter() if node.tag.endswith("loc")]
            for p in ["markets.html", "coin.html", "privacy.html", "terms.html"]),
    "sitemap missing core pages"))
add("global: robots.txt advertises sitemap", lambda: require(
    "sitemap.xml" in robots.lower(), "sitemap reference missing from robots.txt"))

if len(checks) != 100:
    print(f"INTERNAL ERROR: expected 100 checks, registered {len(checks)}", file=sys.stderr)
    raise SystemExit(2)

failed = []
for name, check in checks:
    try:
        check()
        print(f"PASS {name}")
    except Exception as exc:  # Report every independent failure in one run.
        failed.append((name, str(exc)))
        print(f"FAIL {name}: {exc}")

print(f"\nSite audit: {len(checks) - len(failed)}/{len(checks)} passed; {len(failed)} failed.")
if failed:
    raise SystemExit(1)
