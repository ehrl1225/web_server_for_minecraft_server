from pathlib import Path
from PyQt6.QtWidgets import QApplication
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
import logging
import multiprocessing
import sys
import uvicorn

from src.router import server_manager, websocket_router
from src.gui import OpenServerWidget
from src.util.log_filter import EndpointFilter
from src.util import monitor_minecraft_server, stats_tracker

# 2초마다 발생하는 GUI 폴링 로그(/status, /is-started, /is-on, /get-console-output 등)를 uvicorn 콘솔에서 숨김
logging.getLogger("uvicorn.access").addFilter(
    EndpointFilter(excluded_paths=["/status", "/is-started", "/is-on", "/get-console-output", "/ping", "/statistics"])
)

NO_GUI = False


def get_base_dir() -> Path:
    """PyInstaller 번들 실행 환경 또는 일반 파이썬 실행 환경의 베이스 디렉터리 반환"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[System] FastAPI 가동 - 마인크래프트")
    port = 9000
    for arg in sys.argv:
        if arg.startswith("--port="):
            try:
                port = int(arg.split("=")[1])
            except ValueError:
                pass
    stats_tracker.record_web_start(port)
    monitor_task = asyncio.create_task(monitor_minecraft_server())
    yield

    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        print("[System] 모니터링 태스크가 안전하게 종료되었습니다.")
    stats_tracker.record_web_stop()

app = FastAPI(
    title="Minecraft Server Controller",
    lifespan=lifespan,
)

templates_dir = get_base_dir() / "src" / "templates"
app.mount("/server", StaticFiles(directory=str(templates_dir), html=True), name="templates")

app.include_router(server_manager.router)
app.include_router(websocket_router)

@app.get("/ping")
async def ping():
    return {"message": "pong!"}

@app.get("/")
async def root():
    return {"message": "마인크래프트 웹 패널 API 서버가 정상 구동 중입니다."}

def run_uvicorn_server(port: int):
    """서브프로세스에서 실행되는 Uvicorn 엔트리포인트"""
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )

def main():
    if "--serve" in sys.argv:
        port = 9000
        for arg in sys.argv:
            if arg.startswith("--port="):
                try:
                    port = int(arg.split("=")[1])
                except ValueError:
                    pass
        run_uvicorn_server(port)
        return

    if NO_GUI:
        return
    app = QApplication(sys.argv)
    wg = OpenServerWidget()
    wg.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()

