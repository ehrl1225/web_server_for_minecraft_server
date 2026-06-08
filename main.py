from PyQt6.QtWidgets import QApplication
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from src.router import server_manager
from src.gui import OpenServerWidget
import sys

NO_GUI = False

app = FastAPI()
app.mount("/server", StaticFiles(directory="src/templates", html=True), name="templates")

app.include_router(server_manager.router)

@app.get("/ping")
async def ping():
    return {"message": "pong!"}

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
