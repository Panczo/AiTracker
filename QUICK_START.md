# 🚀 Quick Start Guide

## Szybkie uruchomienie aplikacji

### Linux/Mac

Otwórz **dwa terminale** i uruchom:

**Terminal 1 - Backend:**
```bash
./start_backend.sh
```

**Terminal 2 - Frontend:**
```bash
./start_frontend.sh
```

### Windows

Uruchom **dwa pliki bat**:

1. Dwukrotnie kliknij: `start_backend.bat`
2. Dwukrotnie kliknij: `start_frontend.bat`

---

## 🌐 Adresy

- **Frontend (aplikacja)**: http://localhost:3000
- **Backend (API)**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 📝 Pierwsze użycie

1. Otwórz przeglądarkę: http://localhost:3000
2. Przeciągnij plik wideo (MP4/AVI/MOV/MKV) do okna uploadu
3. Poczekaj na zakończenie przetwarzania (progress bar pokazuje postęp)
4. Pobierz wyniki:
   - Wideo z zaznaczonymi pojazdami
   - Raport CSV z danymi

---

## ⚙️ Wymagania

- Python 3.10+
- Node.js 18+
- 4GB+ RAM
- ~5GB wolnego miejsca

---

## 🆘 Problemy?

Sprawdź pełną dokumentację w [README.md](README.md)

### Częste problemy:

**Backend nie startuje:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# lub
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

**Frontend nie startuje:**
```bash
cd frontend
npm install
npm run dev
```

---

**Gotowe! 🎉** Aplikacja działa na http://localhost:3000
