from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QWidget, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QFileDialog, QMessageBox, QLabel, \
    QSpinBox
from src.router import server_data
from .api_server_worker import ApiServerWorker
import os


class OpenServerWidget(QWidget):

    server_started: bool = False

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.url_lb = QLabel("서버 파일 위치 : ")
        self.url_le = QLineEdit()
        self.url_btn = QPushButton("find")
        self.port_lb = QLabel("서버 포트 : ")
        self.port_sp = QSpinBox()
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.command_lb = QLabel("명령어 : ")
        self.command_le = QLineEdit()
        self.command_btn = QPushButton("Send")
        self.server_worker = ApiServerWorker()

        url_hbox = QHBoxLayout()
        url_hbox.addWidget(self.url_lb)
        url_hbox.addWidget(self.url_le)
        url_hbox.addWidget(self.url_btn)

        server_btn_hbox = QHBoxLayout()
        server_btn_hbox.addWidget(self.port_lb)
        server_btn_hbox.addWidget(self.port_sp)
        server_btn_hbox.addWidget(self.start_btn)
        server_btn_hbox.addWidget(self.stop_btn)

        command_hbox = QHBoxLayout()
        command_hbox.addWidget(self.command_lb)
        command_hbox.addWidget(self.command_le)
        command_hbox.addWidget(self.command_btn)

        vbox = QVBoxLayout()
        vbox.addLayout(url_hbox)
        vbox.addLayout(server_btn_hbox)
        vbox.addLayout(command_hbox)

        self.setLayout(vbox)

        self.setUI()

    def setUI(self) -> None:
        if server_data.load_server_file_path():
            self.url_le.setText(server_data.server_file_path)
        self.url_btn.pressed.connect(self.findUrl)
        self.port_sp.setMaximum(65535)
        self.port_sp.setValue(9000)
        self.start_btn.pressed.connect(self.startServer)
        self.stop_btn.pressed.connect(self.stopServer)
        self.command_le.returnPressed.connect(self.sendCommand)
        self.command_btn.pressed.connect(self.sendCommand)
        self.stop_btn.setEnabled(False)
        self.server_worker.server_started.connect(self.serverStarted)
        self.server_worker.server_stopped.connect(self.serverStopped)

    def findUrl(self) -> None:
        file_name, is_ok = QFileDialog.getOpenFileName(self, 'Open File', './', '*.bat')
        if (is_ok == False):
            return
        self.url_le.setText(file_name)

    def startServer(self) -> None:
        file_path = self.url_le.text()
        port = self.port_sp.value()
        if not os.path.isfile(file_path):
            QMessageBox.warning(self, 'Warning', 'Please enter a valid URL')
            return
        server_data.set_server_file_path(file_path)
        server_data.save_server_file_path()
        server_data.set_port(port)
        self.server_worker.start()

    def serverStarted(self) -> None:
        self.url_le.setEnabled(False)
        self.url_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.server_started = True

    def stopServer(self) -> None:
        self.server_worker.stop()

    def serverStopped(self) -> None:
        self.url_le.setEnabled(True)
        self.url_btn.setEnabled(True)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.server_started = False

    def sendCommand(self) -> None:
        server_data.sendCommand(self.command_le.text())
        self.command_le.clear()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.server_started == False:
            event.accept()
            return
        response=QMessageBox.warning(
            self,
            "경고",
            "서버가 켜져있습니다.\n종료하시겠습니까?",
            buttons=QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        if response == QMessageBox.StandardButton.Ok:
            event.accept()
        else:
            event.ignore()