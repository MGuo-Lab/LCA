from unittest import TestCase
import sys
import os
from PyQt5.QtWidgets import QApplication

import molaqt.build as mb
import molaqt.utils as mqu
import molaqt.controllers as mc

app = QApplication(sys.argv)


class BuildTest(TestCase):
    def test_model_build(self):
        setting = mqu.system_settings(testing=True)
        config_path = setting['config_path'].joinpath('test_custom_controller.json')
        new_config = mqu.build_config(config_path)
        controller = mc.CustomController(new_config)
        model_build = mb.ModelBuild(controller)
        model_build.show()

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()
        self.assertIsInstance(model_build, mb.ModelBuild)

