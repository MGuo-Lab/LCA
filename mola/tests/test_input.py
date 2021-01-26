# most of this functionality has moved to the output module
from unittest import TestCase
from pathlib import Path
import mola.input as mp
import pyomo.environ as pe
import mola.specification4a as ms
import json

# only use a DataPortal save to json as the mode configuration file?
# No that saves out all the openLCA data too,


class Pyomoio(TestCase):
    model = pe.ConcreteModel()
    model.A = pe.Set(initialize=[3, 2, 1], doc='Test set')
    model.B = pe.Set(within=model.A, initialize=[1, 2], doc='Test subset')
    # set of sets
    #model.C = pe.Set(model.A, initialize={3: [1, 2, 3], 2: [2, 3, 4], 1: [3, 4, 5]}, doc='Test Indexed Set')
    model.F_m = pe.Set(initialize=['1f7bbd3e-fcd1-412d-8608-035b855ea735'], doc='Test Material Flows')
    model.P = pe.Param(model.A, initialize=2, doc='Test Parameter')
    spec = ms.ScheduleSpecification()
    # json_files = ['test_set_data.json', 'test_parameter_data.json']
    # spec_instance = spec.populate(json_files)

    # def test__get_onset_names(self):
    #     # set_a = mp._get_onset_names(Pyomoio.model.A)
    #     # self.assertEqual(set_a, ['Any'])
    #     # set_b = mp._get_onset_names(Pyomoio.model.B)
    #     # self.assertEqual(set_b, ['A'])
    #     param_p = mp._get_onset_names(Pyomoio.model.P)
    #     self.assertEqual(param_p, ['Any'])
    #     param_f_s = mp._get_onset_names(Pyomoio.spec_instance.F_s)
    #     self.assertEqual(param_f_s, [])

    # def test_list_entities(self):
    #     dfr = mp.list_entities(Pyomoio.model, 'set')
    #     self.assertGreater(len(dfr), 0)
    #     dfr = mp.list_entities(Pyomoio.spec_instance, 'set')
    #     self.assertGreater(len(dfr), 0)
    #     dfr = mp.list_entities(Pyomoio.spec_instance, 'par')
    #     self.assertGreater(len(dfr), 0)

    # def test_get_entity(self):
    #     p = mp.get_entity(Pyomoio.model, 'P')
    #     self.assertGreater(len(p), 0)
    #     # flow = mp.get_entity(Pyomoio.spec_instance, 'Flow')
    #     # self.assertGreater(len(flow), 0)

    def test_get_model_user_parameters(self):
        spec = ms.ScheduleSpecification()
        # test modifications to the default set
        set_data = spec.get_default_sets()
        # need more than just default data to build a model instance
        set_data.update({
            'F_m': ['1f7bbd3e-fcd1-412d-8608-035b855ea735'],
            'P_m': ['f22f5f6e-1bdc-3cb5-8f48-8a04d8f9b768'],
            'KPI': ['061b7db5-4f56-3368-bf50-9ff0fcc8dd1f']
        })
        model_parameter_file_name = 'test_parameter_data.json'
        param_dfr, param_dict = mp.get_model_user_parameters(spec, set_data, model_parameter_file_name)
        self.assertGreater(len(param_dfr), 0)
