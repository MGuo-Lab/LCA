import json
from unittest import TestCase
from tempfile import NamedTemporaryFile
import mola.widgets as mw
import mola.dataview as dv
import mola.dataimport as di
import mola.specification5 as ms


class TestWidgets(TestCase):
    conn = di.get_sqlite_connection()
    lookup = dv.get_lookup_tables(conn)

    def test_get_set(self):
        dfr = TestWidgets.lookup['flows']
        set_qgw = mw.get_set(dfr)
        self.assertEqual(len(set_qgw.df), 0)

    def test_get_sets(self):
        lookups = {'F_m': self.lookup['flows'],
                   'P_m': self.lookup['processes'],
                   'KPI': self.lookup['KPI']}
        with open('test_model_config.json') as fp:
            config = json.load(fp)
        sets_file = NamedTemporaryFile(suffix='.json', delete=False)
        with open(sets_file.name, 'w') as fp:
            json.dump(config['sets'], fp)
        spec = ms.GeneralSpecification()
        vbox, tab = mw.get_sets(spec, lookups, sets_file.name)
        sets_file.close()
        self.assertEqual(len(vbox.children), 2)

