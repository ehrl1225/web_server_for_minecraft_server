import subprocess
import os

log_path = "src/log/console_output.log"
server_file_path_txt = "src/server_file_path.txt"

# 로그 디렉터리 존재 보장
os.makedirs(os.path.dirname(log_path), exist_ok=True)


class ServerData:
    def __init__(self):
        self.server_file_path = None
        self.port = None
        self.server_process = None

    def set_server_file_path(self, file_path):
        if self.__is_started():
            return
        print(f"setting server path {file_path}")
        self.server_file_path = file_path

    def save_server_file_path(self):
        with open(server_file_path_txt, "w", encoding="utf-8") as f:
            f.write(self.server_file_path)

    def load_server_file_path(self):
        if os.path.exists(server_file_path_txt):
            with open(server_file_path_txt, "r", encoding="utf-8") as f:
                self.server_file_path = f.read().strip()
            return True
        return False

    def set_port(self, port):
        if self.__is_started():
            return
        self.port = port

    def __is_started(self) -> bool:
        if self.server_process is None:
            return False
        if self.server_process.poll() is None:
            return True
        return False

    def is_started(self) -> dict[str, bool]:
        return {"is_started": self.__is_started()}

    def is_on(self) -> dict[str, bool]:
        if not self.__is_started():
            return {"is_on": False}
        if not os.path.exists(log_path):
            return {"is_on": False}
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as file:
                output = file.readlines()
                for line in output[::-1]:
                    if "Dedicated server took" in line or "Done (" in line:
                        return {"is_on": True}
        except Exception:
            return {"is_on": False}
        return {"is_on": False}

    def start(self) -> dict[str, str]:
        if not self.__is_started():
            self.load_server_file_path()
            path = self.server_file_path
            if not path or not os.path.exists(path):
                return {"error": "Server executable path not found"}
            print(f"Starting server: {path}")
            # 로그 파일 초기화 또는 생성
            with open(log_path, "w", encoding="utf-8") as log_file:
                log_file.write("[System] Server process initiating...\n")

            log_file_append = open(log_path, "a", encoding="utf-8", buffering=1)
            self.server_process = subprocess.Popen(
                f'"{path}"',
                stdin=subprocess.PIPE,
                stdout=log_file_append,
                stderr=log_file_append,
                shell=True,
                text=True,
                cwd=os.path.dirname(path)
            )
            return {"message": "Server started"}
        return {"message": "Server is already running"}

    def stop(self) -> dict[str, str]:
        if self.__is_started():
            try:
                proc = self.server_process
                if proc.stdin:
                    proc.stdin.write("stop\n")
                    proc.stdin.flush()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    proc.wait(timeout=5)
                self.server_process = None
                return {"message": "Server stopped"}
            except Exception as e:
                if self.server_process:
                    self.server_process.kill()
                    self.server_process = None
                return {"error": str(e)}
        return {"message": "Server is not running"}

    def get_console_output(self, startline: int) -> dict[str, list[str] | str]:
        try:
            if not os.path.exists(log_path):
                return {"console_output": []}
            with open(log_path, "r", encoding="utf-8", errors="replace") as file:
                output = file.readlines()
            return {"console_output": output[startline:]}
        except Exception as e:
            return {"error": str(e)}

    def send_command(self, command) -> dict[str, str]:
        if self.__is_started():
            try:
                cmd_str = command if isinstance(command, str) else getattr(command, "command", str(command))
                proc = self.server_process
                if proc.stdin:
                    proc.stdin.write(f"{cmd_str}\n")
                    proc.stdin.flush()
                return {"message": "sent"}
            except Exception as e:
                return {"error": str(e)}
        else:
            return {"message": "Server is not running"}
