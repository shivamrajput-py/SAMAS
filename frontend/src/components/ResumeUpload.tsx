'use client';
import React, { useRef, useState } from 'react';
import styles from './ResumeUpload.module.css';

interface Props {
  onSubmit: (file: File, urls: string[], apiKey: string, modelName: string) => void;
  isLoading: boolean;
}

export default function ResumeUpload({ onSubmit, isLoading }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [urls, setUrls] = useState<string>('');
  
  // BYOK Settings
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [modelName, setModelName] = useState('qwen/qwen3.7-plus');
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    if (event.dataTransfer.files && event.dataTransfer.files.length > 0) {
      setFile(event.dataTransfer.files[0]);
    }
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) return;
    const urlList = urls.split(',').map((url) => url.trim()).filter(Boolean);
    onSubmit(file, urlList, apiKey, modelName);
  };

  return (
    <div className={`glass-panel ${styles.uploadCard}`}>
      <h2 className={styles.title}>Initialize System</h2>
      <p className={styles.subtitle}>
        Provide your base parameters to start the SAMAS core analysis.
      </p>

      <form onSubmit={handleSubmit} className={styles.form}>
        <div
          className={`${styles.dropZone} ${file ? styles.hasFile : ''}`}
          onDragOver={(event) => event.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={(event) => event.target.files && setFile(event.target.files[0])}
            accept=".pdf,.docx"
            className={styles.hiddenInput}
          />
          {file ? (
            <div className={styles.fileSelected}>
              <span className={styles.fileIcon}>PDF</span>
              <span className={styles.fileName}>{file.name}</span>
            </div>
          ) : (
            <div className={styles.dropPrompt}>
              <span className={styles.uploadIcon}>+</span>
              <p>Drag and drop your resume</p>
              <span className={styles.browseBtn}>PDF or DOCX</span>
            </div>
          )}
        </div>

        <div className={styles.inputGroup}>
          <label>External Sources (GitHub, LinkedIn, Portfolio etc) comma separated</label>
          <input
            type="text"
            value={urls}
            onChange={(event) => setUrls(event.target.value)}
            placeholder="github.com/user, linkedin.com/in/user, portfolio.com"
            className="input-glass"
          />
        </div>
        
        <div className={styles.advancedSection}>
          <button 
            type="button" 
            className={styles.advancedToggle}
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            <span>Advanced Settings (BYOK)</span>
            <span className={styles.chevron}>{showAdvanced ? '▲' : '▼'}</span>
          </button>
          
          {showAdvanced && (
            <div className={styles.advancedPanel}>
              <div className={styles.inputGroup}>
                <label>OpenRouter API Key (Optional)</label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(event) => setApiKey(event.target.value)}
                  placeholder="sk-or-v1-..."
                  className="input-glass"
                />
              </div>
              <div className={styles.inputGroup}>
                <label>Model Name</label>
                <input
                  type="text"
                  value={modelName}
                  onChange={(event) => setModelName(event.target.value)}
                  placeholder="qwen/qwen3.7-plus"
                  className="input-glass"
                />
                <small className={styles.hintText}>Default: qwen/qwen3.7-plus</small>
              </div>
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={!file || isLoading}
          className={`btn-primary ${styles.submitBtn}`}
        >
          {isLoading ? 'Booting Neural Pathways...' : 'Initialize Analysis'}
        </button>
      </form>
    </div>
  );
}
