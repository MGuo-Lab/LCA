# Unit tests for output functions
from unittest import TestCase
import mola.output as o
import mola.dataimport as di
import mola.dataview as dv
import mola.build as mb


class Output(TestCase):
    config = mb.get_config('test_model_config.json')
    instance = mb.build_instance(config)
    conn = di.get_sqlite_connection()
    lookup = dv.LookupTables(conn)

    def test_get_entity(self):
        # TODO just go through each output variable programmatically
        flow = self.instance.Flow
        storage_service_flow = self.instance.Storage_Service_Flow
        demand_selection = self.instance.Demand_Selection
        c = self.instance.C
        flow_dfr = o.get_entity(flow)
        self.assertGreater(len(flow_dfr), 0)
        c_dfr = o.get_entity(c)
        self.assertGreater(len(c_dfr), 0)

        # with lookups and units
        demand_selection_dfr = o.get_entity(demand_selection, self.lookup, units=True)
        self.assertGreater(len(demand_selection_dfr), 0)
        flow_dfr = o.get_entity(flow, self.lookup, units=['P_m'])
        self.assertGreater(len(flow_dfr), 0)
        c_dfr = o.get_entity(c, self.lookup)
        self.assertGreater(len(c_dfr), 0)
        storage_service_flow_dfr = o.get_entity(storage_service_flow, self.lookup, units=True)
        self.assertGreater(len(storage_service_flow_dfr), 0)

