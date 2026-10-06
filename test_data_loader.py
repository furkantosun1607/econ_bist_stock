"""Offline checks for cached-data integrity and inclusive period boundaries."""

import hashlib
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from data_loader import _clean_data, _download_from_yfinance, load_stock_data


def sample_data(dates=("2025-01-02", "2026-09-30")):
    frame = pd.DataFrame(
        {"Open": 100.0, "High": 102.0, "Low": 99.0,
         "Close": 101.0, "Volume": 1_000},
        index=pd.to_datetime(list(dates)),
    )
    frame.index.name = "Date"
    return frame


class TestDataLoader(unittest.TestCase):
    def test_cached_data_is_validated_without_network_or_rewriting(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "AKBNK_ohlcv.csv"
            sample_data().to_csv(cache)
            original = cache.read_bytes()
            with patch("data_loader._get_cache_path", return_value=cache), \
                    patch("data_loader._download_from_yfinance") as download:
                with self.assertWarnsRegex(UserWarning, "2026-09-30"):
                    frame = load_stock_data("AKBNK.IS")
            download.assert_not_called()
            self.assertEqual(cache.read_bytes(), original)
            self.assertEqual(frame.attrs["data_coverage"]["actual_end"], "2026-09-30")
            self.assertFalse(frame.attrs["data_coverage"]["end_date_observed"])
            provenance = frame.attrs["data_provenance"]
            self.assertFalse(provenance["independently_verified"])
            self.assertEqual(provenance["sha256"], hashlib.sha256(original).hexdigest())

    def test_corrupt_cache_is_rejected_without_downloading(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "AKBNK_ohlcv.csv"
            frame = sample_data()
            frame.iloc[0, frame.columns.get_loc("High")] = 90
            frame.to_csv(cache)
            with patch("data_loader._get_cache_path", return_value=cache), \
                    patch("data_loader._download_from_yfinance") as download:
                with self.assertRaisesRegex(ValueError, "inconsistent OHLC"):
                    load_stock_data("AKBNK.IS")
            download.assert_not_called()

    def test_downloader_translates_inclusive_end_for_provider(self):
        with patch("data_loader.yf.download", return_value=sample_data()) as download:
            _download_from_yfinance("AKBNK.IS")
        self.assertEqual(download.call_args.kwargs["end"], "2026-10-02")
        self.assertTrue(download.call_args.kwargs["auto_adjust"])

    def test_cache_keeps_end_date_and_filters_outside_requested_period(self):
        dates = ("2024-12-31", "2025-01-02", "2026-10-01", "2026-10-02")
        result = _clean_data(sample_data(dates), "AKBNK.IS")
        self.assertEqual(list(result.index.strftime("%Y-%m-%d")),
                         ["2025-01-02", "2026-10-01"])

    def test_nonfinite_nonpositive_and_negative_volume_are_rejected(self):
        for column, value in (("Close", np.inf), ("Low", -1),
                              ("Open", 0), ("Volume", -1)):
            with self.subTest(column=column, value=value):
                frame = sample_data()
                frame.loc[frame.index[0], column] = value
                with self.assertRaises(ValueError):
                    _clean_data(frame, "AKBNK.IS")

    def test_missing_columns_and_empty_usable_data_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing OHLCV"):
            _clean_data(sample_data().drop(columns="Volume"), "AKBNK.IS")
        with self.assertRaisesRegex(ValueError, "no usable OHLCV"):
            _clean_data(sample_data(("2024-01-01",)), "AKBNK.IS")
        with self.assertRaisesRegex(ValueError, "invalid dates"):
            frame = sample_data()
            frame.index = ["not-a-date", "also-not-a-date"]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                _clean_data(frame, "AKBNK.IS")

    def test_complete_endpoint_has_no_coverage_warning(self):
        with patch("data_loader._download_from_yfinance", return_value=sample_data(
                ("2025-01-02", "2026-10-01"))):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                result = load_stock_data("AKBNK.IS", use_cache=False)
        self.assertEqual(len(caught), 0)
        self.assertTrue(result.attrs["data_coverage"]["end_date_observed"])


if __name__ == "__main__":
    unittest.main()
