from PyQt6.QtWidgets import QApplication
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio

from src.router import server_manager, websocket_router
from src.gui import OpenServerWidget
import sys

from src.util import monitor_minecraft_server

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
    return {"message":"마인크래프트 웹 패널 API 서버가 정상 구동 중입니다."}

def main():
    if NO_GUI:
        # import uvicorn
        # from src.router import server_data
        # server_data.set_server_file_path("../atm9/startserver.bat")
        # uvicorn.run("src.main:app", host='0.0.0.0', port=9000, reload=True)
        return
    app = QApplication(sys.argv)
    wg = OpenServerWidget()
    wg.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
