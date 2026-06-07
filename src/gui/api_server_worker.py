from PyQt6.QtCore import QObject, pyqtSignal
from src.router import server_data
import subprocess
import atexit

class ApiServerWorker(QObject):
    server_started = pyqtSignal()
    server_stopped = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.process = None

    def start(self):
        try:
            self.process = subprocess.Popen(
                [
                    "uv",
                    "run",
                    "uvicorn",
                    "src.main:app",
                    "--host=0.0.0.0",
                    f"--port={str(server_data.port)}"
                 ]
            )
            def cleanup():
                self.process.terminate()
            atexit.register(cleanup)
        except Exception as e:
            print(e)
        self.server_started.emit()

    def stop(self):
        if self.process is not None:
            self.process.terminate()
            self.process = None
            self.server_stopped.emit()