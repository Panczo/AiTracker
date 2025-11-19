import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

const LineDrawing = ({ jobId, onLineSet, onSkip }) => {
  const [previewFrame, setPreviewFrame] = useState(null);
  const [frameSize, setFrameSize] = useState({ width: 0, height: 0 });
  const [line, setLine] = useState(null); // {p1: {x, y}, p2: {x, y}}
  const [drawing, setDrawing] = useState(false);
  const [currentPoint, setCurrentPoint] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [enableAnonymization, setEnableAnonymization] = useState(false);

  const canvasRef = useRef(null);

  useEffect(() => {
    fetchPreviewFrame();
  }, [jobId]);

  useEffect(() => {
    if (previewFrame && canvasRef.current) {
      drawCanvas();
    }
  }, [previewFrame, line, currentPoint]);

  const fetchPreviewFrame = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/preview/${jobId}`);
      setPreviewFrame(response.data.frame);
      setFrameSize({ width: response.data.width, height: response.data.height });
      setLoading(false);
    } catch (err) {
      setError(err.response?.data?.detail || 'Nie można pobrać podglądu');
      setLoading(false);
    }
  };

  const drawCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas || !previewFrame) return;

    const ctx = canvas.getContext('2d');

    // Load and draw image
    const img = new Image();
    img.onload = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      // Draw existing line
      if (line) {
        ctx.strokeStyle = '#FF0000';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(line.p1.x, line.p1.y);
        ctx.lineTo(line.p2.x, line.p2.y);
        ctx.stroke();

        // Draw points
        ctx.fillStyle = '#FF0000';
        ctx.beginPath();
        ctx.arc(line.p1.x, line.p1.y, 6, 0, 2 * Math.PI);
        ctx.fill();
        ctx.beginPath();
        ctx.arc(line.p2.x, line.p2.y, 6, 0, 2 * Math.PI);
        ctx.fill();

        // Draw arrow to indicate direction
        drawArrow(ctx, line.p1, line.p2);
      }

      // Draw current drawing line
      if (drawing && currentPoint) {
        ctx.strokeStyle = '#00FF00';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.moveTo(currentPoint.x, currentPoint.y);
        const canvas = canvasRef.current;
        const rect = canvas.getBoundingClientRect();
        // This would need mouse position, simplified for now
        ctx.stroke();
        ctx.setLineDash([]);
      }
    };
    img.src = `data:image/jpeg;base64,${previewFrame}`;
  };

  const drawArrow = (ctx, from, to) => {
    const headlen = 15;
    const angle = Math.atan2(to.y - from.y, to.x - from.x);

    ctx.strokeStyle = '#FF0000';
    ctx.fillStyle = '#FF0000';
    ctx.lineWidth = 3;

    // Draw arrowhead
    ctx.beginPath();
    ctx.moveTo(to.x, to.y);
    ctx.lineTo(
      to.x - headlen * Math.cos(angle - Math.PI / 6),
      to.y - headlen * Math.sin(angle - Math.PI / 6)
    );
    ctx.lineTo(
      to.x - headlen * Math.cos(angle + Math.PI / 6),
      to.y - headlen * Math.sin(angle + Math.PI / 6)
    );
    ctx.closePath();
    ctx.fill();
  };

  const getCanvasCoords = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    };
  };

  const handleMouseDown = (e) => {
    if (line) return; // Already have a line

    const coords = getCanvasCoords(e);
    setDrawing(true);
    setCurrentPoint(coords);
  };

  const handleMouseUp = (e) => {
    if (!drawing) return;

    const coords = getCanvasCoords(e);
    setLine({
      p1: currentPoint,
      p2: coords,
    });
    setDrawing(false);
    setCurrentPoint(null);
  };

  const handleClearLine = () => {
    setLine(null);
    setDrawing(false);
    setCurrentPoint(null);
  };

  const handleSaveLine = async () => {
    if (!line) {
      setError('Narysuj linię przed zapisaniem');
      return;
    }

    try {
      setSaving(true);
      setError(null);

      // Save line
      await axios.post(`/api/set-line/${jobId}`, line);

      // Save options
      await axios.post(`/api/set-options/${jobId}`,
        new URLSearchParams({ enable_anonymization: enableAnonymization }),
        {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        }
      );

      onLineSet(line, enableAnonymization);
    } catch (err) {
      setError(err.response?.data?.detail || 'Błąd podczas zapisywania linii');
    } finally {
      setSaving(false);
    }
  };

  const handleSkipLine = async () => {
    try {
      // Save options without line
      await axios.post(`/api/set-options/${jobId}`,
        new URLSearchParams({ enable_anonymization: enableAnonymization }),
        {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        }
      );

      onSkip(enableAnonymization);
    } catch (err) {
      setError('Błąd podczas pomijania linii');
    }
  };

  if (loading) {
    return (
      <div className="card">
        <div className="spinner"></div>
        <p style={{ textAlign: 'center', color: '#666' }}>Ładowanie podglądu...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="error">{error}</div>
        <button className="btn btn-secondary" onClick={onSkip} style={{ marginTop: '10px' }}>
          Pomiń i kontynuuj
        </button>
      </div>
    );
  }

  return (
    <div className="card">
      <h2 style={{ marginBottom: '20px', color: '#333' }}>
        📏 Narysuj linię zliczającą
      </h2>

      <div className="info" style={{ marginBottom: '20px' }}>
        <p>Narysuj linię na obrazie - pojazdy będą zliczane tylko gdy przejadą przez tę linię.</p>
        <p style={{ marginTop: '5px' }}>
          <strong>Instrukcja:</strong> Kliknij i przeciągnij, aby narysować linię. Strzałka wskazuje kierunek zliczania.
        </p>
      </div>

      <div style={{ position: 'relative', display: 'inline-block', marginBottom: '20px' }}>
        <canvas
          ref={canvasRef}
          width={frameSize.width}
          height={frameSize.height}
          onMouseDown={handleMouseDown}
          onMouseUp={handleMouseUp}
          style={{
            border: '2px solid #667eea',
            borderRadius: '8px',
            cursor: line ? 'default' : 'crosshair',
            maxWidth: '100%',
            height: 'auto',
          }}
        />
      </div>

      <div style={{ marginBottom: '20px' }}>
        <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={enableAnonymization}
            onChange={(e) => setEnableAnonymization(e.target.checked)}
            style={{ marginRight: '10px', width: '18px', height: '18px' }}
          />
          <span style={{ color: '#333' }}>
            <strong>Włącz anonimizację</strong> (rozmycie tablic rejestracyjnych)
          </span>
        </label>
      </div>

      <div style={{ display: 'flex', gap: '10px' }}>
        {line && (
          <>
            <button
              className="btn btn-secondary"
              onClick={handleClearLine}
              disabled={saving}
            >
              Wyczyść linię
            </button>
            <button
              className="btn btn-primary"
              onClick={handleSaveLine}
              disabled={saving}
            >
              {saving ? 'Zapisywanie...' : 'Zapisz i kontynuuj'}
            </button>
          </>
        )}
        {!line && (
          <button
            className="btn btn-secondary"
            onClick={handleSkipLine}
          >
            Pomiń linię (zliczaj wszystko)
          </button>
        )}
      </div>
    </div>
  );
};

export default LineDrawing;
