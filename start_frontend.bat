@echo off

echo Uruchamianie AiTracker Frontend...

cd frontend

REM Sprawdz czy node_modules istnieje
if not exist "node_modules\" (
    echo Instalowanie zaleznosci npm...
    npm install
)

REM Uruchom dev server
echo Uruchamianie React dev serwera na http://localhost:3000
npm run dev

pause
