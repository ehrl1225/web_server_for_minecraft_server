import asyncio
import os
from mcstatus import JavaServer
from .server_status import ServerStatus
from .config import load_config

server_status_cache: ServerStatus = ServerStatus()


def _get_server_port_from_properties(server_file_path: str | None) -> int:
    """마인크래프트 서버 폴더의 server.properties에서 server-port를 추출 (기본 25565)"""
    if not server_file_path:
        return 25565
    server_dir = os.path.dirname(server_file_path)
    props_path = os.path.join(server_dir, "server.properties")
    if os.path.exists(props_path):
        try:
            with open(props_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.strip().startswith("server-port="):
                        return int(line.strip().split("=")[1])
        except Exception:
            pass
    return 25565


async def monitor_minecraft_server():
    """마인크래프트 서버 상태, 접속자 수 및 빈 서버 자동 종료(Auto-Stop)를 관리하는 태스크"""
    from src.router import server_data

    ping_fail_count = 0
    poll_interval = 2  # 주기(초)

    while True:
        try:
            # 설정 파일에서 최신 auto_stop 설정 동기화
            cfg = load_config()
            server_status_cache.auto_stop_enabled = cfg.get("auto_stop_enabled", True)
            server_status_cache.auto_stop_timeout_minutes = cfg.get("auto_stop_timeout_minutes", 10)

            started = server_data.is_started()["is_started"]
            if not started:
                server_status_cache.is_starting = False
                server_status_cache.is_online = False
                server_status_cache.is_stopping = False
                server_status_cache.player_count = 0
                server_status_cache.empty_seconds = 0
                ping_fail_count = 0
            else:
                # 종료 진행 중인 경우
                if getattr(server_data, "is_stopping", False):
                    server_status_cache.is_starting = False
                    server_status_cache.is_online = False
                    server_status_cache.is_stopping = True
                    server_status_cache.player_count = 0
                    server_status_cache.empty_seconds = 0
                else:
                    # 1. 프로세스 및 로그 기반 상태 확인
                    is_on = server_data.is_on()["is_on"]
                    if is_on:
                        server_status_cache.is_starting = False
                        server_status_cache.is_online = True
                        server_status_cache.is_stopping = False

                        # 2. 온라인 상태일 때 mcstatus로 실시간 핑 및 접속자 수 조회
                        port = _get_server_port_from_properties(server_data.server_file_path)
                        try:
                            server = await JavaServer.async_lookup(f"127.0.0.1:{port}", timeout=2.0)
                            status = await server.async_status()
                            server_status_cache.player_count = status.players.online
                            server_status_cache.max_players = status.players.max
                            ping_fail_count = 0
                        except Exception:
                            ping_fail_count += 1
                            if ping_fail_count > 3:
                                server_status_cache.player_count = 0

                        # 3. 빈 서버 자동 종료(Auto-Stop) 검사
                        if server_status_cache.player_count == 0:
                            server_status_cache.empty_seconds += poll_interval
                            timeout_seconds = server_status_cache.auto_stop_timeout_minutes * 60

                            if (
                                server_status_cache.auto_stop_enabled
                                and server_status_cache.empty_seconds >= timeout_seconds
                            ):
                                print(
                                    f"[Auto-Stop] 플레이어가 {server_status_cache.auto_stop_timeout_minutes}분 동안 0명이어서 마인크래프트 서버를 안전하게 종료합니다."
                                )
                                server_data.stop()
                                server_status_cache.is_stopping = True
                                server_status_cache.is_online = False
                                server_status_cache.empty_seconds = 0
                        else:
                            server_status_cache.empty_seconds = 0
                    else:
                        server_status_cache.is_starting = True
                        server_status_cache.is_online = False
                        server_status_cache.is_stopping = False
                        server_status_cache.player_count = 0
                        server_status_cache.empty_seconds = 0

            await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(poll_interval)
