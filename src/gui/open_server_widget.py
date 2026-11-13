import os
import requests
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QCloseEvent, QTextCursor
from PyQt6.QtWidgets import (
    QWidget, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout,
    QFileDialog, QMessageBox, QLabel, QSpinBox, QCheckBox, QGroupBox,
    QTextEdit, QSplitter
)
from PyQt6.QtCore import Qt
from src.router import server_data
from src.util.config import load_config, save_config
from .api_server_worker import ApiServerWorker


class OpenServerWidget(QWidget):
    server_started: bool = False

    def __init__(self):
        super().__init__()
        self.setWindowTitle("마인크래프트 웹서버 호스트 관리자")
        self.resize(750, 620)
        self.last_log_line = 0
        self.initUI()

    def initUI(self):
        # 1. 상단: 서버 파일 위치 및 웹서버 포트
        self.url_lb = QLabel("서버 파일 위치 : ")
        self.url_le = QLineEdit()
        self.url_btn = QPushButton("find")

        self.port_lb = QLabel("웹서버 포트 : ")
        self.port_sp = QSpinBox()
        self.start_btn = QPushButton("웹서버 시작")
        self.stop_btn = QPushButton("웹서버 종료")

        url_hbox = QHBoxLayout()
        url_hbox.addWidget(self.url_lb)
        url_hbox.addWidget(self.url_le)
        url_hbox.addWidget(self.url_btn)

        server_btn_hbox = QHBoxLayout()
        server_btn_hbox.addWidget(self.port_lb)
        server_btn_hbox.addWidget(self.port_sp)
        server_btn_hbox.addWidget(self.start_btn)
        server_btn_hbox.addWidget(self.stop_btn)

        # 2. 마인크래프트 실시간 상태 모니터링 (상태, 접속자, RAM 사용량, 자동종료)
        status_group = QGroupBox("마인크래프트 실시간 상태")
        status_layout = QVBoxLayout()

        status_row1 = QHBoxLayout()
        self.mc_status_lb = QLabel("상태: 오프라인")
        self.mc_players_lb = QLabel("접속자: 0 명")
        self.mc_ram_lb = QLabel("RAM 사용량: 0.0 GB")
        status_row1.addWidget(self.mc_status_lb)
        status_row1.addWidget(self.mc_players_lb)
        status_row1.addWidget(self.mc_ram_lb)

        status_row2 = QHBoxLayout()
        self.mc_autostop_lb = QLabel("빈 서버 자동 종료: 대기 중")
        status_row2.addWidget(self.mc_autostop_lb)

        status_layout.addLayout(status_row1)
        status_layout.addLayout(status_row2)
        status_group.setLayout(status_layout)

        # 3. 빈 서버 자동 종료(Auto-Stop) 설정
        autostop_group = QGroupBox("빈 서버 자동 종료 설정")
        autostop_layout = QHBoxLayout()

        self.autostop_chk = QCheckBox("플레이어가 0명일 때 자동 종료")
        self.autostop_timeout_sp = QSpinBox()
        self.autostop_timeout_sp.setRange(1, 180)
        self.autostop_timeout_sp.setSuffix(" 분 후")

        autostop_layout.addWidget(self.autostop_chk)
        autostop_layout.addWidget(self.autostop_timeout_sp)
        autostop_group.setLayout(autostop_layout)

        # 4. 실시간 콘솔 로그 뷰어
        log_group = QGroupBox("마인크래프트 실시간 콘솔 로그")
        log_layout = QVBoxLayout()

        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setStyleSheet(
            "background-color: #111827; color: #E5E7EB; font-family: Consolas, monospace; font-size: 11px;"
        )
        log_layout.addWidget(self.log_text_edit)
        log_group.setLayout(log_layout)

        # 5. 콘솔 명령어 입력 및 전송
        command_group = QGroupBox("마인크래프트 콘솔 명령어 전송")
        command_hbox = QHBoxLayout()
        self.command_le = QLineEdit()
        self.command_le.setPlaceholderText("예: op nickname, stop, list, save-all")
        self.command_btn = QPushButton("Send")
        command_hbox.addWidget(self.command_le)
        command_hbox.addWidget(self.command_btn)
        command_group.setLayout(command_hbox)

        self.server_worker = ApiServerWorker()

        # 전체 레이아웃 구성
        vbox = QVBoxLayout()
        vbox.addLayout(url_hbox)
        vbox.addLayout(server_btn_hbox)
        vbox.addWidget(status_group)
        vbox.addWidget(autostop_group)
        vbox.addWidget(log_group, stretch=1)
        vbox.addWidget(command_group)

        self.setLayout(vbox)
        self.setUI()

        # 실시간 상태 및 로그 폴링 타이머 (1.5초 간격)
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(1500)
        self.poll_timer.timeout.connect(self.pollServerStatus)

    def setUI(self) -> None:
        if server_data.load_server_file_path():
            self.url_le.setText(server_data.server_file_path)
        self.url_btn.pressed.connect(self.findUrl)
        self.port_sp.setMaximum(65535)
        self.port_sp.setValue(9000)

        # 설정 파일 로드
        cfg = load_config()
        self.autostop_chk.setChecked(cfg.get("auto_stop_enabled", True))
        self.autostop_timeout_sp.setValue(cfg.get("auto_stop_timeout_minutes", 10))

        self.autostop_chk.toggled.connect(self.saveAutoStopConfig)
        self.autostop_timeout_sp.valueChanged.connect(self.saveAutoStopConfig)

        self.start_btn.pressed.connect(self.startServer)
        self.stop_btn.pressed.connect(self.stopServer)
        self.command_le.returnPressed.connect(self.sendCommand)
        self.command_btn.pressed.connect(self.sendCommand)
        self.stop_btn.setEnabled(False)

        self.server_worker.server_started.connect(self.serverStarted)
        self.server_worker.server_stopped.connect(self.serverStopped)

    def saveAutoStopConfig(self) -> None:
        cfg = {
            "auto_stop_enabled": self.autostop_chk.isChecked(),
            "auto_stop_timeout_minutes": self.autostop_timeout_sp.value(),
        }
        save_config(cfg)

    def findUrl(self) -> None:
        file_name, is_ok = QFileDialog.getOpenFileName(self, 'Open File', './', '*.bat')
        if not is_ok:
            return
        self.url_le.setText(file_name)

    def startServer(self) -> None:
        file_path = self.url_le.text()
        port = self.port_sp.value()
        if not os.path.isfile(file_path):
            QMessageBox.warning(self, '경고', '올바른 .bat 파일 경로를 입력하세요.')
            return
        server_data.set_server_file_path(file_path)
        server_data.save_server_file_path()
        server_data.set_port(port)
        self.saveAutoStopConfig()
        self.last_log_line = 0
        self.server_worker.start()

    def serverStarted(self) -> None:
        self.url_le.setEnabled(False)
        self.url_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.server_started = True
        self.poll_timer.start()

    def stopServer(self) -> None:
        self.poll_timer.stop()
        self.server_worker.stop()

    def serverStopped(self) -> None:
        self.url_le.setEnabled(True)
        self.url_btn.setEnabled(True)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.server_started = False
        self.mc_status_lb.setText("상태: 오프라인 (웹서버 정지됨)")
        self.mc_players_lb.setText("접속자: 0 명")
        self.mc_ram_lb.setText("RAM 사용량: 0.0 GB")
        self.mc_autostop_lb.setText("빈 서버 자동 종료: 비활성")

    def pollServerStatus(self) -> None:
        """FastAPI 백엔드로 주기적으로 마인크래프트 실시간 상태 및 로그 질의"""
        if not self.server_started:
            return
        port = self.port_sp.value()
        base_url = f"http://127.0.0.1:{port}"

        try:
            # 1. 상태 및 접속자, RAM 조회 (/status)
            res = requests.get(f"{base_url}/status", timeout=1).json()
            is_started = res.get("is_started", False)
            is_online = res.get("is_online", False)
            is_stopping = res.get("is_stopping", False)
            player_count = res.get("player_count", 0)
            max_players = res.get("max_players", 20)
            ram_gb = res.get("ram_usage_gb", 0.0)

            # 라벨 텍스트 업데이트
            self.mc_players_lb.setText(f"접속자: {player_count} / {max_players} 명")
            self.mc_ram_lb.setText(f"RAM 사용량: {ram_gb} GB")

            if is_stopping:
                self.mc_status_lb.setText("상태: 월드 저장 및 안전 종료 중...")
                self.mc_autostop_lb.setText("빈 서버 자동 종료: 종료 진행 중")
            elif not is_started:
                self.mc_status_lb.setText("상태: 오프라인 (꺼짐)")
                self.mc_autostop_lb.setText("빈 서버 자동 종료: 대기 중")
            elif is_online:
                self.mc_status_lb.setText("상태: 온라인 (구동 중)")
                if player_count > 0:
                    self.mc_autostop_lb.setText("빈 서버 자동 종료: 플레이어 활동 중")
                else:
                    rem_sec = res.get("auto_stop_remaining_seconds", 0)
                    rem_min = rem_sec // 60
                    rem_sec_mod = rem_sec % 60
                    self.mc_autostop_lb.setText(f"빈 서버 자동 종료: {rem_min}분 {rem_sec_mod}초 후 자동 종료")
            else:
                self.mc_status_lb.setText("상태: 켜지는 중 (부팅 중)...")
                self.mc_autostop_lb.setText("빈 서버 자동 종료: 부팅 대기 중")

            # 2. 콘솔 로그 실시간 가져오기 (/get-console-output)
            log_res = requests.post(
                f"{base_url}/get-console-output",
                json={"startline": self.last_log_line},
                timeout=1
            ).json()

            new_logs = log_res.get("console_output", [])
            if new_logs:
                self.last_log_line += len(new_logs)
                for line in new_logs:
                    self.log_text_edit.append(line.rstrip("\r\n"))
                # 자동 하단 스크롤
                cursor = self.log_text_edit.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.log_text_edit.setTextCursor(cursor)

        except Exception:
            pass

    def sendCommand(self) -> None:
        cmd = self.command_le.text().strip()
        if not cmd:
            return
        if not self.server_started:
            QMessageBox.warning(self, "경고", "웹서버가 실행 중이지 않습니다.")
            return

        port = self.port_sp.value()
        try:
            res = requests.post(
                f"http://127.0.0.1:{port}/send-command",
                json={"command": cmd},
                timeout=2
            ).json()
            if "error" in res:
                QMessageBox.warning(self, "오류", res["error"])
        except Exception as e:
            QMessageBox.critical(self, "오류", f"명령어 전송 실패: {e}")

        self.command_le.clear()

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self.server_started:
            event.accept()
            return
        response = QMessageBox.warning(
            self,
            "경고",
            "웹서버가 실행 중입니다.\n종료하시겠습니까?",
            buttons=QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        if response == QMessageBox.StandardButton.Ok:
            self.stopServer()
            event.accept()
        else:
            event.ignore()
