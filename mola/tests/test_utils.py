# Unit tests for utility functions
from unittest import TestCase
import mola.utils as mu
import mola.specification5 as ms


class TestUtils(TestCase):
    def test_build_instance(self):
        config_files = [
            'test_model_config.json',
            '../../config/test_custom_controller.json',
            '../../config/Lemon_Toy_Model.json'
        ]
        for config_file in config_files:
            config = mu.get_config(config_file)
            instance = mu.build_instance(config)
            self.assertEqual(len(instance), 1)

    def test_create_specification(self):
        cls = "<class 'mola.specification5.ScheduleSpecification'>"
        spec = mu.create_specification(cls)
        self.assertIsInstance(spec, ms.ScheduleSpecification)

        spec1 = mu.create_specification(cls, settings={'distance_calculated': True})
        self.assertEqual(spec1.settings['distance_calculated'], True)
