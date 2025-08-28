import os
import sys
import platform
import subprocess
import time
import datetime
from typing import List

# Thiết lập ngôn ngữ
LANGUAGE = os.environ.get('LANGUAGE', 'VI')

if LANGUAGE == 'EN':
    MSG_CHECK_OS = "Checking operating system..."
    MSG_OS_DETECTED = "Operating system: {} ({})"
    MSG_CHECK_PROJECT_DIR = "Checking project directory..."
    MSG_PROJECT_DIR_NOT_FOUND = "Project directory {} does not exist."
    MSG_PROJECT_DIR_NOT_WRITABLE = "Project directory {} is not writable."
    MSG_PROJECT_DIR_SUCCESS = "Project directory {} is accessible."
    MSG_VENV_EXISTS = "Virtual environment already exists."
    MSG_CREATE_VENV = "Creating new virtual environment..."
    MSG_VENV_FAIL = "Failed to create virtual environment."
    MSG_ACTIVATE_VENV = "Activating virtual environment..."
    MSG_ACTIVATE_VENV_FAIL = "Failed to activate virtual environment."
    MSG_CHECK_PYTHON_VERSION = "Checking Python version..."
    MSG_PYTHON_VERSION = "Python version: {}"
    MSG_CREATE_REQS = "Creating requirements.txt..."
    MSG_INSTALL_REQS = "Installing packages from requirements.txt..."
    MSG_REQS_FAIL = "Failed to install packages."
    MSG_CHECK_MAIN_PY = "Checking for main.py..."
    MSG_MAIN_PY_NOT_FOUND = "main.py not found in project directory."
    MSG_CREATE_RUN_SH = "Creating run.sh to execute the program..."
    MSG_RUN_SH_FAIL = "Failed to create or execute run.sh."
    MSG_COMPLETE = "Installation completed successfully!"
    MSG_SUMMARY = "Installation Summary"
    MSG_PRESS_ENTER = "Press Enter to continue..."
else:
    MSG_CHECK_OS = "Đang kiểm tra hệ điều hành..."
    MSG_OS_DETECTED = "Hệ điều hành: {} ({})"
    MSG_CHECK_PROJECT_DIR = "Đang kiểm tra thư mục dự án..."
    MSG_PROJECT_DIR_NOT_FOUND = "Thư mục dự án {} không tồn tại."
    MSG_PROJECT_DIR_NOT_WRITABLE = "Thư mục dự án {} không có quyền ghi."
    MSG_PROJECT_DIR_SUCCESS = "Thư mục dự án {} có thể truy cập."
    MSG_VENV_EXISTS = "Môi trường ảo đã tồn tại."
    MSG_CREATE_VENV = "Đang tạo mới môi trường ảo..."
    MSG_VENV_FAIL = "Lỗi khi tạo môi trường ảo."
    MSG_ACTIVATE_VENV = "Kích hoạt môi trường ảo..."
    MSG_ACTIVATE_VENV_FAIL = "Lỗi khi kích hoạt môi trường ảo."
    MSG_CHECK_PYTHON_VERSION = "Đang kiểm tra phiên bản Python..."
    MSG_PYTHON_VERSION = "Phiên bản Python: {}"
    MSG_CREATE_REQS = "Tạo file requirements.txt..."
    MSG_INSTALL_REQS = "Cài đặt các gói từ requirements.txt..."
    MSG_REQS_FAIL = "Lỗi khi cài đặt các gói."
    MSG_CHECK_MAIN_PY = "Đang kiểm tra main.py..."
    MSG_MAIN_PY_NOT_FOUND = "Không tìm thấy main.py trong thư mục dự án."
    MSG_CREATE_RUN_SH = "Tạo file run.sh để chạy chương trình..."
    MSG_RUN_SH_FAIL = "Lỗi khi tạo hoặc chạy run.sh."
    MSG_COMPLETE = "Cài đặt hoàn tất!"
    MSG_SUMMARY = "Tóm tắt cài đặt"
    MSG_PRESS_ENTER = "Nhấn Enter để tiếp tục..."

# Màu sắc và biểu tượng
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[1;34m'
NC = '\033[0m'
CHECKMARK = "✔"
CROSS = "✖"
SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

# File log
LOG_FILE = f"install_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Lấy đường dẫn thư mục dự án hiện tại
PROJECT_DIR = os.getcwd()
VENV_PATH = os.path.join(PROJECT_DIR, '.venv')

# Hàm hiển thị thông báo và ghi log
def log_info(msg: str) -> None:
    print(f"{GREEN}{CHECKMARK} {msg}{NC}")
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[INFO] {msg}\n")

def log_warn(msg: str) -> None:
    print(f"{YELLOW}! {msg}{NC}")
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[WARN] {msg}\n")

def log_error(msg: str) -> None:
    print(f"{RED}{CROSS} {msg}{NC}")
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[ERROR] {msg}\n")
    sys.exit(1)

# Hàm hiển thị thanh tiến trình
def show_progress(msg: str, duration: float) -> None:
    start_time = time.time()
    i = 0
    while time.time() - start_time < duration / 10:
        print(f"\r{BLUE}{msg} {SPINNER[i % 10]}{NC}", end='', flush=True)
        time.sleep(0.1)
        i += 1
    print("\r\033[K", end='', flush=True)

# Tóm tắt trạng thái
SUMMARY: List[str] = []

# Kiểm tra hệ điều hành
def check_os() -> None:
    show_progress(MSG_CHECK_OS, 10)
    OS = platform.system()
    ARCH = platform.machine()
    log_info(MSG_OS_DETECTED.format(OS, ARCH))
    SUMMARY.append(f"OS Check: {GREEN}{CHECKMARK}{NC}")

# Kiểm tra thư mục dự án
def check_project_directory() -> None:
    show_progress(MSG_CHECK_PROJECT_DIR, 5)
    if not os.path.exists(PROJECT_DIR):
        log_error(MSG_PROJECT_DIR_NOT_FOUND.format(PROJECT_DIR))
    if not os.access(PROJECT_DIR, os.R_OK | os.W_OK):
        log_error(MSG_PROJECT_DIR_NOT_WRITABLE.format(PROJECT_DIR))
    log_info(MSG_PROJECT_DIR_SUCCESS.format(PROJECT_DIR))
    SUMMARY.append(f"Project Directory: {GREEN}{CHECKMARK}{NC}")

# Kiểm tra phiên bản Python
def check_python_version() -> None:
    show_progress(MSG_CHECK_PYTHON_VERSION, 5)
    try:
        result = subprocess.run(['python3', '--version'], check=True, capture_output=True, text=True)
        python_version = result.stdout.strip()
        version_parts = python_version.split()[1].split('.')
        major, minor = int(version_parts[0]), int(version_parts[1])
        if major < 3 or (major == 3 and minor < 10):
            log_error(f"Phiên bản Python {python_version} không được hỗ trợ. Yêu cầu Python >= 3.10.")
        log_info(MSG_PYTHON_VERSION.format(python_version))
        SUMMARY.append(f"Python Version: {GREEN}{CHECKMARK}{NC}")
    except subprocess.CalledProcessError as e:
        log_error(f"{MSG_CHECK_PYTHON_VERSION}: {e}")
        SUMMARY.append(f"Python Version: {RED}{CROSS}{NC}")

# Kiểm tra môi trường ảo
def check_venv() -> None:
    if os.path.exists(VENV_PATH):
        log_info(MSG_VENV_EXISTS)
        SUMMARY.append(f"Virtual Env: {GREEN}{CHECKMARK}{NC}")
    else:
        show_progress(MSG_CREATE_VENV, 15)
        try:
            subprocess.run(['python3', '-m', 'venv', VENV_PATH], check=True)
            log_info(MSG_CREATE_VENV)
            SUMMARY.append(f"Virtual Env: {GREEN}{CHECKMARK}{NC}")
        except subprocess.CalledProcessError as e:
            log_error(f"{MSG_VENV_FAIL}: {e}")
            SUMMARY.append(f"Virtual Env: {RED}{CROSS}{NC}")

# Kích hoạt môi trường ảo và kiểm tra phiên bản Python trong môi trường ảo
def activate_venv() -> None:
    show_progress(MSG_ACTIVATE_VENV, 10)
    try:
        venv_python = os.path.join(VENV_PATH, 'bin', 'python') if platform.system() != "Windows" else os.path.join(VENV_PATH, 'Scripts', 'python.exe')
        if not os.path.exists(venv_python):
            raise FileNotFoundError(f"Python executable not found in virtual environment: {venv_python}")

        # Kiểm tra phiên bản Python trong môi trường ảo
        show_progress(MSG_CHECK_PYTHON_VERSION, 5)
        result = subprocess.run([venv_python, '--version'], check=True, capture_output=True, text=True)
        python_version = result.stdout.strip()
        log_info(MSG_PYTHON_VERSION.format(python_version))
        SUMMARY.append(f"Python Version (venv): {GREEN}{CHECKMARK}{NC}")

        log_info(MSG_ACTIVATE_VENV)
        SUMMARY.append(f"Activate Venv: {GREEN}{CHECKMARK}{NC}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        log_error(f"{MSG_ACTIVATE_VENV_FAIL}: {e}")
        SUMMARY.append(f"Activate Venv: {RED}{CROSS}{NC}")

# Tạo file requirements.txt
def create_requirements() -> None:
    show_progress(MSG_CREATE_REQS, 10)
    requirements_content = """\
fastapi
uvicorn
python-dotenv
ddgs
trafilatura
requests
numpy
pillow
protobuf
tqdm
gfpgan
schedule
pygments
beautifulsoup4
python-multipart
PyJWT
httpx
aiohttp
passlib[argon2]
argon2-cffi
PyPDF2
websocket-client
requests
transformers
soundfile
accelerate
rich
prompt_toolkit
reportlab
textual
sqlalchemy
tiktoken
googletrans==4.0.0-rc1
google-auth~=2.40.3
google-auth-oauthlib~=1.0.0
google-auth-httplib2~=0.1.0
google-api-python-client~=2.85.0
"""
    try:
        with open('requirements.txt', 'w', encoding='utf-8') as f:
            f.write(requirements_content)
        log_info(MSG_CREATE_REQS)
        SUMMARY.append(f"Requirements.txt: {GREEN}{CHECKMARK}{NC}")
    except Exception as e:
        log_error(f"{MSG_CREATE_REQS}: {e}")
        SUMMARY.append(f"Requirements.txt: {RED}{CROSS}{NC}")

# Cài đặt các gói
def install_packages() -> None:
    show_progress(MSG_INSTALL_REQS, 30)
    try:
        venv_python = os.path.join(VENV_PATH, 'bin', 'python') if platform.system() != "Windows" else os.path.join(VENV_PATH, 'Scripts', 'python.exe')
        if not os.path.exists(venv_python):
            raise FileNotFoundError(f"Python executable not found in virtual environment: {venv_python}")
        # Cập nhật pip trước khi cài đặt
        subprocess.run([venv_python, '-m', 'pip', 'install', '--upgrade', 'pip'], check=True)
        subprocess.run([venv_python, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        log_info(MSG_INSTALL_REQS)
        SUMMARY.append(f"Packages: {GREEN}{CHECKMARK}{NC}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        log_error(f"{MSG_REQS_FAIL}: {e}")
        SUMMARY.append(f"Packages: {RED}{CROSS}{NC}")

# Hiển thị tóm tắt và tạo file run.sh
def show_summary() -> None:
    show_progress(MSG_CHECK_MAIN_PY, 5)
    if not os.path.exists('main.py'):
        log_error(MSG_MAIN_PY_NOT_FOUND)
        SUMMARY.append(f"Main.py: {RED}{CROSS}{NC}")
        return

    show_progress(MSG_CREATE_RUN_SH, 5)
    run_script_content = """
#!/bin/bash

# Set UTF-8 encoding
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# Set language (default Vietnamese, can switch to EN via LANGUAGE=EN)
LANGUAGE=${LANGUAGE:-VI}
if [ "$LANGUAGE" = "EN" ]; then
    MSG_CANCEL="Operation canceled."
    MSG_CHECKING_ENV="Checking virtual environment..."
    MSG_CHECKING_PY="Checking Python executable..."
    MSG_CHECKING_COMFY="Checking 4T main script..."
    MSG_STARTING="Starting 4T..."
    MSG_SUCCESS="4T started successfully."
    MSG_LOG="Logs saved to: %s"
    MSG_OPENING_LOG="Opening log file: %s"
    MSG_ERROR_ENV="Virtual environment not found."
    MSG_ERROR_PY="Python executable not found."
    MSG_ERROR_COMFY="4T main script not found."
    MSG_ERROR_START="Failed to start 4T."
    MSG_URL_DETECTED="4T URL: http://127.0.0.1:8188"
    MSG_INSTALLING="Installing virtual environment..."
    MSG_ERROR_INSTALL="Failed to install virtual environment. Check logs at %s."
    MSG_ERROR_MANUAL="Try running utils/install.sh manually to diagnose."
    MSG_ERROR_LOG_NOT_FOUND="Log file not found: %s"
    MSG_LOGGING_CONTINUOUS="Continuously logging 4T output to %s..."
else
    MSG_CANCEL="Hủy thao tác."
    MSG_CHECKING_ENV="Kiểm tra môi trường ảo..."
    MSG_CHECKING_PY="Kiểm tra tệp thực thi Python..."
    MSG_CHECKING_COMFY="Kiểm tra script chính của 4T..."
    MSG_STARTING="Đang khởi động 4T..."
    MSG_SUCCESS="4T đã khởi động thành công."
    MSG_LOG="Log được lưu tại: %s"
    MSG_OPENING_LOG="Đang mở tệp log: %s"
    MSG_ERROR_ENV="Không tìm thấy môi trường ảo."
    MSG_ERROR_PY="Không tìm thấy tệp thực thi Python."
    MSG_ERROR_COMFY="Không tìm thấy script chính của 4T."
    MSG_ERROR_START="Không thể khởi động 4T."
    MSG_URL_DETECTED="URL 4T: http://127.0.0.1:8188"
    MSG_INSTALLING="Đang cài đặt môi trường ảo..."
    MSG_ERROR_INSTALL="Không thể cài đặt môi trường ảo. Kiểm tra log tại %s."
    MSG_ERROR_MANUAL="Thử chạy utils/install.sh thủ công để kiểm tra."
    MSG_ERROR_LOG_NOT_FOUND="Không tìm thấy tệp log: %s"
    MSG_LOGGING_CONTINUOUS="Đang ghi log liên tục đầu ra của 4T vào %s..."
fi

# Colors and symbols
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
NC='\033[0m'
CHECKMARK="✔"
CROSS="✖"
SPINNER=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")

# Log file (relative path)
LOG_FILE="./4T_start_$(date +%Y%m%d_%H%M%S).log"
exec 3>&1 1>>"$LOG_FILE" 2>&1

# Flag to track if log file has been opened
LOG_OPENED=false

# Function to display messages
log_info() { echo -e "${GREEN}${CHECKMARK} $1${NC}" >&3; echo "[INFO] $1" >> "$LOG_FILE"; }
log_info_silent() { echo "[INFO] $1" >> "$LOG_FILE"; }
log_warn() { echo -e "${YELLOW}! $1${NC}" >&3; echo "[WARN] $1" >> "$LOG_FILE"; }
log_error() { echo -e "${RED}${CROSS} $1${NC}" >&3; echo "[ERROR] $1" >> "$LOG_FILE"; exit 1; }

# Function to display a simple spinner
show_spinner() {
    local msg=$1
    local cmd=$2
    local i=0
    if [ -z "$cmd" ]; then
        for ((j=0; j<15; j++)); do
            printf "\r${BLUE}%s %s${NC}" "$msg" "${SPINNER[$((i % 10))]}" >&3
            sleep 0.1
            i=$((i + 1))
        done
        printf "\r\033[K" >&3
    else
        $cmd &>/dev/null &
        local pid=$!
        while kill -0 "$pid" 2>/dev/null; do
            printf "\r${BLUE}%s %s${NC}" "$msg" "${SPINNER[$((i % 10))]}" >&3
            sleep 0.1
            i=$((i + 1))
        done
        printf "\r\033[K" >&3
        wait "$pid"
        return $?
    fi
}

# Define project paths (absolute)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)" || log_error "Không thể xác định thư mục script."
log_info "Thư mục script: $SCRIPT_DIR"
PROJECT_DIR="$SCRIPT_DIR"
VENV_PATH="$PROJECT_DIR/.venv"
PYTHON_EXEC="$VENV_PATH/bin/python"
COMFY_MAIN="$PROJECT_DIR/main.py"
INSTALL_SCRIPT="$PROJECT_DIR/install.sh"

# Check virtual environment and install if not exists
show_spinner "$MSG_CHECKING_ENV"
if [ ! -d "$VENV_PATH" ]; then
    log_warn "Không tìm thấy môi trường ảo. Chạy script cài đặt..."
    if [ ! -f "$INSTALL_SCRIPT" ] || [ ! -x "$INSTALL_SCRIPT" ]; then
        log_error "$(printf "$MSG_ERROR_MANUAL" "$LOG_FILE")"
    fi
    if ! show_spinner "$MSG_INSTALLING" "bash \"$INSTALL_SCRIPT\" | tee -a \"$LOG_FILE\""; then
        log_error "$(printf "$MSG_ERROR_MANUAL" "$LOG_FILE")"
    else
        log_info "Môi trường ảo được cài đặt thành công."
    fi
else
    log_info_silent "Tìm thấy môi trường ảo tại $VENV_PATH."
fi

# Check Python executable
show_spinner "$MSG_CHECKING_PY"
if [ ! -x "$PYTHON_EXEC" ]; then
    log_error "$MSG_ERROR_PY"
else
    log_info_silent "Tìm thấy tệp thực thi Python tại $PYTHON_EXEC."
fi

# Check 4T main script
show_spinner "$MSG_CHECKING_COMFY"
if [ ! -f "$COMFY_MAIN" ]; then
    log_error "$MSG_ERROR_COMFY"
else
    log_info_silent "Tìm thấy script chính của 4T tại $COMFY_MAIN."
fi

# Start 4T with optimized parameters for RTX 4060 8GB VRAM
show_spinner "$MSG_STARTING"
log_info "$MSG_STARTING"

TEMP_OUTPUT=$(mktemp)

# Activate venv and run main.py with optimized args
if ! source "$VENV_PATH/bin/activate"; then
    log_error "Không thể kích hoạt môi trường ảo tại $VENV_PATH."
fi
"$PYTHON_EXEC" "$COMFY_MAIN" > "$TEMP_OUTPUT" 2>&1 &
COMFY_PID=$!

# Start continuous logging
if [ -f "$TEMP_OUTPUT" ]; then
    echo -e "\n[4T OUTPUT]" >> "$LOG_FILE"
    tail -f "$TEMP_OUTPUT" >> "$LOG_FILE" &
    TAIL_PID=$!
else
    log_warn "Không tìm thấy tệp đầu ra 4T: $TEMP_OUTPUT"
fi

# Monitor for URL
while true; do
    if grep -q "http://0.0.0.0:8000" "$TEMP_OUTPUT"; then
        log_info "$MSG_SUCCESS"
        log_info "Url api: http://0.0.0.0:8000/docs"
        deactivate 2>/dev/null || log_warn "Không thể hủy kích hoạt môi trường ảo."
        exit 0
    fi
    if ! ps -p $COMFY_PID > /dev/null; then
        log_error "$MSG_ERROR_START"
    fi
    sleep 1
done

"""
    try:
        with open('run.sh', 'w', encoding='utf-8') as f:
            f.write(run_script_content)
        os.chmod('run.sh', 0o755)  # Cấp quyền thực thi
        log_info(MSG_CREATE_RUN_SH)
        SUMMARY.append(f"Run.sh: {GREEN}{CHECKMARK}{NC}")

        # Hiển thị tóm tắt
        print(f"\n{BLUE}{MSG_SUMMARY}{NC}")
        for item in SUMMARY:
            print(f"{BLUE}│{NC} {item}")
        print(f"{GREEN}{CHECKMARK} {MSG_COMPLETE}{NC}")

        # Chạy file run.sh
        log_info("Đang chạy chương trình chính bằng ./run.sh...")
        try:
            subprocess.run(['./run.sh'], check=True, shell=True)
            log_info("Chương trình chính chạy thành công!")
            SUMMARY.append(f"Run Program: {GREEN}{CHECKMARK}{NC}")
        except subprocess.CalledProcessError as e:
            log_error(f"Lỗi khi chạy chương trình chính: {e}")
            SUMMARY.append(f"Run Program: {RED}{CROSS}{NC}")
    except Exception as e:
        log_error(f"{MSG_RUN_SH_FAIL}: {e}")
        SUMMARY.append(f"Run.sh: {RED}{CROSS}{NC}")

# Hàm chính
def main() -> None:
    check_os()
    check_project_directory()
    check_python_version()
    check_venv()
    activate_venv()
    create_requirements()
    install_packages()
    show_summary()
    input(MSG_PRESS_ENTER)

if __name__ == "__main__":
    main()
