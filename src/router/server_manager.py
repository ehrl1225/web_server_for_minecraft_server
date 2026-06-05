from fastapi import FastAPI, APIRouter, Request
from fastapi.templating import Jinja2Templates
import subprocess
from src.models import Command, ReadLine
import os
from starlette.responses import HTMLResponse
from src.util import ServerData

server_process: None | subprocess.Popen = None

router = APIRouter()
api = FastAPI()

templates = Jinja2Templates(directory="src/templates")

server_data = ServerData()

@router.get("/server", response_class=HTMLResponse)
async def server(request: Request):
    return templates.TemplateResponse("server.html", {"request": request})

@router.get("/server/is-started")
async def is_started():
    global server_data
    return server_data.is_started()

@router.get("/server/is-on")
async def is_on():
    global server_data
    return server_data.is_on()

@router.post("/server/start-server")
async def start_server():
    global server_data
    return server_data.start()

@router.post("/server/stop-server")
async def stop_server():
    global server_data
    return server_data.stop()

@router.post("/server/get-console-output")
async def get_console_output(readline: ReadLine):
    global server_data
    return server_data.get_console_output(readline.startline)

@router.post("/server/send-command")
async def communicate(command: Command):
    global server_data
    return server_data.send_command(command.command)