# 🚗 AiTracker - System Detekcji i Klasyfikacji Pojazdów

System automatycznej detekcji i klasyfikacji pojazdów z nagrań wideo wykorzystujący **YOLOv11** i algorytm śledzenia **BoT-SORT**.

## 📋 Funkcjonalności

### Podstawowe
- ✅ Detekcja i śledzenie pojazdów z YOLOv11 + BoT-SORT
- ✅ Klasyfikacja 8+1 kategorii pojazdów:
  - Motocykle, Samochody osobowe, Dostawcze, Ciężarowe
  - Autobusy, Rowery, Ciągniki, Przyczepy, Inne
- ✅ Line crossing detection - zliczanie tylko w wybranym kierunku
- ✅ Real-time progress tracking przez WebSocket

### Batch Processing
- ✅ Upload wielu plików naraz (do 24h materiału)
- ✅ Automatyczna kontynuacja czasu między plikami
- ✅ Przetwarzanie sekwencyjne z cumulative tracking
- ✅ Typowo: 288 plików × 5 min = 24h nagrań

### Raporty i Wyniki
- ✅ **Raport 5-minutowy**: CSV z podziałem na godziny i 5-min przedziały
- ✅ Export wideo z zaznaczonymi pojazdami (bounding boxes + linia)
- ✅ Statystyki per typ pojazdu
- ✅ Format: `Godzina | Przedział | Czas_Od | Czas_Do | [Typy] | SUMA`

### Dodatkowe
- ✅ Opcjonalna anonimizacja (blur tablic rejestracyjnych)
- ✅ Aplikacja webowa z 4-stopniowym workflow
- ✅ Interaktywne rysowanie linii zliczającej na canvas

## 🏗️ Architektura

- **Backend**: FastAPI + Python 3.10+
- **Frontend**: React + Vite
- **AI**: YOLOv11 (Ultralytics) + BoT-SORT tracking
- **Database**: SQLite
- **WebSocket**: Real-time status updates

## 📁 Struktura projektu

```
AiTracker/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI endpoints + WebSocket
│   │   ├── processor.py      # Video processing pipeline
│   │   ├── tracker.py        # YOLO detection + tracking
│   │   ├── models.py         # SQLAlchemy models
│   │   └── config.py         # Configuration
│   ├── storage/
│   │   ├── uploads/          # Temporary uploaded videos
│   │   ├── processed/        # Output videos & CSV
│   │   └── models/           # YOLO model files
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Upload.jsx
│   │   │   ├── ProcessingStatus.jsx
│   │   │   └── Results.jsx
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── package.json
└── README.md
```

## 🚀 Instalacja i uruchomienie

### Wymagania wstępne

- Python 3.10 lub nowszy
- Node.js 18+ i npm
- Co najmniej 4GB RAM (8GB+ zalecane)
- Wolne miejsce na dysku: ~5GB (modele YOLO + storage)

### 1. Klonowanie repozytorium

```bash
git clone <repository-url>
cd AiTracker
```

### 2. Backend Setup

```bash
cd backend

# Utwórz wirtualne środowisko
python -m venv venv

# Aktywuj środowisko
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Zainstaluj zależności
pip install -r requirements.txt

# Uruchom backend
cd app
python main.py
```

Backend będzie dostępny pod adresem: `http://localhost:8000`

### 3. Frontend Setup

W nowym terminalu:

```bash
cd frontend

# Zainstaluj zależności
npm install

# Uruchom frontend
npm run dev
```

Frontend będzie dostępny pod adresem: `http://localhost:3000`

## 💻 Użytkowanie

### Workflow (4 kroki)

1. **📦 Upload wielu plików**
   - Przeciągnij wiele plików MP4 (do 24h łącznie)
   - System waliduje rozmiar i czas trwania
   - Typowo: ~288 plików × 5 min = 24h

2. **📏 Narysuj linię zliczającą**
   - Na pierwszej klatce wideo narysuj linię
   - Strzałka wskazuje kierunek zliczania
   - Opcja: włącz anonimizację tablic
   - Można pominąć (zlicza wszystko)

3. **⚙️ Przetwarzanie**
   - Real-time progress przez WebSocket
   - Status per plik + ogólny postęp
   - Automatyczne przejście między plikami

4. **📊 Wyniki**
   - Pobierz raport CSV (5-min przedziały)
   - Statystyki per typ pojazdu
   - Wykresy i podsumowania

### Format raportu CSV (5-minutowe przedziały)

```csv
Godzina,Przedzial,Czas_Od,Czas_Do,Motocykl,Samochód Osobowy,Samochód Dostawczy,Samochód Ciężarowy,Autobus,Rower,Ciągnik,Przyczepa,Inne,SUMA
0,1,0:00:00,0:05:00,5,120,15,8,2,10,1,0,3,164
0,2,0:05:00,0:10:00,3,98,12,5,1,8,0,1,2,130
0,3,0:10:00,0:15:00,7,115,18,9,3,12,2,1,4,171
...
23,12,23:55:00,24:00:00,4,89,10,4,0,6,1,0,1,115
```

**Kolumny:**
- `Godzina`: Numer godziny (0-23)
- `Przedzial`: Numer 5-min przedziału w godzinie (1-12)
- `Czas_Od` / `Czas_Do`: Zakres czasowy
- `[Typy pojazdów]`: Liczba pojazdów każdego typu
- `SUMA`: Łączna liczba pojazdów w przedziale

## 🔧 Konfiguracja

Edytuj `backend/app/config.py` aby dostosować:

- `MAX_FILE_SIZE_MB`: Maksymalny rozmiar pliku (domyślnie 250MB)
- `YOLO_MODEL`: Model YOLO (domyślnie yolo11n.pt dla CPU)
- `YOLO_CONFIDENCE`: Próg pewności detekcji (domyślnie 0.25)
- `FRAME_SKIP`: Przetwarzaj co N-tą klatkę (1 = wszystkie klatki)

### Optymalizacja dla GPU

Jeśli masz GPU NVIDIA z CUDA:

```bash
# Zainstaluj PyTorch z CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Zmień model na większy dla lepszej dokładności
# w config.py: YOLO_MODEL = "yolo11m.pt" lub "yolo11l.pt"
```

## 📊 API Endpoints

### REST API

**Upload & Configuration:**
- `POST /api/upload` - Upload pojedynczego pliku (legacy)
- `POST /api/upload-batch` - Upload wielu plików (batch)
- `GET /api/preview/{job_id}` - Pobierz pierwszą klatkę (base64 JPEG)
- `POST /api/set-line/{job_id}` - Ustaw linię zliczającą
- `POST /api/set-options/{job_id}` - Ustaw opcje (anonimizacja)

**Processing & Status:**
- `POST /api/process/{job_id}` - Rozpocznij przetwarzanie
- `GET /api/status/{job_id}` - Pobierz status zadania

**Download:**
- `GET /api/download/{job_id}/csv` - Pobierz raport CSV (5-min)
- `DELETE /api/job/{job_id}` - Usuń zadanie i pliki

### WebSocket

- `WS /ws/{job_id}` - Real-time status updates
  - Progress (%)
  - Current step
  - Files processed (batch)
  - Frame counts

## ✨ Zrealizowane funkcjonalności

- [x] Fine-tuning ready (gotowy do treningu na własnym datasecie)
- [x] Wykrywanie kierunku ruchu pojazdów (line crossing)
- [x] Liczenie pojazdów przecinających linię
- [x] Obsługa wielu nagrań jednocześnie (batch do 24h)
- [x] Export CSV z 5-minutowymi przedziałami
- [x] Anonimizacja tablic rejestracyjnych
- [x] WebSocket real-time tracking

## 🎯 Potencjalne rozszerzenia

- [ ] Excel export (aktualnie CSV)
- [ ] Wykresy wizualizacyjne w interfejsie
- [ ] Heatmapy ruchu pojazdów
- [ ] Detekcja prędkości
- [ ] Autentykacja użytkowników
- [ ] Historia przetwarzanych nagrań
- [ ] Dashboard z statystykami

## 🔍 Fine-tuning modelu

Aby poprawić dokładność klasyfikacji dla specyficznych warunków drogowych:

### 1. Przygotuj dataset

```
dataset/
├── images/
│   ├── train/
│   ├── val/
│   └── test/
└── labels/
    ├── train/
    ├── val/
    └── test/
```

### 2. Stwórz plik konfiguracyjny `data.yaml`

```yaml
path: ./dataset
train: images/train
val: images/val
test: images/test

nc: 9  # number of classes
names: ['rower', 'samochod_osobowy', 'motocykl', 'samochod_dostawczy',
        'autobus', 'samochod_ciezarowy', 'ciagnik', 'przyczepa', 'inne']
```

### 3. Trenuj model

```python
from ultralytics import YOLO

# Załaduj pretrenowany model
model = YOLO('yolo11n.pt')

# Trenuj
results = model.train(
    data='data.yaml',
    epochs=100,
    imgsz=640,
    batch=16,
    name='vehicle_classifier'
)

# Zapisz model
model.save('vehicle_classifier.pt')
```

### 4. Użyj wytrenowanego modelu

W `config.py`:
```python
YOLO_MODEL = "vehicle_classifier.pt"
```

## 🐛 Troubleshooting

### Problem: Wolne przetwarzanie na CPU

**Rozwiązanie**:
- Użyj mniejszego modelu: `yolo11n.pt` (nano)
- Zwiększ `FRAME_SKIP` w config.py (np. do 2 lub 3)
- Zmniejsz rozdzielczość wideo przed uploadem

### Problem: Błąd "Out of memory"

**Rozwiązanie**:
- Zmniejsz `batch_size` w tracking (domyślnie 1 dla CPU)
- Zwiększ `FRAME_SKIP`
- Zmniejsz rozdzielczość wideo

### Problem: Nieprawidłowa klasyfikacja ciężarówek

**Rozwiązanie**:
- Fine-tune model na własnym datasecie
- Dodaj klasyfikację opartą na rozmiarze bounding boxa w `tracker.py`

## 📝 Licencja

MIT License

## 🤝 Współpraca

Zgłaszanie błędów i propozycje ulepszeń mile widziane!

## 📧 Kontakt

W razie pytań lub problemów, utwórz issue w repozytorium.

---

**Powered by YOLOv11 & Ultralytics** 🚀
