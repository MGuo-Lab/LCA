import json
from tempfile import NamedTemporaryFile
from pathlib import Path

from PyQt5 import QtWidgets
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.manager import QtKernelManager

# The ID of an installed kernel, e.g. 'bash' or 'ir'.
USE_KERNEL = 'python3'


def make_jupyter_widget_with_kernel():
    """
    Start a kernel, connect to it, and create a RichJupyterWidget to use it
    """
    kernel_manager = QtKernelManager(kernel_name=USE_KERNEL)
    kernel_manager.start_kernel()

    kernel_client = kernel_manager.client()
    kernel_client.start_channels()

    jupyter_widget = RichJupyterWidget(font_size=11)
    jupyter_widget.kernel_manager = kernel_manager
    jupyter_widget.kernel_client = kernel_client

    return jupyter_widget


class QtConsoleWindow(QtWidgets.QMainWindow):
    """A window that contains a single Qt console."""
    def __init__(self, manager=None):
        super().__init__()
        self.manager = manager
        self.setWindowTitle("Mola Debug Console")

        self.jupyter_widget = make_jupyter_widget_with_kernel()
        self.kc = self.jupyter_widget.kernel_client
        self.kc.execute(r'import mola.build as mb')
        self.setCentralWidget(self.jupyter_widget)

        main_tool_bar = self.addToolBar("Main")
        get_config = QtWidgets.QPushButton("Get Config")
        get_config.clicked.connect(self.get_config_clicked)
        build = QtWidgets.QPushButton("Build")
        build.clicked.connect(self.build_clicked)
        run = QtWidgets.QPushButton("Run")
        run.clicked.connect(self.run_clicked)
        main_tool_bar.addWidget(get_config)
        main_tool_bar.addWidget(build)
        main_tool_bar.addWidget(run)

    def get_config_clicked(self):
        if self.manager is not None and not isinstance(self.manager, QtWidgets.QLabel):
            config = self.manager.controller.get_config()
            config_json = NamedTemporaryFile(suffix='.json', delete=False)
            with open(config_json.name, 'w') as fp:
                json.dump(config, fp, indent=4)
            file_name = Path(config_json.name)
            self.kc.execute("cfg = mb.get_config(r'" + str(file_name) + "')", stop_on_error=False)
            self.kc.execute("cfg", stop_on_error=False)
            config_json.close()
        else:
            self.kc.execute("print('Model not loaded')", silent=True)

    def build_clicked(self):
        if self.manager is not None and not isinstance(self.manager, QtWidgets.QLabel):
            self.kc.execute(r'model = mb.build_instance(cfg)')

    def run_clicked(self):
        if self.manager is not None and not isinstance(self.manager, QtWidgets.QLabel):
            self.kc.execute("import pyomo.environ as pe")
            self.kc.execute("opt = pe.SolverFactory('glpk')")
            self.kc.execute("results = opt.solve(model)")
            self.kc.execute("results.write()")

    def shutdown_kernel(self):
        print('Shutting down kernel...')
        self.jupyter_widget.kernel_client.stop_channels()
        self.jupyter_widget.kernel_manager.shutdown_kernel()

