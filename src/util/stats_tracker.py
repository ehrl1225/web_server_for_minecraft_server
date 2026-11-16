import os
import json
from datetime import datetime

LOG_DIR = "src/log"
EVENT_LOG_PATH = os.path.join(LOG_DIR, "server_events.log")
STATS_PATH = os.path.join(LOG_DIR, "stats.json")

os.makedirs(LOG_DIR, exist_ok=True)


class StatsTracker:
    def __init__(self):
        self.stats = {
            "web_start_time": None,
            "web_stop_time": None,
            "web_uptime_seconds": 0,
            "mc_start_time": None,
            "mc_stop_time": None,
            "mc_run_count": 0,
            "mc_total_uptime_seconds": 0,
            "peak_players": 0,
            "unique_players": [],
            "player_session_counts": {},
        }
        self.load_stats()

    def load_stats(self):
        if os.path.exists(STATS_PATH):
            try:
                with open(STATS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.stats.update(data)
            except Exception:
                pass

    def save_stats(self):
        try:
            with open(STATS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def log_event(self, category: str, message: str):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{now_str}] [{category}] {message}\n"
        try:
            with open(EVENT_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception:
            pass

    # 1. 웹서버 이벤트
    def record_web_start(self, port: int):
        now = datetime.now()
        self.stats["web_start_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
        self.save_stats()
        self.log_event("WEB", f"웹서버 시작됨 (포트: {port})")

    def record_web_stop(self):
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        self.stats["web_stop_time"] = now_str
        if self.stats["web_start_time"]:
            try:
                start_dt = datetime.strptime(self.stats["web_start_time"], "%Y-%m-%d %H:%M:%S")
                duration = int((now - start_dt).total_seconds())
                self.stats["web_uptime_seconds"] += max(0, duration)
                m, s = divmod(duration, 60)
                h, m = divmod(m, 60)
                dur_str = f"{h}시간 {m}분 {s}초" if h else f"{m}분 {s}초"
                self.log_event("WEB", f"웹서버 종료됨 (가동 시간: {dur_str})")
            except Exception:
                self.log_event("WEB", "웹서버 종료됨")
        else:
            self.log_event("WEB", "웹서버 종료됨")
        self.save_stats()

    # 2. 마인크래프트 서버 이벤트
    def record_mc_start(self):
        now = datetime.now()
        self.stats["mc_start_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
        self.stats["mc_run_count"] += 1
        self.save_stats()
        self.log_event("MC", "마인크래프트 서버 프로세스 가동")

    def record_mc_online(self):
        self.log_event("MC", "마인크래프트 서버 부팅 완료 (온라인)")

    def record_mc_stop(self):
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        self.stats["mc_stop_time"] = now_str
        if self.stats["mc_start_time"]:
            try:
                start_dt = datetime.strptime(self.stats["mc_start_time"], "%Y-%m-%d %H:%M:%S")
                duration = int((now - start_dt).total_seconds())
                self.stats["mc_total_uptime_seconds"] += max(0, duration)
                m, s = divmod(duration, 60)
                h, m = divmod(m, 60)
                dur_str = f"{h}시간 {m}분 {s}초" if h else f"{m}분 {s}초"
                self.log_event("MC", f"마인크래프트 서버 종료됨 (구동 시간: {dur_str})")
            except Exception:
                self.log_event("MC", "마인크래프트 서버 종료됨")
        else:
            self.log_event("MC", "마인크래프트 서버 종료됨")
        self.save_stats()

    # 3. 플레이어 이벤트
    def record_player_join(self, player_name: str, current_count: int):
        if not player_name:
            return
        player_name = player_name.strip()
        if player_name not in self.stats["unique_players"]:
            self.stats["unique_players"].append(player_name)
        counts = self.stats["player_session_counts"].get(player_name, 0)
        self.stats["player_session_counts"][player_name] = counts + 1

        if current_count > self.stats["peak_players"]:
            self.stats["peak_players"] = current_count

        self.save_stats()
        self.log_event("PLAYER", f"플레이어 접속: {player_name} (현재 {current_count}명)")

    def record_player_leave(self, player_name: str, current_count: int):
        if not player_name:
            return
        player_name = player_name.strip()
        self.log_event("PLAYER", f"플레이어 퇴장: {player_name} (현재 {current_count}명)")

    def get_recent_events(self, count: int = 25) -> list[str]:
        if not os.path.exists(EVENT_LOG_PATH):
            return []
        try:
            with open(EVENT_LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                return [line.strip() for line in lines[-count:]]
        except Exception:
            return []

    def get_summary(self) -> dict:
        self.load_stats()
        return {
            "stats": self.stats,
            "recent_events": self.get_recent_events(25)
        }


stats_tracker = StatsTracker()
