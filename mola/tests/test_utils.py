from unittest import TestCase
from pathlib import Path
import json
import mola.utils as mu
import mola.specification5 as ms


class TestUtils(TestCase):
    def test_build_instance(self):
        spec = ms.ScheduleSpecification()
        sets = spec.get_default_sets()
        config_file = Path('test_model_config.json')
        # config_file = Path('../../config/test_custom_controller.json')
        with open(config_file) as fp:
            config = json.load(fp)
        sets.update(config['sets'])
        parameters = spec.get_default_parameters(sets)
        config['parameters'].update(parameters)
        instance = mu.build_instance(config)
        self.assertEqual(len(instance), 1)

    def test_create_specification(self):
        cls = "<class 'mola.specification5.ScheduleSpecification'>"
        spec = mu.create_specification(cls)
        self.assertIsInstance(spec, ms.ScheduleSpecification)

        spec1 = mu.create_specification(cls, settings={'distance_calculated': True})
        self.assertEqual(spec1.settings['distance_calculated']['value'], True)
