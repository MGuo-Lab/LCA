from unittest import TestCase
from tempfile import NamedTemporaryFile

import mola.specification5 as sp
import json


class TestScheduleSpecification(TestCase):
    spec = sp.ScheduleSpecification()
    with open('test_model_config.json') as fp:
        config = json.load(fp)

    def test_populate(self):
        # from a model config file write out sets and parameters to two temporary files
        # for the DataPortal in populate
        sets_json = NamedTemporaryFile(suffix='.json', delete=False)
        parameters_json = NamedTemporaryFile(suffix='.json', delete=False)
        with open(sets_json.name, 'w') as fp:
            json.dump(self.config['sets'], fp)
        with open(parameters_json.name, 'w') as fp:
            json.dump(self.config['parameters'], fp)
        model_instance = self.spec.populate([sets_json.name, parameters_json.name])
        self.assertGreater(len(model_instance), 0)
        model_instance = self.spec.populate([sets_json.name, parameters_json.name],
                                       elementary_flow_ref_ids=['e1, e2, e3'])
        self.assertGreater(len(model_instance), 0)

    def test_populate_calculated_distance(self):
        sets_json = NamedTemporaryFile(suffix='.json', delete=False)
        parameters_json = NamedTemporaryFile(suffix='.json', delete=False)

        # need to set X and Y coords to something meaningful for task
        config = self.config.copy()
        config['parameters']['X'] = [{'index': ['k1', 't1'], 'value': 0.0}]
        config['parameters']['Y'] = [{'index': ['k1', 't1'], 'value': 0.0}]

        with open(sets_json.name, 'w') as fp:
            json.dump(config['sets'], fp)
        with open(parameters_json.name, 'w') as fp:
            json.dump(config['parameters'], fp)

        self.spec.update_setting('distance_calculated', True)
        model_instance = self.spec.populate([sets_json.name, parameters_json.name])

        sets_json.close()
        parameters_json.close()
        self.assertGreater(len(model_instance), 0)