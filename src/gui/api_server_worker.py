from PyQt6.QtCore import QObject, pyqtSignal
from src.router import server_data
import subprocess
import os
import sys


class ApiServerWorker(QObject):
    server_started = pyqtSignal()
    server_stopped = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.process = None

    def start(self):
        try:
            port = str(server_data.port)
            # PyInstaller exe 환경이든 일반 python 실행 환경이든
            # uv 의존성 없이 sys.executable 자체를 서브프로세스로 구동
            if getattr(sys, "frozen", False):
                cmd = [sys.executable, "--serve", f"--port={port}"]
            else:
                main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "main.py"))
                cmd = [sys.executable, main_py, "--serve", f"--port={port}"]

            self.process = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
        except Exception as e:
            print(f"[ApiServerWorker] 서버 시작 실패: {e}")
        self.server_started.emit()

    def stop(self):
        if self.process is not None:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False
                )
            except Exception as e:
                print(f"[ApiServerWorker] 서버 종료 실패: {e}")
            finally:
                self.process = None
                self.server_stopped.emit()
