#!/bin/bash
# ==============================================================================
# Script cài đặt môi trường trên EC2 (Ubuntu 22.04 / 24.04 LTS)
# ==============================================================================
set -e

echo "=== [1/4] Cập nhật hệ thống và cài đặt system packages ==="
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y \
    python3 \
    python3-venv \
    python3-pip \
    git \
    postgresql-client \
    ffmpeg \
    curl

echo "=== [2/4] Kiểm tra phiên bản Python & FFmpeg ==="
python3 --version
ffmpeg -version | head -n 1
psql --version

echo "=== [3/4] Tạo virtual environment .venv ==="
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "Virtual environment created."
fi

source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo "=== [4/4] Cài đặt hoàn tất! ==="
echo "Tiếp theo: Hãy đảm bảo bạn đã tạo file .env trước khi chạy start.sh"
