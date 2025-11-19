import React, { useState } from 'react';
import BatchUpload from './components/BatchUpload';
import LineDrawing from './components/LineDrawing';
import ProcessingStatus from './components/ProcessingStatus';
import IntervalResults from './components/IntervalResults';

function App() {
  const [currentJobId, setCurrentJobId] = useState(null);
  const [totalFiles, setTotalFiles] = useState(0);
  const [totalDuration, setTotalDuration] = useState(0);
  const [step, setStep] = useState('upload'); // upload, line, processing, completed

  const handleUploadSuccess = (jobId, fileCount, duration) => {
    setCurrentJobId(jobId);
    setTotalFiles(fileCount);
    setTotalDuration(duration);
    setStep('line');
  };

  const handleLineSet = (line, anonymization) => {
    setStep('processing');
  };

  const handleLineSkip = (anonymization) => {
    setStep('processing');
  };

  const handleProcessingComplete = () => {
    setStep('completed');
  };

  const handleReset = () => {
    setCurrentJobId(null);
    setTotalFiles(0);
    setTotalDuration(0);
    setStep('upload');
  };

  const formatDuration = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}min`;
  };

  return (
    <div className="container">
      <div className="header">
        <h1>🚗 AiTracker</h1>
        <p>System detekcji i klasyfikacji pojazdów - batch processing z wykrywaniem kierunku</p>
      </div>

      {/* Progress indicator */}
      {currentJobId && (
        <div className="card" style={{ background: '#f8f9ff', marginBottom: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ flex: 1, textAlign: 'center' }}>
              <div style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                background: step === 'upload' ? '#667eea' : '#4caf50',
                color: 'white',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 'bold',
              }}>
                {step === 'upload' ? '1' : '✓'}
              </div>
              <p style={{ marginTop: '8px', fontSize: '0.9rem', color: '#666' }}>Upload</p>
            </div>
            <div style={{ flex: 0.5, height: '2px', background: step !== 'upload' ? '#4caf50' : '#ddd' }} />
            <div style={{ flex: 1, textAlign: 'center' }}>
              <div style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                background: step === 'line' ? '#667eea' : step === 'processing' || step === 'completed' ? '#4caf50' : '#ddd',
                color: 'white',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 'bold',
              }}>
                {step === 'line' ? '2' : step === 'upload' ? '2' : '✓'}
              </div>
              <p style={{ marginTop: '8px', fontSize: '0.9rem', color: '#666' }}>Linia</p>
            </div>
            <div style={{ flex: 0.5, height: '2px', background: step === 'processing' || step === 'completed' ? '#4caf50' : '#ddd' }} />
            <div style={{ flex: 1, textAlign: 'center' }}>
              <div style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                background: step === 'processing' ? '#667eea' : step === 'completed' ? '#4caf50' : '#ddd',
                color: 'white',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 'bold',
              }}>
                {step === 'processing' ? '3' : step === 'completed' ? '✓' : '3'}
              </div>
              <p style={{ marginTop: '8px', fontSize: '0.9rem', color: '#666' }}>Przetwarzanie</p>
            </div>
            <div style={{ flex: 0.5, height: '2px', background: step === 'completed' ? '#4caf50' : '#ddd' }} />
            <div style={{ flex: 1, textAlign: 'center' }}>
              <div style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                background: step === 'completed' ? '#4caf50' : '#ddd',
                color: 'white',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 'bold',
              }}>
                {step === 'completed' ? '✓' : '4'}
              </div>
              <p style={{ marginTop: '8px', fontSize: '0.9rem', color: '#666' }}>Wyniki</p>
            </div>
          </div>

          {currentJobId && totalFiles > 0 && (
            <div style={{ marginTop: '15px', textAlign: 'center', color: '#666' }}>
              <p>
                <strong>Plików:</strong> {totalFiles} | <strong>Łączny czas:</strong> {formatDuration(totalDuration)}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Step 1: Upload */}
      {step === 'upload' && (
        <BatchUpload onUploadSuccess={handleUploadSuccess} />
      )}

      {/* Step 2: Line Drawing */}
      {step === 'line' && (
        <LineDrawing
          jobId={currentJobId}
          onLineSet={handleLineSet}
          onSkip={handleLineSkip}
        />
      )}

      {/* Step 3: Processing */}
      {step === 'processing' && (
        <ProcessingStatus
          jobId={currentJobId}
          filename={`${totalFiles} plików`}
          onComplete={handleProcessingComplete}
        />
      )}

      {/* Step 4: Results */}
      {step === 'completed' && (
        <>
          <IntervalResults jobId={currentJobId} />

          <div style={{ textAlign: 'center', marginTop: '30px' }}>
            <button className="btn btn-primary" onClick={handleReset}>
              ➕ Przetwórz kolejne nagrania
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
          <li>Batch processing: do 24h materiału (288 plików x 5 min)</li>
          <li>Line crossing detection: zliczanie w wybranym kierunku</li>
          <li>Raport 5-minutowy: CSV z podziałem na godziny i przedziały</li>
          <li>Opcjonalna anonimizacja tablic rejestracyjnych</li>
          <li>Obsługiwane formaty: MP4, AVI, MOV, MKV</li>
        </ul>
      </div>

      <div style={{ textAlign: 'center', marginTop: '30px', color: 'white', opacity: 0.8' }}>
        <p>© 2024 AiTracker - Powered by YOLOv11 & FastAPI</p>
      </div>
    </div>
  );
}

export default App;
