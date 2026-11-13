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
    with TestClient(app) as client:
        res = client.post("/send-command", json={"command": "list"})
        assert res.status_code == 200
        assert res.json() == {"message": "Server is not running"}


def test_rest_api_console_output():
    with TestClient(app) as client:
        res = client.post("/get-console-output", json={"startline": 0})
        assert res.status_code == 200
        assert "console_output" in res.json()
