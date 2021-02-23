# test of QtConsole widget
import sys
import os
from unittest import TestCase

from PyQt5.QtWidgets import QApplication

from molaqt.console import QtConsoleWindow


class TestQtConsole(TestCase):
    def test_init(self):

        # TODO: does not seem to work silently so no automated test for now
        if 'IGNORE_EXEC' not in os.environ:
            app = QApplication(sys.argv)
            qt_console = QtConsoleWindow()
            qt_console.show()
            app.aboutToQuit.connect(qt_console.shutdown_kernel)
            app.exec()

            self.assertIsInstance(qt_console, QtConsoleWindow)
        else:
            self.assertTrue(True)
