import React, { useState, useEffect } from 'react';
import axios from 'axios';

const IntervalResults = ({ jobId }) => {
  const [status, setStatus] = useState(null);
  const [intervals, setIntervals] = useState([]);
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

      // For interval data, we'd need to fetch and parse the CSV
      // For now, show summary
    } catch (err) {
      console.error('Error fetching status:', err);
    }
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
        📊 Wyniki analizy
      </h2>

      <div className="results-grid">
        <div className="result-card">
          <h4>Wszystkie pojazdy</h4>
          <div className="value">{status.total_vehicles || 0}</div>
        </div>

        {status.is_batch && (
          <div className="result-card">
            <h4>Przetworzone pliki</h4>
            <div className="value">{status.total_files || 0}</div>
          </div>
        )}

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

      <div className="info" style={{ marginTop: '20px', marginBottom: '20px' }}>
        <h3 style={{ marginBottom: '10px' }}>📋 Raport 5-minutowych przedziałów</h3>
        <p>
          Szczegółowy raport CSV zawiera dane pogrupowane według godzin i 5-minutowych przedziałów czasowych.
        </p>
        <p style={{ marginTop: '10px' }}>
          <strong>Format CSV:</strong> Godzina | Przedział | Czas od-do | [Typy pojazdów] | Suma
        </p>
      </div>

      <div className="download-buttons">
        <button className="btn btn-primary" onClick={handleDownloadCSV}>
          📊 Pobierz raport CSV (5-min przedziały)
        </button>
      </div>

      <div className="info" style={{ marginTop: '20px' }}>
        💡 <strong>Przykład raportu CSV:</strong>
        <pre style={{
          background: '#f5f5f5',
          padding: '15px',
          borderRadius: '8px',
          overflow: 'auto',
          marginTop: '10px',
          fontSize: '0.85rem',
        }}>
{`Godzina,Przedzial,Czas_Od,Czas_Do,Motocykl,Samochód Osobowy,...,SUMA
0,1,0:00:00,0:05:00,5,120,15,8,2,10,1,0,3,164
0,2,0:05:00,0:10:00,3,98,12,5,1,8,0,1,2,130
...`}
        </pre>
      </div>
    </div>
  );
};

export default IntervalResults;
