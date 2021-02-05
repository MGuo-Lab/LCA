# units test of model manager
import os
import sys
from unittest import TestCase

from PyQt5.QtWidgets import QApplication

import molaqt.manager as mm
import molaqt.utils as mqu


app = QApplication(sys.argv)
setting = mqu.system_settings(testing=True)
config_path = setting['config_path'].joinpath('test_model_config.json')


class TestModelManager(TestCase):
    def test_init(self):
        model_manager = mm.ModelManager(setting)
        model_manager.show()
        model_manager.resize(1000, 600)

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()
        self.assertIsInstance(model_manager, mm.ModelManager)
