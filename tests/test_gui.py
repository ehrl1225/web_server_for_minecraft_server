import sys
from PyQt6.QtWidgets import QApplication
from src.gui import OpenServerWidget


def test_gui_widget_initialization(monkeypatch):
    # GUI 앱 인스턴스 초기화 테스트
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    widget = OpenServerWidget()
    assert widget.port_sp.value() == 9000
    assert widget.server_started is False
    assert widget.stop_btn.isEnabled() is False
    assert widget.start_btn.isEnabled() is True
