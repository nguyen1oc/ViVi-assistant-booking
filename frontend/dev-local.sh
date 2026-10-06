#!/usr/bin/env bash
# Khởi động môi trường dev local cho P-053 (backend SQLite + frontend Vite).
# Không cần Docker. Dừng bằng Ctrl+C.
#
# Cách dùng:  bash frontend/dev-local.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
SHIM="${TMPDIR:-/tmp}/p053-media-shim"

# SQLite thay cho PostgreSQL: biến môi trường luôn thắng giá trị trong .env
export DATABASE_URL="sqlite:///./data/app.db"
export AUTO_LOAD_EVAL_DATA="false"
export MEDIA_ROOT="./data/media"

# ---- 1. Python venv ----
if [ -x "$BACKEND/.venv/bin/python" ]; then
  PY="$BACKEND/.venv/bin/python"
elif [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
else
  echo "==> Tạo backend/.venv (chỉ chạy lần đầu, mất vài phút)"
  python3 -m venv "$BACKEND/.venv"
  "$BACKEND/.venv/bin/python" -m pip install --quiet --upgrade pip
  "$BACKEND/.venv/bin/python" -m pip install -r "$BACKEND/requirements.txt"
  PY="$BACKEND/.venv/bin/python"
fi
echo "==> Python: $PY"

# ---- 1b. Cổng có đang bị tiến trình cũ chiếm không ----
# Chạy script lần hai khi lần một chưa tắt hẳn là chuyện rất hay xảy ra. Khi đó uvicorn
# không bind được cổng 8000 và chết lặng lẽ, còn Vite tự nhảy sang 3001 — nhìn thì web
# vẫn lên nhưng thực chất đang nói chuyện với backend của lần chạy trước. Báo rõ ngay đây.
for port in 8000 3000; do
  holder="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | head -1 || true)"
  if [ -n "$holder" ]; then
    echo "!!  Cổng $port đang bị tiến trình $holder chiếm (có thể là lần chạy trước chưa tắt)."
    echo "!!  Tắt nó rồi chạy lại:   kill $holder"
    exit 1
  fi
done

mkdir -p "$BACKEND/data" "$BACKEND/logs"

# ---- 1c. Cảnh báo key LLM còn là chuỗi mẫu ----
# Luồng đặt lịch (bấm nút) KHÔNG cần key. Nhưng gõ tin nhắn tự do cho ViVi thì cần, và khi
# key là chuỗi mẫu, backend trả "Đã xảy ra lỗi khi kết nối với mô hình AI" — rất dễ bị hiểu
# nhầm thành mất kết nối backend. Nói trước để khỏi mất công đi tìm.
llm_key="$(grep -E '^(OPENAI_API_KEY|OPENROUTER_API_KEY)=' "$ROOT/.env" 2>/dev/null | cut -d= -f2- | grep -v '^$' | grep -v 'your-key-here\|your-key\|sk-or-v1-your' || true)"
if [ -z "$llm_key" ]; then
  echo "!!  Chưa có OPENAI_API_KEY / OPENROUTER_API_KEY thật trong .env"
  echo "!!  Bấm nút để đặt lịch thì VẪN CHẠY. Chỉ chat tự do với ViVi mới báo lỗi mô hình AI."
fi

# ---- 2. Seed dữ liệu showroom/xe/khung giờ (bỏ qua nếu DB đã có) ----
echo "==> Seed database"
(cd "$BACKEND" && "$PY" scripts/seed_dev_db.py)

# ---- 3. Copy ảnh xe sang media origin của backend ----
# TODO [BACKEND/MEDIA]: backend/scripts/publish_site_media.py còn trỏ tới layout cũ
# (frontend/"Ảnh xe vinfast" và frontend/src/assets). Media hiện nằm ở
# frontend/src/media/local/{vehicle-media,common}. Shim dưới đây chỉ là workaround
# tạm; backend nên cập nhật đường dẫn nguồn trong script.
if [ ! -f "$BACKEND/data/media/content/home/hero.webp" ]; then
  echo "==> Publish media"
  rm -rf "$SHIM"
  mkdir -p "$SHIM/src"
  ln -s "$FRONTEND/src/media/local/vehicle-media" "$SHIM/Ảnh xe vinfast"
  ln -s "$FRONTEND/src/media/local/common" "$SHIM/src/assets"
  (cd "$BACKEND" && "$PY" scripts/publish_site_media.py "$SHIM" data/media)
fi

# ---- 3b. Đẩy ảnh ghi đè theo mã xe (src/media/local/by-model/) sang kho media backend ----
# Chỉ ghi vào backend/data/media — dữ liệu sinh lúc chạy, đã nằm trong .gitignore.
echo "==> Áp dụng ảnh ghi đè theo mã xe"
(cd "$FRONTEND" && node scripts/apply-model-overrides.mjs)

# ---- 4. Chạy backend + frontend ----
echo "==> Backend  http://localhost:8000  (docs: /docs)"
(cd "$BACKEND" && exec "$PY" -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000) &
BACKEND_PID=$!

cleanup() { echo; echo "==> Dừng backend"; kill "$BACKEND_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

sleep 3
echo "==> Frontend http://localhost:3000"
(cd "$FRONTEND" && npm run dev)
