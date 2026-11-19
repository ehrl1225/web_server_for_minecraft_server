import os
import requests
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QCloseEvent, QTextCursor
from PyQt6.QtWidgets import (
    QWidget, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout,
    QFileDialog, QMessageBox, QLabel, QSpinBox, QCheckBox, QGroupBox,
    QTextEdit, QSplitter, QTabWidget, QGridLayout
)
from PyQt6.QtCore import Qt
from src.router import server_data
from src.util.config import load_config, save_config
from src.util import stats_tracker
from .api_server_worker import ApiServerWorker


class OpenServerWidget(QWidget):
    server_started: bool = False

    def __init__(self):
        super().__init__()
        self.setWindowTitle("마인크래프트 웹서버 호스트 관리자")
        self.resize(750, 620)
        self.last_log_line = 0
        self.mc_was_started = False
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
        self.mc_start_btn = QPushButton("MC서버 시작")
        self.mc_stop_btn = QPushButton("MC서버 종료")

        url_hbox = QHBoxLayout()
        url_hbox.addWidget(self.url_lb)
        url_hbox.addWidget(self.url_le)
        url_hbox.addWidget(self.url_btn)

        server_btn_hbox = QHBoxLayout()
        server_btn_hbox.addWidget(self.port_lb)
        server_btn_hbox.addWidget(self.port_sp)
        server_btn_hbox.addWidget(self.start_btn)
        server_btn_hbox.addWidget(self.stop_btn)

        mc_server_btn_hbox = QHBoxLayout()
        mc_server_btn_hbox.addStretch(2)
        mc_server_btn_hbox.addWidget(self.mc_start_btn, 1)
        mc_server_btn_hbox.addWidget(self.mc_stop_btn, 1)

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

        # [탭 1: 서버 제어 및 콘솔] 위젯
        tab1_widget = QWidget()
        tab1_layout = QVBoxLayout()
        tab1_layout.addWidget(status_group)
        tab1_layout.addWidget(autostop_group)
        tab1_layout.addWidget(log_group, stretch=1)
        tab1_layout.addWidget(command_group)
        tab1_widget.setLayout(tab1_layout)

        # [탭 2: 서버 가동 및 접속자 통계] 위젯
        tab2_widget = QWidget()
        tab2_layout = QVBoxLayout()

        # Query 비활성화 경고 배너
        self.query_warning_lb = QLabel(
            "⚠️ 마인크래프트 server.properties에 'enable-query=true' 설정이 되어있지 않아 플레이어 통계를 수집할 수 없습니다.\n"
            "   (정확한 접속자 통계를 이용하려면 server.properties 파일에서 enable-query=true로 변경 후 서버를 재시작하세요)"
        )
        self.query_warning_lb.setStyleSheet(
            "background-color: #7F1D1D; color: #FCA5A5; padding: 10px; border-radius: 8px; font-weight: bold; font-size: 11px;"
        )
        self.query_warning_lb.setVisible(False)
        tab2_layout.addWidget(self.query_warning_lb)

        # 통계 요약 그룹박스
        summary_group = QGroupBox("누적 및 세션 요약 통계")
        grid = QGridLayout()

        self.stat_web_start_lb = QLabel("웹서버 최근 시작: -")
        self.stat_web_uptime_lb = QLabel("웹서버 누적 가동 시간: 0분")
        self.stat_mc_runs_lb = QLabel("MC 서버 실행 횟수: 0 회")
        self.stat_mc_uptime_lb = QLabel("MC 서버 누적 가동 시간: 0분")
        self.stat_peak_players_lb = QLabel("최대 동시 접속자(Peak): 0 명")
        self.stat_unique_players_lb = QLabel("방문한 고유 플레이어: 0 명 (-)")

        grid.addWidget(self.stat_web_start_lb, 0, 0)
        grid.addWidget(self.stat_web_uptime_lb, 0, 1)
        grid.addWidget(self.stat_mc_runs_lb, 1, 0)
        grid.addWidget(self.stat_mc_uptime_lb, 1, 1)
        grid.addWidget(self.stat_peak_players_lb, 2, 0)
        grid.addWidget(self.stat_unique_players_lb, 2, 1)
        summary_group.setLayout(grid)

        # 중요 이벤트 히스토리 뷰어
        events_group = QGroupBox("최근 시스템 및 플레이어 이벤트 히스토리")
        events_layout = QVBoxLayout()
        self.events_text_edit = QTextEdit()
        self.events_text_edit.setReadOnly(True)
        self.events_text_edit.setStyleSheet(
            "background-color: #111827; color: #60A5FA; font-family: Consolas, monospace; font-size: 11px;"
        )
        events_layout.addWidget(self.events_text_edit)
        events_group.setLayout(events_layout)

        tab2_layout.addWidget(summary_group)
        tab2_layout.addWidget(events_group, stretch=1)
        tab2_widget.setLayout(tab2_layout)

        # 탭 컨테이너 구성
        self.tabs = QTabWidget()
        self.tabs.addTab(tab1_widget, "🎮 서버 제어 & 콘솔")
        self.tabs.addTab(tab2_widget, "📊 통계 및 이벤트 로그")

        self.server_worker = ApiServerWorker()

        # 전체 레이아웃 구성
        vbox = QVBoxLayout()
        vbox.addLayout(url_hbox)
        vbox.addLayout(server_btn_hbox)
        vbox.addLayout(mc_server_btn_hbox)
        vbox.addWidget(self.tabs, stretch=1)

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
        self.mc_start_btn.pressed.connect(self.startMinecraftServer)
        self.mc_stop_btn.pressed.connect(self.stopMinecraftServer)
        self.mc_start_btn.setEnabled(False)
        self.mc_stop_btn.setEnabled(False)
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
        self.mc_start_btn.setEnabled(False)
        self.mc_stop_btn.setEnabled(False)
        self.server_started = False
        self.mc_was_started = False
        self.mc_status_lb.setText("상태: 오프라인 (웹서버 정지됨)")
        self.mc_players_lb.setText("접속자: 0 명")
        self.mc_ram_lb.setText("RAM 사용량: 0.0 GB")
        self.mc_autostop_lb.setText("빈 서버 자동 종료: 비활성")

        # 웹서버 종료 직후 최신 통계 및 이벤트 히스토리 로컬 반영
        self.updateStatisticsUI()

    def updateStatisticsUI(self, stats: dict | None = None, events: list[str] | None = None, query_enabled: bool = True, is_started: bool = False) -> None:
        """통계 라벨 및 최근 이벤트 히스토리 UI 갱신 (로컬 직접 읽기 또는 API 결과)"""
        if stats is None or events is None:
            data = stats_tracker.get_summary()
            stats = data.get("stats", {})
            events = data.get("recent_events", [])

        # 웹서버 통계 라벨
        web_start = stats.get("web_start_time") or "-"
        web_sec = stats.get("web_uptime_seconds", 0)
        web_m, web_s = divmod(web_sec, 60)
        web_h, web_m = divmod(web_m, 60)
        web_dur_str = f"{web_h}시간 {web_m}분" if web_h else f"{web_m}분 {web_s}초"
        self.stat_web_start_lb.setText(f"웹서버 최근 시작: {web_start}")
        self.stat_web_uptime_lb.setText(f"웹서버 누적 가동: {web_dur_str}")

        # MC 서버 통계 라벨
        mc_runs = stats.get("mc_run_count", 0)
        mc_sec = stats.get("mc_total_uptime_seconds", 0)
        mc_m, mc_s = divmod(mc_sec, 60)
        mc_h, mc_m = divmod(mc_m, 60)
        mc_dur_str = f"{mc_h}시간 {mc_m}분" if mc_h else f"{mc_m}분 {mc_s}초"
        self.stat_mc_runs_lb.setText(f"MC 서버 실행 횟수: {mc_runs}회")
        self.stat_mc_uptime_lb.setText(f"MC 서버 누적 가동: {mc_dur_str}")

        # 플레이어 통계 라벨
        if is_started and not query_enabled:
            self.stat_peak_players_lb.setText("최대 동시 접속자(Peak): [Query 비활성화로 통계 중단]")
            self.stat_unique_players_lb.setText("고유 플레이어: [server.properties enable-query=true 필요]")
        else:
            peak = stats.get("peak_players", 0)
            unique = stats.get("unique_players", [])
            unique_str = ", ".join(unique) if unique else "없음"
            self.stat_peak_players_lb.setText(f"최대 동시 접속자(Peak): {peak}명")
            self.stat_unique_players_lb.setText(f"고유 플레이어: {len(unique)}명 ({unique_str})")

        # 최근 이벤트 텍스트 갱신
        if events:
            self.events_text_edit.setPlainText("\n".join(events))
            events_cursor = self.events_text_edit.textCursor()
            events_cursor.movePosition(QTextCursor.MoveOperation.End)
            self.events_text_edit.setTextCursor(events_cursor)

    def startMinecraftServer(self) -> None:
        if not self.server_started:
            QMessageBox.warning(self, "경고", "먼저 웹서버를 시작해야 합니다.")
            return
        port = self.port_sp.value()
        try:
            res = requests.post(f"http://127.0.0.1:{port}/start-server", timeout=3).json()
            if res.get("status") is False:
                QMessageBox.warning(self, "안내", res.get("message", "서버를 시작할 수 없습니다."))
        except Exception as e:
            QMessageBox.critical(self, "오류", f"마인크래프트 서버 시작 요청 실패: {e}")

    def stopMinecraftServer(self) -> None:
        if not self.server_started:
            QMessageBox.warning(self, "경고", "먼저 웹서버를 시작해야 합니다.")
            return
        port = self.port_sp.value()
        try:
            res = requests.post(f"http://127.0.0.1:{port}/stop-server", timeout=3).json()
            if res.get("status") is False:
                QMessageBox.warning(self, "안내", res.get("message", "서버를 종료할 수 없습니다."))
        except Exception as e:
            QMessageBox.critical(self, "오류", f"마인크래프트 서버 종료 요청 실패: {e}")

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

            # 마인크래프트 서버 시작/종료 버튼 활성화 제어
            if is_stopping:
                self.mc_start_btn.setEnabled(False)
                self.mc_stop_btn.setEnabled(False)
            elif is_started:
                self.mc_start_btn.setEnabled(False)
                self.mc_stop_btn.setEnabled(True)
            else:
                self.mc_start_btn.setEnabled(True)
                self.mc_stop_btn.setEnabled(False)

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

            # 2. 서버가 새로 시작(부팅 시작 또는 재시작)되었는지 확인하여 로그 리셋
            if is_started and not self.mc_was_started:
                self.last_log_line = 0
                self.log_text_edit.clear()
            self.mc_was_started = is_started

            # 3. 콘솔 로그 실시간 가져오기 (/get-console-output)
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

            # 4. 통계 탭이 열려있거나 주기적으로 통계 및 이벤트 히스토리 갱신 (/statistics)
            try:
                stat_res = requests.get(f"{base_url}/statistics", timeout=1).json()
                stats = stat_res.get("stats", {})
                events = stat_res.get("recent_events", [])
                query_enabled = stat_res.get("query_enabled", True)

                # Query 비활성화 여부 경고 표시 (서버가 켜져 있을 때 query가 꺼져있으면 표시)
                if is_started and not query_enabled:
                    self.query_warning_lb.setVisible(True)
                else:
                    self.query_warning_lb.setVisible(False)

                self.updateStatisticsUI(stats=stats, events=events, query_enabled=query_enabled, is_started=is_started)
            except Exception:
                pass

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
