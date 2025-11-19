# 🚗 AiTracker - System Detekcji i Klasyfikacji Pojazdów

System automatycznej detekcji i klasyfikacji pojazdów z nagrań wideo wykorzystujący **YOLOv11** i algorytm śledzenia **BoT-SORT**.

## 📋 Funkcjonalności

- ✅ Detekcja i śledzenie pojazdów w czasie rzeczywistym
- ✅ Klasyfikacja 8+1 kategorii pojazdów:
  - Motocykle
  - Samochody osobowe
  - Samochody dostawcze
  - Samochody ciężarowe
  - Autobusy
  - Rowery
  - Ciągniki
  - Przyczepy
  - Inne
- ✅ Export wideo z zaznaczonymi pojazdami (bounding boxes)
- ✅ Raport CSV z szczegółowymi danymi (ID, typ, pewność, czasy)
- ✅ Real-time progress tracking przez WebSocket
- ✅ Aplikacja webowa z intuicyjnym interfejsem

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

1. **Upload nagrania**: Przeciągnij plik wideo (MP4, AVI, MOV, MKV) lub kliknij, aby wybrać plik
2. **Przetwarzanie**: System automatycznie rozpocznie detekcję i śledzenie pojazdów
3. **Monitorowanie**: Obserwuj postęp w czasie rzeczywistym przez WebSocket
4. **Wyniki**: Po zakończeniu pobierz:
   - Wideo z zaznaczonymi pojazdami
   - Raport CSV z danymi

### Format raportu CSV

```csv
vehicle_id,type,confidence,first_seen,last_seen,duration_seconds
1,samochod_osobowy,0.95,0:00:05,0:00:12,7.00
2,motocykl,0.89,0:00:08,0:00:15,7.00
```

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

- `POST /api/upload` - Upload pliku wideo
- `POST /api/process/{job_id}` - Rozpocznij przetwarzanie
- `GET /api/status/{job_id}` - Pobierz status zadania
- `GET /api/download/{job_id}/video` - Pobierz przetworzone wideo
- `GET /api/download/{job_id}/csv` - Pobierz raport CSV
- `DELETE /api/job/{job_id}` - Usuń zadanie

### WebSocket

- `WS /ws/{job_id}` - Real-time status updates

## 🎯 Planowane ulepszenia

- [ ] Fine-tuning modelu dla lepszej klasyfikacji ciężarówek/dostawczych
- [ ] Wykrywanie kierunku ruchu pojazdów
- [ ] Liczenie pojazdów przecinających linię
- [ ] Obsługa wielu nagrań jednocześnie (kolejka)
- [ ] Eksport do innych formatów (JSON, XML)
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
