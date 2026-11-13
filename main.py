from PyQt6.QtWidgets import QApplication
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
import logging

from src.router import server_manager, websocket_router
from src.gui import OpenServerWidget
from src.util.log_filter import EndpointFilter
import sys

from src.util import monitor_minecraft_server

# 2초마다 발생하는 /is-started, /is-on 등의 단순 폴링 로그를 uvicorn 콘솔에서 숨김
logging.getLogger("uvicorn.access").addFilter(
    EndpointFilter(excluded_paths=["/is-started", "/is-on", "/ping"])
)

NO_GUI = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[System] FastAPI 가동 - 마인크래프트")
    monitor_task = asyncio.create_task(monitor_minecraft_server())
    yield

    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        print("[System] 모니터링 태스크가 안전하게 종료되었습니다.")

app = FastAPI(
    title="Minecraft Server Controller",
    lifespan=lifespan,
)
app.mount("/server", StaticFiles(directory="src/templates", html=True), name="templates")

app.include_router(server_manager.router)
app.include_router(websocket_router)

@app.get("/ping")
async def ping():
    return {"message": "pong!"}

@app.get("/")
async def root():
    return {"message": "마인크래프트 웹 패널 API 서버가 정상 구동 중입니다."}

def main():
    if NO_GUI:
        return
    app = QApplication(sys.argv)
    wg = OpenServerWidget()
    wg.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
