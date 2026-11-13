import os
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.util import server_status_cache, MessageType

router = APIRouter(
    prefix="/ws",
    tags=["Realtime WebSocket"]
)

async def read_stdout(process):
    server_status_cache.is_starting = True


@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    log_file_path = ""

    await websocket.send_json({
        "type": MessageType.STATUS.value,
        "data": server_status_cache
    })

    async def stream_logs():
        if not os.path.exists(log_file_path):
            await websocket.send_json({
                "type": MessageType.ERROR.value,
                "data": "로그 파일을 찾을 수 없습니다."
            })
            return

        with open(log_file_path, "r", encoding="utf-8") as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if not line:
                    await asyncio.sleep(0.2)
                    continue
                await websocket.send_json({
                    "type": MessageType.LOG.value,
                    "data": line.strip()
                })

    async def stream_status():
        last_status = {}
        while True:
            if last_status != server_status_cache:
                await websocket.send_json({
                    "type": MessageType.STATUS.value,
                    "data": ""
                })
            await asyncio.sleep(2)

    try:
        await asyncio.gather(stream_logs(), stream_status())

    except WebSocketDisconnect:
        print("통합 웹소켓 클라이언트 연결 종료")
    except Exception as e:
        print(f"웹소켓 에러 발생: {e}")
    
