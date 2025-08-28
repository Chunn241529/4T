#!/bin/bash

# Đặt biến môi trường UTF-8
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# Định nghĩa ngôn ngữ (mặc định là tiếng Việt, có thể chuyển sang EN bằng LANGUAGE=EN)
LANGUAGE=${LANGUAGE:-VN}
if [ "$LANGUAGE" = "EN" ]; then
    MSG_CANCEL="Operation canceled."
    MSG_CHECKING_VENV="Checking virtual environment..."
    MSG_ACTIVATING_VENV="Activating virtual environment..."
    MSG_VENV_NOT_FOUND="Virtual environment not found at %s."
    MSG_CHECKING_PROCESS="Checking for running 4T process..."
    MSG_STOPPING="Stopping 4T..."
    MSG_NO_PROCESS="No running 4T process found."
    MSG_ERROR_STOP="Failed to stop 4T process (PID: %s). Try 'ps -aux | grep main.py' to debug."
    MSG_SUGGEST_MANUAL="Try running 'ps -aux | grep main.py' to check for running processes."
    MSG_STOPPING_TAIL="Stopping tail processes..."
    MSG_NO_TAIL="No tail processes found."
    MSG_CLEANING_LOGS="Cleaning log files..."
    MSG_CLEANING_TEMP="Cleaning temporary output files..."
    MSG_CLEANING="Cleaning cache..."
    MSG_CLEAN_HF="Clearing Hugging Face cache..."
    MSG_CLEAN_TORCH="Clearing PyTorch cache..."
    MSG_CLEAN_PYCACHE="Clearing __pycache__ directories..."
    MSG_CLEAN_PYC="Clearing *.pyc files..."
    MSG_CLEAN_PIP="Clearing pip cache..."
    MSG_CLEAN_COMFY_TEMP="Clearing 4T temp directory..."
    MSG_CLEAN_COMFY_OUTPUT="Clearing 4T output directory..."
else
    MSG_CANCEL="Hủy thao tác."
    MSG_CHECKING_VENV="Kiểm tra môi trường ảo..."
    MSG_ACTIVATING_VENV="Kích hoạt môi trường ảo..."
    MSG_VENV_NOT_FOUND="Không tìm thấy môi trường ảo tại %s."
    MSG_CHECKING_PROCESS="Kiểm tra tiến trình 4T đang chạy..."
    MSG_STOPPING="Đang dừng 4T..."
    MSG_NO_PROCESS="Không tìm thấy tiến trình 4T đang chạy."
    MSG_ERROR_STOP="Không thể dừng tiến trình 4T (PID: %s). Thử 'ps -aux | grep main.py' để kiểm tra."
    MSG_SUGGEST_MANUAL="Thử chạy 'ps -aux | grep main.py' để kiểm tra tiến trình đang chạy."
    MSG_STOPPING_TAIL="Đang dừng các tiến trình tail..."
    MSG_NO_TAIL="Không tìm thấy tiến trình tail."
    MSG_CLEANING_LOGS="Đang xóa các tệp log..."
    MSG_CLEANING_TEMP="Đang xóa các tệp đầu ra tạm thời..."
    MSG_CLEANING="Dọn dẹp cache..."
    MSG_CLEAN_HF="Xóa cache Hugging Face..."
    MSG_CLEAN_TORCH="Xóa cache PyTorch..."
    MSG_CLEAN_PYCACHE="Xóa các thư mục __pycache__..."
    MSG_CLEAN_PYC="Xóa các file *.pyc..."
    MSG_CLEAN_PIP="Xóa cache pip..."
    MSG_CLEAN_COMFY_TEMP="Xóa thư mục temp của 4T..."
    MSG_CLEAN_COMFY_OUTPUT="Xóa thư mục output của 4T..."
fi

# Colors và symbols
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
NC='\033[0m'
CHECKMARK="✔"
CROSS="✖"
SPINNER=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")

# Định nghĩa đường dẫn dự án (tuyệt đối)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
VENV_PATH="$PROJECT_DIR/.venv"
PYTHON_EXEC="$VENV_PATH/bin/python"
COMFY_MAIN="$PROJECT_DIR/main.py"
LOG_FILE="$PROJECT_DIR/4T_stop_$(date +%Y%m%d_%H%M%S).log"

# Tạo thư mục dự án trước khi ghi log
mkdir -p "$PROJECT_DIR" || { echo -e "${RED}${CROSS} Không thể tạo thư mục dự án: $PROJECT_DIR${NC}"; exit 1; }

# Chuyển hướng output tới log file và console
exec 3>&1 1>>"$LOG_FILE" 2>&1

# Hàm hiển thị thông điệp
log_info() { echo -e "${GREEN}${CHECKMARK} $1${NC}" >&3; echo "[INFO] $1" >> "$LOG_FILE"; }
log_warn() { echo -e "${YELLOW}! $1${NC}" >&3; echo "[WARN] $1" >> "$LOG_FILE"; }
log_error() { echo -e "${RED}${CROSS} $1${NC}" >&3; echo "[ERROR] $1" >> "$LOG_FILE"; exit 1; }

# Hàm hiển thị spinner
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
        $cmd >> "$LOG_FILE" 2>&1 &
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

# Bước 1: Kiểm tra và kích hoạt môi trường ảo
show_spinner "$MSG_CHECKING_VENV"
if [ ! -d "$VENV_PATH" ] || [ ! -f "$PYTHON_EXEC" ]; then
    log_error "$(printf "$MSG_VENV_NOT_FOUND" "$VENV_PATH")"
fi

show_spinner "$MSG_ACTIVATING_VENV"
source "$VENV_PATH/bin/activate" || log_error "Không thể kích hoạt môi trường ảo tại $VENV_PATH."

# Bước 2: Dừng tiến trình 4T
show_spinner "$MSG_CHECKING_PROCESS"
if [ ! -f "$COMFY_MAIN" ]; then
    log_error "Không tìm thấy script chính của 4T tại $COMFY_MAIN."
fi

# Tìm tiến trình 4T bằng pgrep, chỉ lấy các tiến trình của người dùng hiện tại
COMFY_PID=$(pgrep -u "$USER" -f "python.*$COMFY_MAIN")

if [ -n "$COMFY_PID" ]; then
    show_spinner "$MSG_STOPPING"
    log_info "$MSG_STOPPING"
    for pid in $COMFY_PID; do
        if ! kill -TERM "$pid" 2>/dev/null; then
            log_error "$(printf "$MSG_ERROR_STOP" "$pid")"
            log_info "$MSG_SUGGEST_MANUAL"
        fi

        # Chờ tiến trình dừng
        for i in {1..5}; do
            if ! ps -p "$pid" > /dev/null 2>&1; then
                log_info "Tiến trình (PID: $pid) đã dừng thành công."
                break
            fi
            sleep 1
        done

        # Nếu tiến trình vẫn chạy, buộc dừng
        if ps -p "$pid" > /dev/null 2>&1; then
            log_warn "Tiến trình (PID: $pid) không dừng nhẹ nhàng, buộc dừng..."
            if ! kill -KILL "$pid" 2>/dev/null; then
                log_error "$(printf "$MSG_ERROR_STOP" "$pid")"
                log_info "$MSG_SUGGEST_MANUAL"
            fi
        fi
    done
else
    log_info "$MSG_NO_PROCESS"
fi

# Bước 3: Dừng các tiến trình tail liên quan đến người dùng hiện tại
show_spinner "$MSG_STOPPING_TAIL"
TAIL_PIDS=$(pgrep -u "$USER" -f "tail -f /tmp/tmp")
if [ -n "$TAIL_PIDS" ]; then
    for pid in $TAIL_PIDS; do
        kill -TERM "$pid" 2>/dev/null && log_info "Đã dừng tiến trình tail (PID: $pid)." || log_warn "Không thể dừng tiến trình tail (PID: $pid)."
    done
else
    log_info "$MSG_NO_TAIL"
fi

# Bước 4: Xóa các tệp log
show_spinner "$MSG_CLEANING_LOGS"
if compgen -G "$PROJECT_DIR"/4T_{start,restart,stop}_*.log > /dev/null; then
    rm -f -- "$PROJECT_DIR"/4T_{start,restart,stop}_*.log \
        && log_info "$MSG_CLEANING_LOGS" \
        || log_warn "Không thể xóa một số tệp log."
else
    log_info "Không tìm thấy tệp log."
fi


# Bước 5: Xóa các tệp đầu ra tạm thời
show_spinner "$MSG_CLEANING_TEMP"
if ls /tmp/tmp* >/dev/null 2>&1; then
    rm -f /tmp/tmp* && log_info "$MSG_CLEANING_TEMP" || log_warn "Không thể xóa một số tệp tạm thời."
else
    log_info "Không tìm thấy tệp tạm thời."
fi

# Bước 6: Dọn dẹp cache
show_spinner "$MSG_CLEANING"
# Xóa cache Hugging Face
show_spinner "$MSG_CLEAN_HF"
if [ -d "/home/$USER/.cache/huggingface" ]; then
    rm -rf "/home/$USER/.cache/huggingface"/* && log_info "$MSG_CLEAN_HF" || log_warn "Không thể xóa cache Hugging Face."
else
    log_info "Không tìm thấy thư mục cache Hugging Face."
fi

# Xóa cache PyTorch
show_spinner "$MSG_CLEAN_TORCH"
if [ -d "/home/$USER/.cache/torch" ]; then
    rm -rf "/home/$USER/.cache/torch"/* && log_info "$MSG_CLEAN_TORCH" || log_warn "Không thể xóa cache PyTorch."
else
    log_info "Không tìm thấy thư mục cache PyTorch."
fi

# Xóa thư mục __pycache__
show_spinner "$MSG_CLEAN_PYCACHE"
if find "$PROJECT_DIR" -type d -name "__pycache__" | grep -q .; then
    find "$PROJECT_DIR" -type d -name "__pycache__" -exec rm -rf {} + && log_info "$MSG_CLEAN_PYCACHE" || log_warn "Không thể xóa một số thư mục __pycache__."
else
    log_info "Không tìm thấy thư mục __pycache__."
fi

# Xóa file *.pyc
show_spinner "$MSG_CLEAN_PYC"
if find "$PROJECT_DIR" -type f -name "*.pyc" | grep -q .; then
    find "$PROJECT_DIR" -type f -name "*.pyc" -exec rm -f {} + && log_info "$MSG_CLEAN_PYC" || log_warn "Không thể xóa một số file *.pyc."
else
    log_info "Không tìm thấy file *.pyc."
fi

# Xóa cache pip
show_spinner "$MSG_CLEAN_PIP"
if [ -d "/home/$USER/.cache/pip" ]; then
    rm -rf "/home/$USER/.cache/pip"/* && log_info "$MSG_CLEAN_PIP" || log_warn "Không thể xóa cache pip."
else
    log_info "Không tìm thấy thư mục cache pip."
fi


# Thoát môi trường ảo
deactivate 2>/dev/null || log_warn "Không thể thoát môi trường ảo."

# Xóa tệp log dừng
rm -f "$LOG_FILE" 2>/dev/null

exit 0
