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
    MSG_COMPLETE = "Cài đặt hoàn tất!"
    MSG_SUMMARY = "Tóm tắt cài đặt"
    MSG_PRESS_ENTER = "Nhấn Enter để thoát..."

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

# Kiểm tra thư mục dự án
def check_project_directory() -> None:
    show_progress(MSG_CHECK_PROJECT_DIR, 5)
    if not os.path.exists(PROJECT_DIR):
        log_error(MSG_PROJECT_DIR_NOT_FOUND.format(PROJECT_DIR))
    if not os.access(PROJECT_DIR, os.R_OK | os.W_OK):
        log_error(MSG_PROJECT_DIR_NOT_WRITABLE.format(PROJECT_DIR))
    log_info(MSG_PROJECT_DIR_SUCCESS.format(PROJECT_DIR))
    SUMMARY.append(f"Project Directory: {GREEN}{CHECKMARK}{NC}")

# Kiểm tra hệ điều hành
def check_os() -> None:
    show_progress(MSG_CHECK_OS, 10)
    OS = platform.system()
    ARCH = platform.machine()
    log_info(MSG_OS_DETECTED.format(OS, ARCH))
    SUMMARY.append(f"OS Check: {GREEN}{CHECKMARK}{NC}")

# Kiểm tra môi trường ảo
def check_venv() -> None:
    if os.path.exists(VENV_PATH):
        log_info(MSG_VENV_EXISTS)
        SUMMARY.append(f"Virtual Env: {GREEN}{CHECKMARK}{NC}")
    else:
        show_progress(MSG_CREATE_VENV, 15)
        try:
            subprocess.run(['python3.12', '-m', 'venv', VENV_PATH], check=True)
            log_info(MSG_CREATE_VENV)
            SUMMARY.append(f"Virtual Env: {GREEN}{CHECKMARK}{NC}")
        except subprocess.CalledProcessError as e:
            log_error(f"{MSG_VENV_FAIL}: {e}")
            SUMMARY.append(f"Virtual Env: {RED}{CROSS}{NC}")

# Kích hoạt môi trường ảo và kiểm tra phiên bản Python
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
        SUMMARY.append(f"Python Version: {GREEN}{CHECKMARK}{NC}")

        log_info(MSG_ACTIVATE_VENV)
        SUMMARY.append(f"Activate Venv: {GREEN}{CHECKMARK}{NC}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        log_error(f"{MSG_ACTIVATE_VENV_FAIL}: {e}")
        SUMMARY.append(f"Activate Venv: {RED}{CROSS}{NC}")

# Tạo file requirements.txt
def create_requirements() -> None:
    show_progress(MSG_CREATE_REQS, 10)
    requirements_content = """openai
fastapi
uvicorn
python-dotenv
duckduckgo-search
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
        subprocess.run([venv_python, '-m', 'pip', 'install', '-U', '-r', 'requirements.txt'], check=True)
        log_info(MSG_INSTALL_REQS)
        SUMMARY.append(f"Packages: {GREEN}{CHECKMARK}{NC}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        log_error(f"{MSG_REQS_FAIL}: {e}")
        SUMMARY.append(f"Packages: {RED}{CROSS}{NC}")

# Hiển thị tóm tắt và tạo file run.sh
def show_summary() -> None:
    for item in SUMMARY:
        print(f"{BLUE}│{NC} {item}")
    print(f"{GREEN}{CHECKMARK} {MSG_COMPLETE}{NC}")

    # Tạo shell script để chạy chương trình
    run_script_content = """#!/bin/bash
source .venv/bin/activate
python main.py
"""
    try:
        with open('run.sh', 'w', encoding='utf-8') as f:
            f.write(run_script_content)
        os.chmod('run.sh', 0o755)  # Cấp quyền thực thi
        log_info("Tạo file run.sh để chạy chương trình trong môi trường ảo.")
        log_info("Đang chạy chương trình chính bằng ./run.sh...")

        # Chạy file run.sh
        try:
            subprocess.run(['./run.sh'], check=True, shell=True)
            log_info("Chương trình chính chạy thành công!")
        except subprocess.CalledProcessError as e:
            log_error(f"Lỗi khi chạy chương trình chính: {e}")
    except Exception as e:
        log_error(f"Lỗi khi tạo hoặc chạy run.sh: {e}")

    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

if __name__ == "__main__":
    main()
