#!/usr/bin/env bash
# Launcher script untuk menjalankan YouTube Live Streaming Tool di lokal
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Buat virtualenv jika belum ada
if [ ! -d ".venv" ]; then
    echo "📦 Membuat virtual environment..."
    python3 -m venv .venv
fi

# Aktifkan venv
# shellcheck disable=SC1091
source .venv/bin/activate

# Install / upgrade dependensi
echo "📚 Menginstall dependensi..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "🚀 Menjalankan Streamlit app..."
echo "   Buka: http://localhost:8501"
echo "   Tekan Ctrl+C untuk berhenti."
echo ""

streamlit run app.py "$@"
