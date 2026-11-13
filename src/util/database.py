import asyncio
import os
from .server_status import ServerStatus

server_status_cache: ServerStatus = ServerStatus()


async def monitor_minecraft_server():
    """마인크래프트 서버 상태를 주기적으로 감시하고 server_status_cache를 업데이트하는 백그라운드 태스크"""
    # 순환 참조 방지를 위해 함수 내부에서 import
    from src.router import server_data

    log_path = "src/log/console_output.log"

    while True:
        try:
            started = server_data.is_started()["is_started"]
            if not started:
                server_status_cache.is_starting = False
                server_status_cache.is_online = False
                server_status_cache.player_count = 0
                server_status_cache.ram_usage_gb = 0.0
            else:
                is_on = server_data.is_on()["is_on"]
                if is_on:
                    server_status_cache.is_starting = False
                    server_status_cache.is_online = True
                else:
                    server_status_cache.is_starting = True
                    server_status_cache.is_online = False

            await asyncio.sleep(1)
        except asyncio.CancelledError:
            break
        except Exception as e:
            await asyncio.sleep(1)
