#!/bin/bash

echo "🚀 Uruchamianie AiTracker Frontend..."

cd frontend

# Sprawdź czy node_modules istnieje
if [ ! -d "node_modules" ]; then
    echo "📦 Instalowanie zależności npm..."
    npm install
fi

# Uruchom dev server
echo "✅ Uruchamianie React dev serwera na http://localhost:3000"
npm run dev
