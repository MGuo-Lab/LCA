# test of QtConsole widget
import sys
import os
from unittest import TestCase

from PyQt5.QtWidgets import QApplication

from molaqt.console import QtConsoleWindow


class QtConsoleTest(TestCase):
    def test_init(self):
        app = QApplication(sys.argv)
        qt_console = QtConsoleWindow()
        qt_console.show()
        app.aboutToQuit.connect(qt_console.shutdown_kernel)

        if 'IGNORE_EXEC' not in os.environ:
            app.exec()

        self.assertIsInstance(qt_console, QtConsoleWindow)
