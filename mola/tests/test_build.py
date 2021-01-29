# Unit tests for build functions
from unittest import TestCase
import mola.build as mb
import mola.specification5 as ms


class TestBuild(TestCase):
    def test_build_instance(self):
        config_files = [
            '../../config/Lemon_Toy_Model.json',
            'test_model_config.json',
            '../../config/test_custom_controller.json',
        ]
        for config_file in config_files:
            config = mb.get_config(config_file)
            instance = mb.build_instance(config)
            self.assertEqual(len(instance), 1)

    def test_create_specification(self):
        cls = "<class 'mola.specification5.ScheduleSpecification'>"
        spec = mb.create_specification(cls)
        self.assertIsInstance(spec, ms.ScheduleSpecification)

        spec1 = mb.create_specification(cls, settings={'distance_calculated': True})
        self.assertEqual(spec1.settings['distance_calculated'], True)
