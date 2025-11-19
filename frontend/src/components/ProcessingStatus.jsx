import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const ProcessingStatus = ({ jobId, filename, onComplete }) => {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    if (!jobId) return;

    // Fetch initial status
    fetchStatus();

    // Connect WebSocket
    connectWebSocket();

    // Start processing
    startProcessing();

    // Cleanup
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [jobId]);

  const fetchStatus = async () => {
    try {
      const response = await axios.get(`/api/status/${jobId}`);
      setStatus(response.data);
    } catch (err) {
      console.error('Error fetching status:', err);
    }
  };

  const connectWebSocket = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.hostname}:${window.location.port}/ws/${jobId}`;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('WebSocket message:', data);

      setStatus((prevStatus) => ({
        ...prevStatus,
        ...data,
      }));

      if (data.status === 'completed') {
        onComplete();
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };

    wsRef.current = ws;
  };

  const startProcessing = async () => {
    try {
      await axios.post(`/api/process/${jobId}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Błąd podczas rozpoczynania przetwarzania');
    }
  };

  if (!status) {
    return (
      <div className="card">
        <div className="spinner"></div>
        <p style={{ textAlign: 'center', color: '#666' }}>Ładowanie...</p>
      </div>
    );
  }

  const getStatusBadge = () => {
    const statusMap = {
      uploaded: { class: 'status-uploaded', text: 'Przesłano' },
      processing: { class: 'status-processing', text: 'Przetwarzanie' },
      completed: { class: 'status-completed', text: 'Zakończono' },
      failed: { class: 'status-failed', text: 'Błąd' },
    };

    const statusInfo = statusMap[status.status] || { class: '', text: status.status };
    return <span className={`status-badge ${statusInfo.class}`}>{statusInfo.text}</span>;
  };

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2 style={{ color: '#333' }}>📊 Status przetwarzania</h2>
        {getStatusBadge()}
      </div>

      {error && <div className="error">{error}</div>}

      <div className="file-info">
        <p><strong>Plik:</strong> {filename}</p>
        <p><strong>ID zadania:</strong> {jobId}</p>
      </div>

      {status.status === 'processing' && (
        <div className="progress-container">
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${status.progress || 0}%` }}
            >
              {Math.round(status.progress || 0)}%
            </div>
          </div>
          <p className="progress-text">
            {status.current_step || 'Przetwarzanie...'}
          </p>
          {status.processed_frames && status.total_frames && (
            <p className="progress-text">
              Klatki: {status.processed_frames} / {status.total_frames}
            </p>
          )}
        </div>
      )}

      {status.status === 'completed' && (
        <div className="info" style={{ marginTop: '20px' }}>
          ✅ Przetwarzanie zakończone pomyślnie!
        </div>
      )}

      {status.status === 'failed' && status.error_message && (
        <div className="error" style={{ marginTop: '20px' }}>
          ❌ {status.error_message}
        </div>
      )}
    </div>
  );
};

export default ProcessingStatus;
