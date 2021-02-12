# Unit tests for output functions
from unittest import TestCase
import pyomo.environ as pe

import mola.output as mo
import mola.dataimport as di
import mola.dataview as dv
import mola.build as mb


class Output(TestCase):
    config = mb.get_config('test_model_config.json')
    instance = mb.build_instance(config)
    conn = di.get_sqlite_connection()
    lookup = dv.LookupTables(conn)

    def test_get_entity(self):
        # output the variables with and without units
        for v in self.instance.component_objects(pe.Var, active=True):
            v_dfr = mo.get_entity(v)
            self.assertGreater(len(v_dfr), 0)
            u_dfr = mo.get_entity(v, self.lookup, units=True)
            self.assertGreater(len(u_dfr), 0)

        # name the unit set for lookup
        flow_dfr = mo.get_entity(self.instance.Flow, self.lookup, units=['P_m'])
        self.assertGreater(len(flow_dfr), 0)

    def test_objectives(self):
        # do the optimisation for each objective
        for i, o in enumerate(self.instance.component_objects(pe.Objective)):
            for j, oo in enumerate(self.instance.component_objects(pe.Objective)):
                if i == j:
                    oo.activate()
                else:
                    oo.deactivate()
            opt = pe.SolverFactory("glpk")
            opt.solve(self.instance)
            o_dfr = mo.get_entity(o)
            self.assertGreater(len(o_dfr), 0)
            ou_dfr = mo.get_entity(o, self.lookup, units=True)
            self.assertGreater(len(ou_dfr), 0)
