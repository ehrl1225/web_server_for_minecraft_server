import asyncio
import os
from mcstatus import JavaServer
from .server_status import ServerStatus

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
    """마인크래프트 서버 상태 및 접속자 수를 주기적으로 감시하고 server_status_cache를 업데이트하는 태스크"""
    from src.router import server_data

    ping_fail_count = 0

    while True:
        try:
            started = server_data.is_started()["is_started"]
            if not started:
                server_status_cache.is_starting = False
                server_status_cache.is_online = False
                server_status_cache.player_count = 0
                ping_fail_count = 0
            else:
                # 1. 프로세스 및 로그 기반 상태 확인
                is_on = server_data.is_on()["is_on"]
                if is_on:
                    server_status_cache.is_starting = False
                    server_status_cache.is_online = True

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
                        # 핑 실패가 누적되면 (예: 5초 이상 응답 없을 때)
                        if ping_fail_count > 3:
                            server_status_cache.player_count = 0
                else:
                    server_status_cache.is_starting = True
                    server_status_cache.is_online = False
                    server_status_cache.player_count = 0

            await asyncio.sleep(2)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(2)
