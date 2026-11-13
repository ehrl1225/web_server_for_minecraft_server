from enum import Enum

class MessageType(Enum):
    ERROR = "error"
    STATUS = "status"
    LOG = "log"