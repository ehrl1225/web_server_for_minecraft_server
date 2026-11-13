import subprocess
import os
import threading

log_path = "src/log/console_output.log"
server_file_path_txt = "src/server_file_path.txt"

# 로그 디렉터리 존재 보장
os.makedirs(os.path.dirname(log_path), exist_ok=True)


class ServerData:
    def __init__(self):
        self.server_file_path = None
        self.port = None
        self.server_process = None
        self.is_stopping: bool = False

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
        # 프로세스가 이미 종료된 경우 정리
        self.server_process = None
        self.is_stopping = False
        return False

    def is_started(self) -> dict[str, bool]:
        return {"is_started": self.__is_started()}

    def is_on(self) -> dict[str, bool]:
        if not self.__is_started() or self.is_stopping:
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
            self.is_stopping = False
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
        """마인크래프트 서버 표준 입력에 stop 명령어를 보내 맵과 데이터를 안전하게 저장하고 자연 종료될 때까지 대기"""
        if self.__is_started():
            if self.is_stopping:
                return {"message": "Server is already stopping gracefully"}

            try:
                proc = self.server_process
                self.is_stopping = True

                # 마인크래프트 표준 입력으로 stop 명령어 전송
                if proc.stdin:
                    proc.stdin.write("stop\n")
                    proc.stdin.flush()

                # 비동기 백그라운드 스레드에서 서버가 맵 저장 및 정상 종료할 때까지 충분히 대기
                def wait_graceful_shutdown(target_proc):
                    try:
                        # 모드팩이나 월드 저장 시간을 감안하여 최대 90초 동안 자연 종료 대기
                        target_proc.wait(timeout=90)
                    except subprocess.TimeoutExpired:
                        print("[System] 서버가 90초 내에 자연 종료되지 않아 안전 종료 프로세스를 진행합니다.")
                        try:
                            target_proc.terminate()
                            target_proc.wait(timeout=10)
                        except Exception:
                            target_proc.kill()
                    finally:
                        self.server_process = None
                        self.is_stopping = False
                        print("[System] 마인크래프트 서버가 완전히 안전하게 종료되었습니다.")

                shutdown_thread = threading.Thread(
                    target=wait_graceful_shutdown,
                    args=(proc,),
                    daemon=True
                )
                shutdown_thread.start()

                return {"message": "Stop command sent. Saving world and shutting down gracefully."}
            except Exception as e:
                self.is_stopping = False
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
