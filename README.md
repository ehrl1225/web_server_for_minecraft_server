# Minecraft Server Web Controller (마인크래프트 서버 웹 컨트롤러)

FastAPI와 PyQt6를 결합하여 마인크래프트 서버의 실행/종료 및 콘솔 모니터링을 데스크톱 GUI 및 웹 패널을 통해 제어할 수 있도록 설계된 프로젝트입니다.

---

## 📌 프로젝트 아키텍처 및 동작 원리

이 프로젝트는 **PyQt6 GUI 애플리케이션**이 백그라운드로 **FastAPI 웹 서버(Uvicorn)** 프로세스를 띄우고, 사용자는 데스크톱 GUI 또는 웹 브라우저를 통해 마인크래프트 서버(.bat 파일)를 실행하고 관리하는 **이중 제어(Hybrid Controller)** 구조를 갖추고 있습니다.

```mermaid
flowchart TD
    UserGUI[사용자 / 데스크톱] -->|실행 및 설정| PyQt[PyQt6 GUI: OpenServerWidget]
    PyQt -->|subprocess uv run uvicorn| FastAPI[FastAPI 웹 서버: main.py]
    
    WebClient[외부 사용자 / 웹 브라우저] -->|HTTP REST / WebSocket| FastAPI
    
    FastAPI -->|서버 제어 및 콘솔 입출력| MC[마인크래프트 서버 프로세스 (.bat)]
    PyQt -->|경로 저장 / 직접 명령 전송 시도| MC
```

1. **PyQt6 GUI 실행 (`main.py` -> `OpenServerWidget`)**:
   - 서버 구동 스크립트(`.bat`) 경로 선택 및 파일 저장 (`src/server_file_path.txt`).
   - 웹 서버 포트 설정(기본 9000).
   - `Start` 클릭 시 `ApiServerWorker`를 통해 `uv run uvicorn main:app` 프로세스 실행.
   - 데스크톱 GUI에서 마인크래프트 콘솔에 직접 명령어를 보낼 수 있는 입력창 제공.
2. **FastAPI 웹 서버 (`main.py` / `src/router/`)**:
   - 정적 파일 호스팅: `http://localhost:<포트>/server/` (기본 `index.html`, 신규 `new_index.html`).
   - REST API 엔드포인트를 통해 마인크래프트 프로세스를 `subprocess.Popen`으로 띄우고, 로그를 `src/log/console_output.log`에 저장 및 조회.
   - 웹소켓 엔드포인트 (`/ws/stream`)를 통한 실시간 로그 스트리밍 및 상태 전송 준비.

---

## 📂 프로젝트 구조

```
web_server_for_minecraft_server/
├── main.py                     # 애플리케이션 진입점 (FastAPI 앱 정의 및 PyQt6 실행)
├── run.bat                     # 빠른 실행 배치 파일 (uv run main.py)
├── pyproject.toml              # 프로젝트 의존성 설정 (uv / setuptools)
├── README.md                   # 프로젝트 설명 및 상태 문서
└── src/
    ├── gui/
    │   ├── __init__.py
    │   ├── api_server_worker.py  # Uvicorn 서브프로세스 실행 및 Taskkill 관리 QObject
    │   └── open_server_widget.py # PyQt6 메인 GUI 윈도우
    ├── models/
    │   ├── __init__.py
    │   └── models.py             # FastAPI 요청용 Pydantic 모델 (Command, ReadLine)
    ├── router/
    │   ├── __init__.py
    │   ├── server_manager.py     # 마인크래프트 서버 제어 REST API 라우터
    │   └── websocket.py          # 실시간 웹소켓 라우터 (/ws/stream)
    ├── templates/
    │   ├── index.html            # 1차 구현 웹 UI (폴링 기반 REST API 연동)
    │   └── new_index.html        # 고도화 중인 모던 웹 대시보드 UI (웹소켓 기반, Chart.js)
    └── util/
        ├── __init__.py
        ├── database.py           # 상태 캐시 인스턴스 (미완성: monitor_minecraft_server 누락)
        ├── message_type.py       # 웹소켓 메시지 Enum (ERROR, STATUS, LOG)
        ├── server_data.py        # 마인크래프트 프로세스 실행/중지, 입출력 핵심 클래스
        ├── server_log.py         # 로그 관리 유틸리티 클래스
        └── server_status.py      # 서버 상태 데이터 클래스
```

---

## 🚦 현재 구현 상태 및 진척도

| 기능 영역 | 세부 항목 | 상태 | 설명 |
| :--- | :--- | :---: | :--- |
| **GUI (PyQt6)** | 서버 경로(.bat) 탐색 및 저장 | ✅ 완료 | `QFileDialog` 선택 및 `src/server_file_path.txt` 저장/불러오기 지원 |
| | API 웹서버 On/Off 제어 | ✅ 완료 | `ApiServerWorker`를 통해 `uvicorn` 프로세스 시작/강제종료 (`taskkill`) 지원 |
| | GUI 내 콘솔 명령어 직접 전송 | ⚠️ 미완성/버그 | GUI 프로세스와 API 서버 프로세스가 분리되어 실행되므로, GUI 측 `ServerData` 인스턴스에는 프로세스 핸들이 없음 (IPC 미연동) |
| **REST API** | 마인크래프트 서버 시작 (`POST /start-server`) | ✅ 구현됨 | `.bat` 파일 백그라운드 구동 및 `console_output.log`로 표준 출력 리다이렉트 |
| | 마인크래프트 서버 종료 (`POST /stop-server`) | ✅ 구현됨 | `stop\n` 명령 전송 후 terminate/kill 처리 |
| | 서버 실행 상태 확인 (`GET /is-started`, `/is-on`) | ✅ 구현됨 | 프로세스 존재 여부 및 로그 내 `"Dedicated server took"` 문구로 구동 완료 판별 |
| | 로그 폴링 (`POST /get-console-output`) | ✅ 구현됨 | 특정 라인 수 이후의 콘솔 로그 슬라이싱 반환 |
| | 콘솔 명령어 전송 (`POST /send-command`) | ⚠️ 버그 | `command.command` 속성 참조 버그 (`server_data.py`의 `send_command`) |
| **웹 프론트엔드** | 기존 UI (`index.html`) | 🟡 기본 동작 | 1초 주기로 REST API를 폴링하여 상태/로그 갱신 및 시작/종료 버튼 작동 |
| | 신규 대시보드 (`new_index.html`) | 🟡 퍼블리싱 완료 (연동 미완) | Tailwind CSS + Chart.js 기반의 세련된 UI이나, 웹소켓 백엔드와 연결 미완료 |
| **웹소켓 & 실시간성** | 웹소켓 라우터 (`/ws/stream`) | ❌ 미완성 | 웹소켓 엔드포인트 뼈대만 존재 (log_file_path 미지정, 클라이언트 명령 수신 루프 부재) |
| | 서버 라이프사이클 모니터링 | ❌ 오류 유발 | `main.py`에서 `monitor_minecraft_server`를 임포트하고 호출하지만 `database.py`에 미구현 (FastAPI 단독 실행 시 ImportError) |

---

## 🛠️ 발견된 주요 미완성 지점 및 수정 필요 사항

나중에 이어서 개발할 때 아래 항목들을 우선적으로 점검하고 개선해야 합니다:

1. **`main.py`의 모니터링 태스크 미구현 에러**:
   - `main.py` 11번 라인 `from src.util import monitor_minecraft_server`가 있으나 `database.py`에 해당 함수가 정의되어 있지 않아 FastAPI 가동 시 `ImportError`가 발생합니다.
   - 주기적으로 프로세스 상태 및 리소스(RAM 등)를 감시하는 비동기 함수 구현이 필요합니다.

2. **GUI ↔ FastAPI 프로세스 간 상태 불일치**:
   - PyQt GUI(`main.py`의 `OpenServerWidget`)는 별도의 서브프로세스(`ApiServerWorker` -> `uv run uvicorn`)로 웹서버를 실행합니다.
   - 따라서 GUI 상의 `server_data` 싱글톤과 Uvicorn 프로세스 내부의 `server_data` 싱글톤이 메모리를 공유하지 않습니다.
   - GUI의 명령어 전송(`sendCommand`)이나 시작 여부는 웹서버의 REST API(`localhost:포트/send-command`)를 호출하도록 변경해야 합니다.

3. **`server_data.py`의 `send_command` 버그**:
   - `server_manager.py`에서 `command.command`를 문자열로 넘겨주지만, `server_data.py` 내부에서 `proc.stdin.write(f"{command.command}\n")`처럼 다시 `.command`를 참조하고 있어 문자열 `AttributeError`가 발생합니다 (`f"{command}\n"`으로 수정 필요).

4. **웹소켓(`src/router/websocket.py`) 연동 완성**:
   - `log_file_path`가 빈 문자열(`""`)로 방치되어 있어 로그를 읽지 못합니다 (`src/log/console_output.log` 지정 필요).
   - 프론트(`new_index.html`)에서 보내는 JSON(`{"action": "start"}`, `{"action": "command"}`)을 수신하는 `websocket.receive_json()` 핸들러가 없습니다.
   - `ServerStatus`의 `equal_to_dict` 메서드가 미구현(`pass`) 상태입니다.

---

## 🚀 실행 방법

### 요구 사항
- Python >= 3.11
- [uv](https://github.com/astral-sh/uv) 패키지 매니저

### 실행
```bash
# GUI 실행 (기본)
uv run python main.py
# 또는
run.bat
```
1. GUI 창에서 **서버 파일 위치**의 `find` 버튼을 눌러 마인크래프트 서버의 `.bat` 파일을 선택합니다.
2. 포트 번호(기본 9000)를 확인한 후 **Start** 버튼을 누르면 FastAPI 서버가 구동됩니다.
3. 브라우저에서 `http://localhost:9000/server/index.html` (또는 `new_index.html`)로 접속하여 서버를 제어합니다.
