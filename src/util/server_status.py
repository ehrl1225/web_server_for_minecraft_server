from .config import load_config


class ServerStatus:
    is_starting: bool = False
    is_online: bool = False
    is_stopping: bool = False
    player_count: int = 0
    max_players: int = 20
    ram_usage_gb: float = 0.0

    def __init__(self):
        cfg = load_config()
        self.auto_stop_enabled: bool = cfg.get("auto_stop_enabled", True)
        self.auto_stop_timeout_minutes: int = cfg.get("auto_stop_timeout_minutes", 10)
        self.empty_seconds: int = 0  # 플레이어가 0명인 지속 시간(초)

    def to_dict(self) -> dict:
        remaining = 0
        if self.auto_stop_enabled and self.is_online and self.player_count == 0 and not self.is_stopping:
            remaining = max(0, (self.auto_stop_timeout_minutes * 60) - self.empty_seconds)

        return {
            "is_starting": self.is_starting,
            "is_online": self.is_online,
            "is_stopping": self.is_stopping,
            "player_count": self.player_count,
            "max_players": self.max_players,
            "ram_usage_gb": self.ram_usage_gb,
            "auto_stop_enabled": self.auto_stop_enabled,
            "auto_stop_timeout_minutes": self.auto_stop_timeout_minutes,
            "empty_seconds": self.empty_seconds,
            "auto_stop_remaining_seconds": remaining,
        }

    def equal_to_dict(self, other: dict) -> bool:
        return self.to_dict() == other
