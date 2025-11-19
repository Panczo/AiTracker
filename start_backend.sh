#!/bin/bash

echo "🚀 Uruchamianie AiTracker Backend..."

cd backend

# Sprawdź czy venv istnieje
if [ ! -d "venv" ]; then
    echo "📦 Tworzenie wirtualnego środowiska..."
    python3 -m venv venv
fi

# Aktywuj venv
echo "🔧 Aktywowanie środowiska..."
source venv/bin/activate

# Instaluj zależności
echo "📥 Instalowanie zależności..."
pip install -r requirements.txt

# Uruchom serwer
echo "✅ Uruchamianie FastAPI serwera na http://localhost:8000"
cd app
python main.py
