from fastapi import APIRouter, Request
import subprocess

from src.models import Command, ReadLine
from src.util import ServerData, server_status_cache, stats_tracker

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
async def stop_server(request: Request):
    global server_data
    # 요청 IP 확인: 로컬(GUI 호스트 관리자)인지 확인
    client_host = request.client.host if request.client else ""
    is_localhost = client_host in ("127.0.0.1", "localhost", "::1", "testclient")

    # 외부(웹 등)에서 요청했고 플레이어가 1명 이상 접속해 있는 경우 종료 차단
    if not is_localhost and server_status_cache.player_count > 0:
        return {
            "status": False,
            "message": f"현재 {server_status_cache.player_count}명이 플레이 중이므로 서버를 종료할 수 없습니다."
        }

    return server_data.stop()


@router.post("/get-console-output")
async def get_console_output(readline: ReadLine):
    global server_data
    return server_data.get_console_output(readline.startline)


@router.post("/send-command")
async def communicate(command: Command):
    global server_data
    return server_data.send_command(command.command)


@router.get("/statistics")
async def get_statistics():
    """서버 수명주기 및 플레이어 통계, 최근 이벤트 히스토리 반환"""
    data = stats_tracker.get_summary()
    data["query_enabled"] = server_status_cache.query_enabled
    return data
