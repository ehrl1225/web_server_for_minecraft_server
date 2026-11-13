import logging

class EndpointFilter(logging.Filter):
    """지정된 엔드포인트(헬스체크, 폴링 등)에 대한 uvicorn 액세스 로그를 숨기는 필터"""
    def __init__(self, excluded_paths: list[str]):
        super().__init__()
        self.excluded_paths = excluded_paths

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return not any(path in message for path in self.excluded_paths)
