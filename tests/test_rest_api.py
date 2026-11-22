import pytest
from starlette.testclient import TestClient
from main import app
from src.router import server_data


def test_rest_api_ping():
    with TestClient(app) as client:
        res = client.get("/ping")
        assert res.status_code == 200
        assert res.json() == {"message": "pong!"}


def test_rest_api_root():
    with TestClient(app) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert "마인크래프트" in res.json()["message"]


def test_rest_api_server_status_endpoints():
    with TestClient(app) as client:
        res_started = client.get("/is-started")
        assert res_started.status_code == 200
        assert "is_started" in res_started.json()

        res_on = client.get("/is-on")
        assert res_on.status_code == 200
        assert "is_on" in res_on.json()


def test_rest_api_send_command_when_offline():
    # 로컬 요청 시 정상 전달 및 처리
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        res = client.post("/send-command", json={"command": "list"})
        assert res.status_code == 200
        assert res.json() == {"message": "Server is not running"}

    # 외부 요청 시 차단
    with TestClient(app, client=("192.168.0.50", 50000)) as client:
        res = client.post("/send-command", json={"command": "list"})
        assert res.status_code == 200
        data = res.json()
        assert data.get("status") is False
        assert "관리자(로컬) 전용" in data.get("message", "")


def test_rest_api_console_output():
    # 로컬 요청 시 정상 응답
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        res = client.post("/get-console-output", json={"startline": 0})
        assert res.status_code == 200
        assert "console_output" in res.json()

    # 외부 요청 시 차단
    with TestClient(app, client=("192.168.0.50", 50000)) as client:
        res = client.post("/get-console-output", json={"startline": 0})
        assert res.status_code == 200
        data = res.json()
        assert data.get("status") is False
        assert "관리자(로컬) 전용" in data.get("message", "")


def test_rest_api_statistics():
    # 로컬 요청 시 정상 반환
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        res = client.get("/statistics")
        assert res.status_code == 200
        data = res.json()
        assert "stats" in data
        assert "recent_events" in data
        assert "peak_players" in data["stats"]

    # 외부 요청 시 차단
    with TestClient(app, client=("192.168.0.50", 50000)) as client:
        res = client.get("/statistics")
        assert res.status_code == 200
        data = res.json()
        assert data.get("status") is False
        assert "관리자(로컬) 전용" in data.get("message", "")


def test_rest_api_stop_server_remote_blocked_when_players_online(monkeypatch):
    from src.util import server_status_cache
    # 1. 원격 클라이언트 (외부 IP: 192.168.0.50 등) 요청 시 차단
    with TestClient(app, client=("192.168.0.50", 50000)) as client:
        monkeypatch.setattr(server_status_cache, "player_count", 3)
        res = client.post("/stop-server")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] is False
        assert "플레이 중이므로" in data["message"]

    # 2. 로컬호스트 (호스트 GUI 등 127.0.0.1) 요청 시에는 차단되지 않고 정상 진행
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        monkeypatch.setattr(server_status_cache, "player_count", 3)
        res = client.post("/stop-server")
        assert res.status_code == 200
        data = res.json()
        # 서버가 꺼져 있을 때는 stop()의 기본 반환 ("Server is not running")
        assert data.get("message") == "Server is not running"
