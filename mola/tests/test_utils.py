# Unit tests for utility functions
from unittest import TestCase
import mola.utils as mu
import pandas as pd


class TestUtils(TestCase):

    def test_get_index_value_parameters(self):
        p = {'a': pd.DataFrame({'b': 1, 'c': 2}, index=[0])}
        d = mu.get_index_value_parameters(p)
        self.assertEqual(len(d), 1)
