# test dialog widgets
import os
import sys
from unittest import TestCase

from PyQt5.QtWidgets import QApplication

import molaqt.dialogs as md

app = QApplication(sys.argv)


class Test(TestCase):
    def test_new_model_dialog(self):
        dialog = md.NewModelDialog(db_files=[])

        if 'IGNORE_EXEC' not in os.environ:
            if dialog.exec():
                print(dialog.get_inputs())

    # def test_doc_widget(self):
    #     self.fail()
    #
    # def test_rename_model_dialog(self):
    #     self.fail()
