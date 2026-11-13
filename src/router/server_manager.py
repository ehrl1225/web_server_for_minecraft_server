from fastapi import APIRouter
import subprocess

from src.models import Command, ReadLine
from src.util import ServerData, server_status_cache

server_process: None | subprocess.Popen = None

router = APIRouter()

server_data = ServerData()


@router.get("/status")
async def get_server_status():
    """마인크래프트 서버의 전체 실시간 상태(접속자 수, 램 사용량, On/Off, 자동종료 등) 반환"""
    global server_data
    status_dict = server_status_cache.to_dict()
    # 프로세스 실제 가동 여부도 보정
    status_dict["is_started"] = server_data.is_started()["is_started"]
    return status_dict


@router.get("/is-started")
async def is_started():
    global server_data
    return server_data.is_started()


@router.get("/is-on")
async def is_on():
    global server_data
    return server_data.is_on()


@router.post("/start-server")
async def start_server():
    global server_data
    return server_data.start()


@router.post("/stop-server")
async def stop_server():
    global server_data
    return server_data.stop()


@router.post("/get-console-output")
async def get_console_output(readline: ReadLine):
    global server_data
    return server_data.get_console_output(readline.startline)


@router.post("/send-command")
async def communicate(command: Command):
    global server_data
    return server_data.send_command(command.command)
