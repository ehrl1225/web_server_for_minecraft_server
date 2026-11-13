class ServerStatus:
    is_starting: bool = False
    is_online: bool = False
    player_count: int = 0
    max_players: int = 20
    ram_usage_gb: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_starting": self.is_starting,
            "is_online": self.is_online,
            "player_count": self.player_count,
            "max_players": self.max_players,
            "ram_usage_gb": self.ram_usage_gb,
        }

    def equal_to_dict(self, other: dict) -> bool:
        return self.to_dict() == other
