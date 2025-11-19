import React, { useState, useRef } from 'react';
import axios from 'axios';

const Upload = ({ onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

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

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleFileInputChange = (e) => {
    if (e.target.files.length > 0) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const handleFileSelect = (file) => {
    setError(null);

    // Validate file type
    const allowedTypes = ['video/mp4', 'video/avi', 'video/quicktime', 'video/x-matroska'];
    if (!allowedTypes.includes(file.type) && !file.name.match(/\.(mp4|avi|mov|mkv)$/i)) {
      setError('Nieprawidłowy format pliku. Dozwolone: MP4, AVI, MOV, MKV');
      return;
    }

    // Validate file size (250MB)
    const maxSize = 250 * 1024 * 1024;
    if (file.size > maxSize) {
      setError('Plik zbyt duży. Maksymalny rozmiar: 250MB');
      return;
    }

    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await axios.post('/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      onUploadSuccess(response.data.job_id, selectedFile.name);
      setSelectedFile(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Błąd podczas uploadu pliku');
    } finally {
      setIsUploading(false);
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="card">
      <h2 style={{ marginBottom: '20px', color: '#333' }}>
        📤 Prześlij nagranie wideo
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
          <h3>Przeciągnij plik wideo tutaj</h3>
          <p>lub kliknij, aby wybrać plik</p>
          <p style={{ fontSize: '0.85rem', marginTop: '10px', color: '#999' }}>
            Maksymalny rozmiar: 250MB | Formaty: MP4, AVI, MOV, MKV
          </p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          className="file-input"
          accept="video/mp4,video/avi,video/quicktime,video/x-matroska,.mp4,.avi,.mov,.mkv"
          onChange={handleFileInputChange}
        />
      </div>

      {selectedFile && (
        <div className="file-info">
          <p><strong>Wybrany plik:</strong> {selectedFile.name}</p>
          <p><strong>Rozmiar:</strong> {formatFileSize(selectedFile.size)}</p>
          <button
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={isUploading}
            style={{ marginTop: '15px' }}
          >
            {isUploading ? 'Przesyłanie...' : 'Prześlij i rozpocznij przetwarzanie'}
          </button>
        </div>
      )}
    </div>
  );
};

export default Upload;
