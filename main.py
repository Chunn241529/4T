
import uvicorn
from fastapi import FastAPI
from routes import router
import os
import subprocess
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn
from pathlib import Path

app = FastAPI()
app.include_router(router)

def clear_cache():
    # Kiểm tra biến môi trường CLEAR_CACHE, mặc định là True
    if os.getenv("CLEAR_CACHE", "true").lower() != "true":
        print("Bỏ qua xóa cache theo cấu hình CLEAR_CACHE.")
        return

    # Đường dẫn đến clean_full.sh
    script_path = os.path.join(os.getcwd(), "clean.sh")

    if not os.path.exists(script_path):
        print(f"Không tìm thấy script {script_path}")
        return

    # Đảm bảo script có quyền thực thi
    os.chmod(script_path, 0o755)

    # Ước lượng số lượng cache bằng cách chạy script ở chế độ thử
    try:
        test_process = subprocess.run(
            [script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )
        # Đếm số dòng output có "Đang xóa" để ước lượng tiến trình
        total_tasks = len([line for line in test_process.stdout.splitlines() if "Đang xóa" in line])
    except Exception as e:
        print(f"Lỗi khi ước lượng tiến trình: {str(e)}")
        total_tasks = 1  # Dự phòng để tránh lỗi progress bar

    if total_tasks == 0:
        print("Không tìm thấy thư mục cache nào để xóa.")
        return

    # Sử dụng rich để hiển thị progress bar
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeRemainingColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        task = progress.add_task("Loading...", total=total_tasks)

        try:
            # Chạy clean_full.sh
            process = subprocess.Popen(
                [script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.getcwd()
            )

            # Đọc output và cập nhật progress bar
            while process.poll() is None:
                output = process.stdout.readline().strip()
                if output and "Đang xóa" in output:
                    progress.advance(task)

            # Đọc output còn lại
            stdout, stderr = process.communicate()
            for line in stdout.splitlines():
                if line.strip() and "Đang xóa" in line:
                    progress.advance(task)

            if process.returncode != 0:
                progress.console.print(f"Lỗi khi chạy clean_full.sh: {stderr}")
            else:
                progress.console.print("Đã xóa xong cache.")

        except Exception as e:
            progress.console.print(f"Lỗi khi chạy clean_full.sh: {str(e)}")

    print("Lưu ý: Thư mục __pycache__ có thể được Python tạo lại khi chạy ứng dụng.")

def main():
    print("Kiểm tra và xóa các thư mục cache...")
    clear_cache()
    print("Khởi động server...")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1
    )

if __name__ == "__main__":
    main()
