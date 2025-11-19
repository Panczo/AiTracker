import React, { useState, useEffect } from 'react';
import axios from 'axios';

const Results = ({ jobId }) => {
  const [status, setStatus] = useState(null);
  const [vehicleCounts, setVehicleCounts] = useState(null);

  useEffect(() => {
    if (!jobId) return;
    fetchStatus();
  }, [jobId]);

  const fetchStatus = async () => {
    try {
      const response = await axios.get(`/api/status/${jobId}`);
      setStatus(response.data);

      if (response.data.vehicle_counts) {
        try {
          const counts = JSON.parse(response.data.vehicle_counts);
          setVehicleCounts(counts);
        } catch (e) {
          console.error('Error parsing vehicle counts:', e);
        }
      }
    } catch (err) {
      console.error('Error fetching status:', err);
    }
  };

  const handleDownloadVideo = () => {
    window.open(`/api/download/${jobId}/video`, '_blank');
  };

  const handleDownloadCSV = () => {
    window.open(`/api/download/${jobId}/csv`, '_blank');
  };

  const getVehicleTypeLabel = (type) => {
    const labels = {
      'motocykl': 'Motocykle',
      'samochod_osobowy': 'Samochody osobowe',
      'samochod_dostawczy': 'Samochody dostawcze',
      'samochod_ciezarowy': 'Samochody ciężarowe',
      'autobus': 'Autobusy',
      'rower': 'Rowery',
      'ciagnik': 'Ciągniki',
      'przyczepa': 'Przyczepy',
      'inne': 'Inne',
    };
    return labels[type] || type;
  };

  if (!status) {
    return null;
  }

  if (status.status !== 'completed') {
    return null;
  }

  return (
    <div className="card">
      <h2 style={{ marginBottom: '20px', color: '#333' }}>
        🎯 Wyniki analizy
      </h2>

      <div className="results-grid">
        <div className="result-card">
          <h4>Wszystkie pojazdy</h4>
          <div className="value">{status.total_vehicles || 0}</div>
        </div>

        {vehicleCounts && Object.keys(vehicleCounts).length > 0 && (
          Object.entries(vehicleCounts).map(([type, count]) => (
            <div className="result-card" key={type}>
              <h4>{getVehicleTypeLabel(type)}</h4>
              <div className="value">{count}</div>
            </div>
          ))
        )}
      </div>

      {vehicleCounts && Object.keys(vehicleCounts).length > 0 && (
        <div className="vehicle-counts">
          <h3>Szczegółowy rozkład pojazdów</h3>
          <div className="vehicle-list">
            {Object.entries(vehicleCounts)
              .sort((a, b) => b[1] - a[1])
              .map(([type, count]) => (
                <div className="vehicle-item" key={type}>
                  <div className="type">{getVehicleTypeLabel(type)}</div>
                  <div className="count">{count}</div>
                </div>
              ))}
          </div>
        </div>
      )}

      <div className="download-buttons">
        <button className="btn btn-primary" onClick={handleDownloadVideo}>
          📹 Pobierz wideo z detekcją
        </button>
        <button className="btn btn-primary" onClick={handleDownloadCSV}>
          📊 Pobierz raport CSV
        </button>
      </div>

      <div className="info" style={{ marginTop: '20px' }}>
        💡 Raport CSV zawiera szczegółowe informacje o każdym wykrytym pojeździe:
        ID, typ, pewność detekcji, czas pojawienia się i zniknięcia.
      </div>
    </div>
  );
};

export default Results;
