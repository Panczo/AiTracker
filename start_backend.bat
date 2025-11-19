@echo off

echo Uruchamianie AiTracker Backend...

cd backend

REM Sprawdz czy venv istnieje
if not exist "venv\" (
    echo Tworzenie wirtualnego srodowiska...
    python -m venv venv
)

REM Aktywuj venv
echo Aktywowanie srodowiska...
call venv\Scripts\activate.bat

REM Instaluj zaleznosci
echo Instalowanie zaleznosci...
pip install -r requirements.txt

REM Uruchom serwer
echo Uruchamianie FastAPI serwera na http://localhost:8000
cd app
python main.py

pause
