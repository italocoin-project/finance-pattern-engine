import unittest
from unittest.mock import patch

from scripts import archive_market_data as archive


class ArchiveMarketDataTests(unittest.TestCase):
    def test_asset_universe_has_30_unique_assets(self):
        self.assertEqual(len(archive.ASSETS), 30)
        self.assertEqual(len(set(archive.ASSETS)), 30)

    def test_tasks_cover_three_primary_exchanges_and_kraken(self):
        tasks = [
            (asset, exchange, symbols[i])
            for asset, symbols in archive.ASSETS.items()
            for i, exchange in enumerate(archive.EXCHANGES[:3])
        ] + [
            (asset, "kraken", archive.KRAKEN_PAIRS.get(asset, ""))
            for asset in archive.ASSETS
        ]
        self.assertEqual(len(tasks), 120)
        self.assertEqual(sum(task[1] == "kraken" for task in tasks), 30)

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
    def test_api_failure_is_recorded_as_error(self, get_json):
        get_json.side_effect = OSError("temporarily unavailable")
        result = archive.fetch_price("coinbase", "BTC-USD", "BTC")
        self.assertIsInstance(result, dict)
        self.assertIn("temporarily unavailable", result["error"])


if __name__ == "__main__":
    unittest.main()
