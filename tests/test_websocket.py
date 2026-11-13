import pytest
from starlette.testclient import TestClient
from main import app
from src.util import server_status_cache, MessageType


def test_websocket_stream_connect_and_status():
    with TestClient(app) as client:
        with client.websocket_connect("/ws/stream") as websocket:
            # 첫 번째 메시지로 현재 상태를 수신해야 함
            data = websocket.receive_json()
            assert data["type"] == MessageType.STATUS.value
            assert "is_starting" in data["data"]
            assert "is_online" in data["data"]


def test_websocket_stream_send_command():
    with TestClient(app) as client:
        with client.websocket_connect("/ws/stream") as websocket:
            init_msg = websocket.receive_json()
            assert init_msg["type"] == MessageType.STATUS.value

            # 클라이언트 -> 서버 명령 전송 테스트
            websocket.send_json({"action": "command", "data": "help"})
            # 서버가 오프라인 상태일 때는 별도 에러 없이 stdin 무시 처리됨
