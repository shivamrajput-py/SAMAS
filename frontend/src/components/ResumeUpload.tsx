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
  
  // Model Settings
  const [modelSelection, setModelSelection] = useState('openai/gpt-oss-120b:nitro'); // Use requested default
  const [apiKey, setApiKey] = useState('');
  const [customModel, setCustomModel] = useState('');
  
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
    const finalModel = modelSelection === 'custom' ? customModel : modelSelection;
    onSubmit(file, urlList, apiKey, finalModel);
  };

  return (
    <div className={`glass-panel ${styles.uploadCard}`}>
      <h2 className={styles.title}>INITIALIZE PRISM</h2>
      <p className={styles.subtitle}>
        Upload your resume. SAMAS agents take it from there.
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
              <p>Drag and drop your base identity file</p>
              <span className={styles.browseBtn}>Browse Files</span>
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
        
        <div className={styles.modelSection}>
          <div className={styles.inputGroup}>
            <label>AI Intelligence Core</label>
            <select 
              className={`input-glass ${styles.customSelect}`} 
              value={modelSelection} 
              onChange={(e) => setModelSelection(e.target.value)}
            >
              <option value="openai/gpt-oss-120b:nitro">GPT-OSS 120B Nitro</option>
              <option value="deepseek/deepseek-v4-flash">DeepSeek V4 Flash</option>
              <option value="custom">Custom Model (Bring Your Own Key)</option>
            </select>
          </div>

          {modelSelection === 'custom' && (
            <div className={styles.advancedPanel}>
              <div className={styles.inputGroup}>
                <label>OpenRouter API Key (Required for custom models)</label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(event) => setApiKey(event.target.value)}
                  placeholder="sk-or-v1-..."
                  className="input-glass"
                  required={modelSelection === 'custom'}
                />
              </div>
              <div className={styles.inputGroup}>
                <label>Custom Model ID (OpenRouter)</label>
                <input
                  type="text"
                  value={customModel}
                  onChange={(event) => setCustomModel(event.target.value)}
                  placeholder="e.g. meta-llama/llama-3-70b-instruct"
                  className="input-glass"
                  required={modelSelection === 'custom'}
                />
              </div>
            </div>
          )}
        </div>

        <button 
          type="submit" 
          className={`btn-primary ${styles.submitBtn}`} 
          disabled={!file || isLoading}
        >
          {isLoading ? 'Processing...' : 'START SAMAS'}
        </button>
      </form>
    </div>
  );
}
