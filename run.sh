
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
RED='[0;31m'
GREEN='[0;32m'
YELLOW='[1;33m'
BLUE='[1;34m'
NC='[0m'
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
            printf "${BLUE}%s %s${NC}" "$msg" "${SPINNER[$((i % 10))]}" >&3
            sleep 0.1
            i=$((i + 1))
        done
        printf "[K" >&3
    else
        $cmd &>/dev/null &
        local pid=$!
        while kill -0 "$pid" 2>/dev/null; do
            printf "${BLUE}%s %s${NC}" "$msg" "${SPINNER[$((i % 10))]}" >&3
            sleep 0.1
            i=$((i + 1))
        done
        printf "[K" >&3
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
    if ! show_spinner "$MSG_INSTALLING" "bash "$INSTALL_SCRIPT" | tee -a "$LOG_FILE""; then
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
    echo -e "
[4T OUTPUT]" >> "$LOG_FILE"
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

