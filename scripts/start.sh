#!/bin/bash
# ==============================================================================
# Script khởi chạy FastAPI Backend trên EC2
# ==============================================================================
set -e

# Chuyển về thư mục chứa script (thư mục gốc dự án)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Kích hoạt virtualenv
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Lỗi: Không tìm thấy thư mục .venv! Hãy chạy scripts/setup_ec2.sh trước."
    exit 1
fi

# Kiểm tra file .env
if [ ! -f ".env" ]; then
    echo "Lỗi: Không tìm thấy file .env!"
    echo "Hãy copy .env.example sang .env và điền thông tin cấu hình."
    exit 1
fi

echo "=== Khởi chạy FastAPI Backend tại 0.0.0.0:8000 ==="
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
