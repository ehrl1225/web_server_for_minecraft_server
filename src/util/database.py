import asyncio
import os
import psutil
from mcstatus import JavaServer
from .server_status import ServerStatus
from .config import load_config
from .stats_tracker import stats_tracker

server_status_cache: ServerStatus = ServerStatus()


def _get_server_properties(server_file_path: str | None) -> dict:
    """마인크래프트 서버 폴더의 server.properties 파싱"""
    result = {
        "server-port": 25565,
        "enable-query": False,
        "query.port": 25565
    }
    if not server_file_path:
        return result
    server_dir = os.path.dirname(server_file_path)
    props_path = os.path.join(server_dir, "server.properties")
    if os.path.exists(props_path):
        try:
            with open(props_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip()
                    if k == "server-port":
                        try:
                            result["server-port"] = int(v)
                        except ValueError:
                            pass
                    elif k == "enable-query":
                        result["enable-query"] = (v.lower() == "true")
                    elif k == "query.port":
                        try:
                            result["query.port"] = int(v)
                        except ValueError:
                            pass
        except Exception:
            pass
    return result


def _get_server_port_from_properties(server_file_path: str | None) -> int:
    """마인크래프트 서버 폴더의 server.properties에서 server-port를 추출 (기본 25565)"""
    return _get_server_properties(server_file_path)["server-port"]


def _calc_process_ram_gb(proc) -> float:
    """마인크래프트 프로세스 및 자식 Java 프로세스들의 총 물리 메모리(RSS) 합산 (GB 단위)"""
    if proc is None or proc.poll() is not None:
        return 0.0
    try:
        parent = psutil.Process(proc.pid)
        total_rss = parent.memory_info().rss
        for child in parent.children(recursive=True):
            try:
                total_rss += child.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return round(total_rss / (1024 ** 3), 2)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0.0


async def monitor_minecraft_server():
    """마인크래프트 서버 상태, 접속자 수, RAM 사용량 및 빈 서버 자동 종료(Auto-Stop)를 관리하는 태스크"""
    from src.router import server_data

    ping_fail_count = 0
    tick_count = 0
    was_online = False
    known_online_players: set[str] = set()

    while True:
        try:
            # 설정 파일에서 최신 auto_stop 설정 동기화
            cfg = load_config()
            server_status_cache.auto_stop_enabled = cfg.get("auto_stop_enabled", True)
            server_status_cache.auto_stop_timeout_minutes = cfg.get("auto_stop_timeout_minutes", 10)

            started = server_data.is_started()["is_started"]
            if not started:
                if was_online:
                    for p in known_online_players:
                        stats_tracker.record_player_leave(p, 0)
                    known_online_players.clear()
                    was_online = False
                server_status_cache.is_starting = False
                server_status_cache.is_online = False
                server_status_cache.is_stopping = False
                server_status_cache.player_count = 0
                server_status_cache.ram_usage_gb = 0.0
                server_status_cache.empty_seconds = 0
                ping_fail_count = 0
            else:
                # 2초마다 RAM 사용량 갱신
                if tick_count % 2 == 0:
                    server_status_cache.ram_usage_gb = _calc_process_ram_gb(server_data.server_process)

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
                        if not was_online:
                            was_online = True
                            stats_tracker.record_mc_online()

                        server_status_cache.is_starting = False
                        server_status_cache.is_online = True
                        server_status_cache.is_stopping = False

                        # 2. 2초마다 mcstatus로 실시간 핑 및 접속자 수 조회
                        if tick_count % 2 == 0:
                            props = _get_server_properties(server_data.server_file_path)
                            port = props["server-port"]
                            query_enabled = props["enable-query"]
                            query_port = props.get("query.port", port)
                            server_status_cache.query_enabled = query_enabled

                            try:
                                server = await JavaServer.async_lookup(f"127.0.0.1:{port}", timeout=1.8)
                                status = await server.async_status()
                                server_status_cache.player_count = status.players.online
                                server_status_cache.max_players = status.players.max
                                ping_fail_count = 0

                                # 쿼리 기능(enable-query=true)이 켜진 경우에만 정확한 전체 플레이어 목록 추적
                                if query_enabled:
                                    try:
                                        # query_port로 쿼리 요청
                                        query_server = JavaServer("127.0.0.1", port=port, query_port=query_port)
                                        query_res = await query_server.async_query(tries=1)
                                        current_players = set()
                                        if query_res.players and query_res.players.list:
                                            for name in query_res.players.list:
                                                if name and name.strip():
                                                    current_players.add(name.strip())

                                        joined = current_players - known_online_players
                                        left = known_online_players - current_players

                                        for p in joined:
                                            stats_tracker.record_player_join(p, server_status_cache.player_count)
                                        for p in left:
                                            stats_tracker.record_player_leave(p, server_status_cache.player_count)

                                        known_online_players = current_players
                                    except Exception:
                                        # 쿼리 패킷 일시적 유실 시 기존 목록 유지
                                        pass
                                else:
                                    # enable-query가 꺼진 경우 추적하지 않고 목록 초기화
                                    known_online_players.clear()

                            except Exception:
                                ping_fail_count += 1
                                if ping_fail_count > 3:
                                    server_status_cache.player_count = 0
                                    for p in known_online_players:
                                        stats_tracker.record_player_leave(p, 0)
                                    known_online_players.clear()

                        # 3. 빈 서버 자동 종료 카운터: 매 1초마다 정확히 1초씩 누적
                        if server_status_cache.player_count == 0:
                            server_status_cache.empty_seconds += 1
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

            tick_count += 1
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(1)
