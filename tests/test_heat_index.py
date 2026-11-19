import math
import unittest

import pandas as pd

from data_pipeline.preprocessing.heat_index import (
    calculate_heat_index_celsius,
    calculate_heat_index_fahrenheit,
    calculate_heat_index_series,
    classify_heat_index,
)


class HeatIndexTests(unittest.TestCase):
    def test_simple_formula_path(self):
        self.assertAlmostEqual(calculate_heat_index_fahrenheit(68.0, 50.0), 67.425, places=6)
        self.assertAlmostEqual(calculate_heat_index_celsius(20.0, 50.0), 19.6805556, places=6)

    def test_rothfusz_regression_path(self):
        self.assertAlmostEqual(
            calculate_heat_index_celsius(35.0, 70.0),
            50.3405781,
            places=6,
        )

    def test_low_humidity_adjustment(self):
        self.assertAlmostEqual(
            calculate_heat_index_celsius(32.2222222222, 10.0),
            29.5994269,
            places=6,
        )

    def test_high_humidity_adjustment(self):
        self.assertAlmostEqual(
            calculate_heat_index_celsius(29.4444444444, 90.0),
            38.7671131,
            places=6,
        )

    def test_invalid_inputs_return_nan(self):
        self.assertTrue(math.isnan(calculate_heat_index_celsius(None, 50)))
        self.assertTrue(math.isnan(calculate_heat_index_celsius(25, 101)))
        self.assertTrue(math.isnan(calculate_heat_index_celsius(-61, 50)))

    def test_vectorized_series_preserves_index(self):
        temperature = pd.Series([20.0, 35.0], index=[4, 8])
        humidity = pd.Series([50.0, 70.0], index=[4, 8])
        result = calculate_heat_index_series(temperature, humidity)
        self.assertListEqual(result.index.tolist(), [4, 8])
        self.assertEqual(len(result), 2)

    def test_pagasa_boundaries(self):
        expected = {
            26.99: "Not Hazardous",
            27.0: "Caution",
            32.99: "Caution",
            33.0: "Extreme Caution",
            41.99: "Extreme Caution",
            42.0: "Danger",
            51.99: "Danger",
            52.0: "Extreme Danger",
        }
        for value, category in expected.items():
            with self.subTest(value=value):
                self.assertEqual(classify_heat_index(value), category)


if __name__ == "__main__":
    unittest.main()
