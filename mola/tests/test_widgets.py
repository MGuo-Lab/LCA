import json
from unittest import TestCase
from tempfile import NamedTemporaryFile
import mola.widgets as mw
import mola.dataview as dv
import mola.dataimport as di
import mola.specification4a as ms


class TestWidgets(TestCase):
    db_file = 'C:/data/openlca/sqlite/system/CSV_juice_ecoinvent_36_apos_lci_20200206_20201029-102818.sqlite'
    conn = di.get_sqlite_connection(db_file)
    lookup = dv.get_lookup_tables(conn)

    def test_get_set(self):
        dfr = TestWidgets.lookup['flows']
        set = mw.get_set(dfr)
        self.assertEqual(len(set.df), 0)

    def test_get_sets(self):
        lookups = {'F_m': TestWidgets.lookup['flows'],
                   'P_m': TestWidgets.lookup['processes'],
                   'KPI': TestWidgets.lookup['KPI']}
        with open('test_model_config.json') as fp:
            config = json.load(fp)
        sets_file = NamedTemporaryFile(suffix='.json', delete=False)
        with open(sets_file.name, 'w') as fp:
            json.dump(config['sets'], fp)
        spec = ms.ScheduleSpecification()
        vbox, tab = mw.get_sets(spec, lookups, sets_file.name)
        sets_file.close()
        self.assertEqual(len(vbox.children), 2)

