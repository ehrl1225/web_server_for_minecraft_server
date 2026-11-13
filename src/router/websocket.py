import os
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.util import server_status_cache, MessageType
from src.util.server_data import log_path

router = APIRouter(
    prefix="/ws",
    tags=["Realtime WebSocket"]
)


@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    from src.router import server_data

    await websocket.accept()

    # 연결 즉시 현재 상태 전송
    await websocket.send_json({
        "type": MessageType.STATUS.value,
        "data": server_status_cache.to_dict()
    })

    # 기존 최근 로그 전송 (최대 50줄)
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                recent_lines = lines[-50:] if len(lines) > 50 else lines
                for line in recent_lines:
                    await websocket.send_json({
                        "type": MessageType.LOG.value,
                        "data": line.strip()
                    })
        except Exception:
            pass

    async def stream_logs():
        """실시간 로그 파일 추적 및 클라이언트 전송"""
        last_pos = 0
        if os.path.exists(log_path):
            last_pos = os.path.getsize(log_path)

        while True:
            await asyncio.sleep(0.3)
            if not os.path.exists(log_path):
                continue

            current_size = os.path.getsize(log_path)
            if current_size < last_pos:
                last_pos = 0

            if current_size > last_pos:
                try:
                    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                        f.seek(last_pos)
                        new_content = f.read()
                        last_pos = f.tell()
                        for line in new_content.splitlines():
                            if line.strip():
                                await websocket.send_json({
                                    "type": MessageType.LOG.value,
                                    "data": line.strip()
                                })
                except Exception:
                    pass

    async def stream_status():
        """서버 상태 변경 감지 및 브로드캐스트"""
        last_status = {}
        while True:
            current_status = server_status_cache.to_dict()
            if last_status != current_status:
                await websocket.send_json({
                    "type": MessageType.STATUS.value,
                    "data": current_status
                })
                last_status = current_status.copy()
            await asyncio.sleep(1)

    async def receive_commands():
        """클라이언트로부터의 웹소켓 제어 및 명령어 수신"""
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            if action == "start":
                server_data.start()
                server_status_cache.is_starting = True
                await websocket.send_json({
                    "type": MessageType.STATUS.value,
                    "data": server_status_cache.to_dict()
                })
            elif action == "stop":
                server_data.stop()
                server_status_cache.is_starting = False
                server_status_cache.is_online = False
                server_status_cache.empty_seconds = 0
                await websocket.send_json({
                    "type": MessageType.STATUS.value,
                    "data": server_status_cache.to_dict()
                })
            elif action == "command":
                cmd = data.get("data", "")
                if cmd:
                    server_data.send_command(cmd)
            elif action == "set_auto_stop":
                # 자동 종료 설정 업데이트 (enabled, timeout_minutes)
                enabled = data.get("enabled")
                timeout = data.get("timeout_minutes")
                if enabled is not None:
                    server_status_cache.auto_stop_enabled = bool(enabled)
                if timeout is not None:
                    server_status_cache.auto_stop_timeout_minutes = max(1, int(timeout))
                await websocket.send_json({
                    "type": MessageType.STATUS.value,
                    "data": server_status_cache.to_dict()
                })

    try:
        await asyncio.gather(stream_logs(), stream_status(), receive_commands())
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WebSocket] 에러 발생: {e}")
