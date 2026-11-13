
class ServerStatus:

    is_starting: bool = False
    is_online: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "is_starting": self.is_starting,
            "is_online": self.is_online,
        }

    def equal_to_dict(self, other: dict[str, bool]) -> bool:
        pass

