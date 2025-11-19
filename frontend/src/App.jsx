import React, { useState } from 'react';
import Upload from './components/Upload';
import ProcessingStatus from './components/ProcessingStatus';
import Results from './components/Results';

function App() {
  const [currentJobId, setCurrentJobId] = useState(null);
  const [currentFilename, setCurrentFilename] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);

  const handleUploadSuccess = (jobId, filename) => {
    setCurrentJobId(jobId);
    setCurrentFilename(filename);
    setIsProcessing(true);
    setIsCompleted(false);
  };

  const handleProcessingComplete = () => {
    setIsProcessing(false);
    setIsCompleted(true);
  };

  const handleReset = () => {
    setCurrentJobId(null);
    setCurrentFilename(null);
    setIsProcessing(false);
    setIsCompleted(false);
  };

  return (
    <div className="container">
      <div className="header">
        <h1>🚗 AiTracker</h1>
        <p>System detekcji i klasyfikacji pojazdów z użyciem YOLOv11</p>
      </div>

      {!currentJobId && <Upload onUploadSuccess={handleUploadSuccess} />}

      {currentJobId && isProcessing && (
        <ProcessingStatus
          jobId={currentJobId}
          filename={currentFilename}
          onComplete={handleProcessingComplete}
        />
      )}

      {currentJobId && isCompleted && (
        <>
          <Results jobId={currentJobId} />

          <div style={{ textAlign: 'center', marginTop: '30px' }}>
            <button className="btn btn-primary" onClick={handleReset}>
              ➕ Przetwórz kolejne nagranie
            </button>
          </div>
        </>
      )}

      <div className="card" style={{ marginTop: '40px', background: '#f8f9ff' }}>
        <h3 style={{ marginBottom: '15px', color: '#333' }}>
          ℹ️ Informacje o systemie
        </h3>
        <ul style={{ color: '#666', lineHeight: '1.8' }}>
          <li>Model: YOLOv11 z algorytmem śledzenia BoT-SORT</li>
          <li>Klasyfikacja: 8+1 kategorii pojazdów</li>
          <li>Format wyjściowy: Wideo z zaznaczonymi pojazdami + raport CSV</li>
          <li>Maksymalny rozmiar pliku: 250 MB</li>
          <li>Obsługiwane formaty: MP4, AVI, MOV, MKV</li>
        </ul>
      </div>

      <div style={{ textAlign: 'center', marginTop: '30px', color: 'white', opacity: 0.8 }}>
        <p>© 2024 AiTracker - Powered by YOLOv11 & FastAPI</p>
      </div>
    </div>
  );
}

export default App;
