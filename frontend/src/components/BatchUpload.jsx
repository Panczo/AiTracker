import React, { useState, useRef } from 'react';
import axios from 'axios';

const BatchUpload = ({ onUploadSuccess }) => {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const MAX_TOTAL_HOURS = 24;
  const MAX_TOTAL_SECONDS = MAX_TOTAL_HOURS * 3600;

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    handleFilesSelected(files);
  };

  const handleFileInputChange = (e) => {
    const files = Array.from(e.target.files);
    handleFilesSelected(files);
  };

  const handleFilesSelected = (files) => {
    setError(null);

    // Validate file types
    const allowedTypes = ['video/mp4', 'video/avi', 'video/quicktime', 'video/x-matroska'];
    const invalidFiles = files.filter(
      file => !allowedTypes.includes(file.type) && !file.name.match(/\.(mp4|avi|mov|mkv)$/i)
    );

    if (invalidFiles.length > 0) {
      setError(`Nieprawidłowe pliki: ${invalidFiles.map(f => f.name).join(', ')}`);
      return;
    }

    // Validate file size (250MB each)
    const maxFileSize = 250 * 1024 * 1024;
    const oversizedFiles = files.filter(file => file.size > maxFileSize);

    if (oversizedFiles.length > 0) {
      setError(`Pliki zbyt duże (max 250MB): ${oversizedFiles.map(f => f.name).join(', ')}`);
      return;
    }

    setSelectedFiles(prev => [...prev, ...files]);
  };

  const removeFile = (index) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const getTotalDuration = () => {
    // Estimate: 5 minutes per file (can be updated after upload)
    return selectedFiles.length * 5 * 60;
  };

  const getTotalSize = () => {
    return selectedFiles.reduce((sum, file) => sum + file.size, 0);
  };

  const formatSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDuration = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}min`;
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      setError('Wybierz co najmniej jeden plik');
      return;
    }

    // Estimate total duration
    const estimatedDuration = getTotalDuration();
    if (estimatedDuration > MAX_TOTAL_SECONDS) {
      setError(`Szacowany czas przekracza ${MAX_TOTAL_HOURS}h. Usuń część plików.`);
      return;
    }

    setIsUploading(true);
    setError(null);

    const formData = new FormData();
    selectedFiles.forEach(file => {
      formData.append('files', file);
    });

    try {
      const response = await axios.post('/api/upload-batch', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          console.log('Upload progress:', percentCompleted);
        },
      });

      onUploadSuccess(response.data.job_id, selectedFiles.length, response.data.total_duration);
      setSelectedFiles([]);
    } catch (err) {
      setError(err.response?.data?.detail || 'Błąd podczas uploadu plików');
    } finally {
      setIsUploading(false);
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const totalSize = getTotalSize();
  const estimatedDuration = getTotalDuration();

  return (
    <div className="card">
      <h2 style={{ marginBottom: '20px', color: '#333' }}>
        📦 Prześlij nagrania (batch)
      </h2>

      {error && <div className="error">{error}</div>}

      <div
        className={`upload-zone ${isDragging ? 'drag-over' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
      >
        <div className="upload-icon">🎥</div>
        <div className="upload-text">
          <h3>Przeciągnij pliki wideo tutaj</h3>
          <p>lub kliknij, aby wybrać wiele plików</p>
          <p style={{ fontSize: '0.85rem', marginTop: '10px', color: '#999' }}>
            Maksymalnie {MAX_TOTAL_HOURS}h materiału | Format: MP4, AVI, MOV, MKV
          </p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          className="file-input"
          accept="video/mp4,video/avi,video/quicktime,video/x-matroska,.mp4,.avi,.mov,.mkv"
          onChange={handleFileInputChange}
          multiple
        />
      </div>

      {selectedFiles.length > 0 && (
        <div style={{ marginTop: '20px' }}>
          <h3 style={{ color: '#333', marginBottom: '10px' }}>
            Wybrane pliki ({selectedFiles.length})
          </h3>

          <div className="file-info" style={{ maxHeight: '200px', overflowY: 'auto', marginBottom: '15px' }}>
            {selectedFiles.map((file, index) => (
              <div
                key={index}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px',
                  borderBottom: '1px solid #eee',
                }}
              >
                <div style={{ flex: 1 }}>
                  <strong>{index + 1}.</strong> {file.name}
                  <span style={{ color: '#666', marginLeft: '10px', fontSize: '0.9rem' }}>
                    ({formatSize(file.size)})
                  </span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(index);
                  }}
                  style={{
                    background: '#ff4444',
                    color: 'white',
                    border: 'none',
                    padding: '5px 10px',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  Usuń
                </button>
              </div>
            ))}
          </div>

          <div className="file-info">
            <p><strong>Łączny rozmiar:</strong> {formatSize(totalSize)}</p>
            <p><strong>Szacowany czas:</strong> {formatDuration(estimatedDuration)}</p>
            {estimatedDuration > MAX_TOTAL_SECONDS && (
              <p style={{ color: '#ff4444', fontWeight: 'bold' }}>
                ⚠️ Przekroczono limit {MAX_TOTAL_HOURS}h!
              </p>
            )}
          </div>

          <button
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={isUploading || estimatedDuration > MAX_TOTAL_SECONDS}
            style={{ marginTop: '15px', width: '100%' }}
          >
            {isUploading ? 'Przesyłanie...' : `Prześlij ${selectedFiles.length} plików`}
          </button>
        </div>
      )}
    </div>
  );
};

export default BatchUpload;
