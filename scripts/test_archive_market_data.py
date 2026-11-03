import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import archive_market_data as archive


class ArchiveMarketDataTests(unittest.TestCase):
    def test_asset_universe_has_30_unique_assets(self):
        self.assertEqual(len(archive.ASSETS), 30)
        self.assertEqual(len(set(archive.ASSETS)), 30)

    def test_tasks_cover_three_primary_exchanges_and_kraken(self):
        tasks = archive.build_tasks()
        self.assertEqual(len(tasks), 120)
        self.assertEqual(sum(task[1] == "kraken" for task in tasks), 30)
        self.assertEqual(set(task[1] for task in tasks), set(archive.EXCHANGES))

    @patch("scripts.archive_market_data.get_json")
    def test_binance_price_is_parsed(self, get_json):
        get_json.return_value = {"price": "123.45"}
        self.assertEqual(archive.fetch_price("binance", "BTCUSDT", "BTC"), 123.45)

    @patch("scripts.archive_market_data.get_json")
    def test_coinbase_price_is_parsed(self, get_json):
        get_json.return_value = {"price": "234.56"}
        self.assertEqual(archive.fetch_price("coinbase", "BTC-USD", "BTC"), 234.56)

    @patch("scripts.archive_market_data.get_json")
    def test_okx_price_is_parsed(self, get_json):
        get_json.return_value = {"data": [{"last": "345.67"}]}
        self.assertEqual(archive.fetch_price("okx", "BTC-USDT", "BTC"), 345.67)

    @patch("scripts.archive_market_data.get_json")
    def test_kraken_price_is_parsed(self, get_json):
        get_json.return_value = {"error": [], "result": {"XXBTZUSD": {"c": ["567.89"]}}}
        self.assertEqual(archive.fetch_price("kraken", "XBTUSD", "BTC"), 567.89)

    def test_unsupported_kraken_pair_returns_diagnostic_not_price(self):
        result = archive.fetch_price("kraken", "", "BNB")
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)

    @patch("scripts.archive_market_data.get_json")
    def test_invalid_zero_price_is_rejected(self, get_json):
        get_json.return_value = {"price": "0"}
        result = archive.fetch_price("binance", "BTCUSDT", "BTC")
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)

    @patch("scripts.archive_market_data.get_json")
    def test_non_finite_price_is_rejected(self, get_json):
        get_json.return_value = {"price": "NaN"}
        result = archive.fetch_price("binance", "BTCUSDT", "BTC")
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)

    @patch("scripts.archive_market_data.get_json")
    def test_api_failure_is_recorded_as_error(self, get_json):
        get_json.side_effect = OSError("temporarily unavailable")
        result = archive.fetch_price("coinbase", "BTC-USD", "BTC")
        self.assertIsInstance(result, dict)
        self.assertIn("temporarily unavailable", result["error"])

    def test_pair_archive_writes_only_valid_prices(self):
        with tempfile.TemporaryDirectory() as tmp:
            timestamp = datetime(2026, 11, 3, 12, 55, tzinfo=timezone.utc)
            quotes = {"BTC": {"binance": 123.4, "coinbase": {"error": "offline"}, "okx": float("nan")}}
            written = archive.append_pair_archives(quotes, timestamp, Path(tmp))
            self.assertEqual(written, 1)
            path = Path(tmp) / "pairs" / "BTC" / "2026-11-03.jsonl"
            record = json.loads(path.read_text(encoding="utf-8").strip())
            self.assertEqual(record["quotes"]["BTC"], {"binance": 123.4})
            self.assertEqual(record["timestamp_utc"], "2026-11-03T12:55:00+00:00")

    def test_legacy_archive_migrates_once_without_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = {
                "timestamp_utc": "2026-11-02T10:00:00+00:00",
                "quotes": {"BTC": {"binance": 100.0, "coinbase": {"error": "offline"}}},
            }
            (root / "2026-11-02.jsonl").write_text(json.dumps(old) + "\n", encoding="utf-8")
            self.assertEqual(archive.migrate_legacy_archive(root), 1)
            self.assertEqual(archive.migrate_legacy_archive(root), 0)
            path = root / "pairs" / "BTC" / "2026-11-02.jsonl"
            records = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(records), 1)
            self.assertEqual(json.loads(records[0])["quotes"]["BTC"]["binance"], 100.0)


if __name__ == "__main__":
    unittest.main()
