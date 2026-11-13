import os
import pytest
from src.util import ServerData, ServerStatus


def test_server_status_model():
    status = ServerStatus()
    assert status.is_starting is False
    assert status.is_online is False
    assert status.player_count == 0

    d = status.to_dict()
    assert d["is_starting"] is False
    assert d["is_online"] is False
    assert d["player_count"] == 0
    assert status.equal_to_dict(d) is True


def test_server_data_initial_state(tmp_path):
    sd = ServerData()
    assert sd.is_started() == {"is_started": False}
    assert sd.is_on() == {"is_on": False}
    # 서버 미구동 시 stop
    assert sd.stop() == {"message": "Server is not running"}
    # 서버 미구동 시 send_command
    assert sd.send_command("help") == {"message": "Server is not running"}


def test_server_data_save_and_load(tmp_path, monkeypatch):
    test_txt = str(tmp_path / "server_path.txt")
    monkeypatch.setattr("src.util.server_data.server_file_path_txt", test_txt)

    sd = ServerData()
    sd.set_server_file_path("C:/fake/path/server.bat")
    sd.save_server_file_path()

    assert os.path.exists(test_txt)

    sd2 = ServerData()
    assert sd2.load_server_file_path() is True
    assert sd2.server_file_path == "C:/fake/path/server.bat"
