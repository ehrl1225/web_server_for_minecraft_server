import subprocess
import os

log_path = "src/log/console_output.log"
server_file_path_txt = "src/server_file_path.txt"


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
        with open(server_file_path_txt, "w") as f:
            f.write(self.server_file_path)

    def load_server_file_path(self):
        if os.path.exists(server_file_path_txt):
            with open(server_file_path_txt, "r") as f:
                self.server_file_path = f.read()
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
        if self.server_process is None:
            return {"is_started": False}
        if self.server_process.poll() is None:
            return {"is_started": True}
        return {"is_started": False}


    def is_on(self) -> dict[str, bool]:
        if self.server_process is None:
            return {"is_on": False}
        if self.server_process.poll() is not None:
            return {"is_on": False}
        with open(log_path, "r") as file:
            output = file.readlines()
            for line in output[::-1]:
                split_line = line.split(": ")
                if len(split_line) == 2:
                    a, b = split_line
                    if b.startswith("Dedicated server took"):
                        break
            else:
                return {"is_on": False}
            return {"is_on": True}


    def start(self) -> dict[str, str]:
        if self.server_process is None:
            self.load_server_file_path()
            path = self.server_file_path
            print(path)
            with open(log_path, "w") as log_file:
                self.server_process = subprocess.Popen(
                    f"\"{path}\"",
                    stdin=subprocess.PIPE,
                    stdout=log_file,
                    stderr=log_file,
                    shell=True,
                    text=True,
                    cwd=os.path.dirname(path)
                )
            return {"message": "Server started"}
        return {"message": "Server is already running"}


    def stop(self) -> dict[str, str]:
        if self.server_process is not None:
            try:
                proc = self.server_process
                proc.stdin.write("stop\n")
                proc.terminate()
                proc.wait(5)
                if proc.poll() is None:
                    proc.kill()
                self.server_process = None
                return {"message": "Server stopped"}
            except Exception as e:
                return {"error": str(e)}
        return {"message": "Server is not running"}

    def get_console_output(self, startline:int) -> dict[str, list[str]|str]:
        try:
            with open(log_path, "r") as file:
                output = file.readlines()
            return {"console_output": output[startline:]}
        except Exception as e:
            return {"error": str(e)}

    def send_command(self, command:str) -> dict[str, str]:
        if self.server_process is not None:
            try:
                proc = self.server_process
                proc.stdin.write(f"{command.command}\n")
                proc.stdin.flush()
                return {
                    "message": "sent"
                }
            except Exception as e:
                return {"error": str(e)}
        else:
            return {"message": "Server is not running"}
