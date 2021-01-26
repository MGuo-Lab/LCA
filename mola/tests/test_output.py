from unittest import TestCase
import mola.output as o
import mola.dataimport as di
import mola.dataview as dv
import mola.utils as mu


class Output(TestCase):
    config = mu.get_config('test_model_config.json')
    instance = mu.build_instance(config)
    conn = di.get_sqlite_connection()
    lookup = dv.LookupTables(conn)

    def test_get_entity(self):
        flow = self.instance.component('Flow')
        c = self.instance.component('C')
        flow_dfr = o.get_entity(flow)
        self.assertGreater(len(flow_dfr), 0)
        c_dfr = o.get_entity(c)
        self.assertGreater(len(c_dfr), 0)

        # with lookups and units
        flow_dfr = o.get_entity(flow, self.lookup, units=['P_m'])
        self.assertGreater(len(flow_dfr), 0)
        c_dfr = o.get_entity(c, self.lookup)
        self.assertGreater(len(c_dfr), 0)

