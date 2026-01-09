import React, { useState, useRef } from 'react';
import { useToast } from '../context/ToastContext';
import api from '../services/api';
import './ReportAnalyzer.css';

const ReportAnalyzer = () => {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const toast = useToast();

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = (selectedFile) => {
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf'];
    
    if (!allowedTypes.includes(selectedFile.type)) {
      toast.error('Please upload a valid image (JPEG, PNG, WebP) or PDF file');
      return;
    }

    if (selectedFile.size > 10 * 1024 * 1024) {
      toast.error('File size must be less than 10MB');
      return;
    }

    setFile(selectedFile);
    setAnalysis(null);

    // Create preview for images
    if (selectedFile.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result);
      };
      reader.readAsDataURL(selectedFile);
    } else {
      setPreview(null);
    }
  };

  const handleAnalyze = async () => {
    if (!file) {
      toast.error('Please upload a file first');
      return;
    }

    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('consent', 'true');

      const response = await api.post('/report/analyze', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      setAnalysis(response.data);
      toast.success('Report analyzed successfully');
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to analyze report');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setPreview(null);
    setAnalysis(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Get status indicator color
  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'normal':
        return 'normal';
      case 'high':
      case 'elevated':
        return 'high';
      case 'low':
        return 'low';
      case 'critical':
        return 'critical';
      default:
        return 'normal';
    }
  };

  return (
    <div className="report-analyzer-page">
      <div className="page-header">
        <div className="header-content">
          <h1>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14,2 14,8 20,8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10,9 9,9 8,9" />
            </svg>
            Medical Report Analyzer
          </h1>
          <p>Upload lab reports and get AI-powered analysis</p>
        </div>
      </div>

      <div className="analyzer-layout">
        {/* Upload Section */}
        <div className="upload-section">
          <div className="upload-card">
            <div
              className={`drop-zone ${dragActive ? 'active' : ''} ${file ? 'has-file' : ''}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => !file && fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,application/pdf"
                onChange={handleFileInput}
                hidden
              />

              {!file ? (
                <div className="upload-placeholder">
                  <div className="upload-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="17,8 12,3 7,8" />
                      <line x1="12" y1="3" x2="12" y2="15" />
                    </svg>
                  </div>
                  <h3>Drag & Drop your report</h3>
                  <p>or click to browse</p>
                  <span className="file-types">Supports: JPEG, PNG, WebP, PDF (Max 10MB)</span>
                </div>
              ) : (
                <div className="file-preview">
                  {preview ? (
                    <img src={preview} alt="Report preview" className="preview-image" />
                  ) : (
                    <div className="pdf-preview">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14,2 14,8 20,8" />
                      </svg>
                      <span>PDF Document</span>
                    </div>
                  )}
                  <div className="file-info">
                    <span className="file-name">{file.name}</span>
                    <span className="file-size">{(file.size / 1024).toFixed(1)} KB</span>
                  </div>
                </div>
              )}
            </div>

            {file && (
              <div className="upload-actions">
                <button
                  onClick={handleAnalyze}
                  disabled={loading}
                  className="btn btn-primary"
                >
                  {loading ? (
                    <>
                      <span className="spinner spinner-sm"></span>
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="11" cy="11" r="8" />
                        <line x1="21" y1="21" x2="16.65" y2="16.65" />
                      </svg>
                      Analyze Report
                    </>
                  )}
                </button>
                <button onClick={handleReset} className="btn btn-outline">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                  Clear
                </button>
              </div>
            )}
          </div>

          {/* Supported Tests */}
          <div className="supported-tests">
            <h3>Supported Tests</h3>
            <div className="test-grid">
              <div className="test-item">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                </svg>
                <span>CBC (Complete Blood Count)</span>
              </div>
              <div className="test-item">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                </svg>
                <span>Lipid Profile</span>
              </div>
              <div className="test-item">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                </svg>
                <span>Liver Function Tests</span>
              </div>
              <div className="test-item">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                </svg>
                <span>Kidney Function Tests</span>
              </div>
              <div className="test-item">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                </svg>
                <span>Thyroid Panel</span>
              </div>
              <div className="test-item">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                </svg>
                <span>Blood Sugar Tests</span>
              </div>
            </div>
          </div>
        </div>

        {/* Results Section */}
        <div className="results-section">
          {!analysis ? (
            <div className="empty-results">
              <div className="empty-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
              </div>
              <h3>Upload a report to see analysis</h3>
              <p>Our AI will extract and analyze the test results from your medical report.</p>
            </div>
          ) : (
            <div className="analysis-results">
              <div className="results-header">
                <h2>Analysis Results</h2>
                <span className="analysis-time">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12,6 12,12 16,14" />
                  </svg>
                  {new Date().toLocaleString()}
                </span>
              </div>

              {/* Summary */}
              {analysis.summary && (
                <div className="summary-card">
                  <h3>Summary</h3>
                  <p>{analysis.summary}</p>
                </div>
              )}

              {/* Parameters */}
              {analysis.parameters && analysis.parameters.length > 0 && (
                <div className="parameters-section">
                  <h3>Test Parameters</h3>
                  <div className="parameters-table">
                    <div className="table-header">
                      <span>Parameter</span>
                      <span>Value</span>
                      <span>Reference Range</span>
                      <span>Status</span>
                    </div>
                    {analysis.parameters.map((param, idx) => (
                      <div key={idx} className="table-row">
                        <span className="param-name">{param.name}</span>
                        <span className="param-value">{param.value} {param.unit}</span>
                        <span className="param-range">{param.reference_range || 'N/A'}</span>
                        <span className={`param-status status-${getStatusColor(param.status)}`}>
                          {param.status || 'Normal'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Red Flags */}
              {analysis.red_flags && analysis.red_flags.length > 0 && (
                <div className="red-flags-section">
                  <div className="section-title warning">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                      <line x1="12" y1="9" x2="12" y2="13" />
                      <line x1="12" y1="17" x2="12.01" y2="17" />
                    </svg>
                    <h3>Red Flags</h3>
                  </div>
                  <ul className="flags-list">
                    {analysis.red_flags.map((flag, idx) => (
                      <li key={idx}>{flag}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Recommendations */}
              {analysis.recommendations && analysis.recommendations.length > 0 && (
                <div className="recommendations-section">
                  <div className="section-title">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M9 11l3 3L22 4" />
                      <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
                    </svg>
                    <h3>Recommendations</h3>
                  </div>
                  <ul className="recommendations-list">
                    {analysis.recommendations.map((rec, idx) => (
                      <li key={idx}>{rec}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Explanation */}
              {analysis.explanation && (
                <div className="explanation-section">
                  <div className="section-title">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="16" x2="12" y2="12" />
                      <line x1="12" y1="8" x2="12.01" y2="8" />
                    </svg>
                    <h3>AI Explanation</h3>
                  </div>
                  <p>{analysis.explanation}</p>
                </div>
              )}

              {/* Actions */}
              <div className="analysis-actions">
                <button className="btn btn-primary">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7,10 12,15 17,10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                  Download Report
                </button>
                <button className="btn btn-outline" onClick={handleReset}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                    <path d="M3 3v5h5" />
                  </svg>
                  New Analysis
                </button>
              </div>

              {/* Disclaimer */}
              <div className="analysis-disclaimer">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <p>This analysis is for informational purposes only. Please consult a healthcare professional for proper interpretation and advice.</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Side Info */}
      <div className="side-info">
        <div className="info-card">
          <h3>How It Works</h3>
          <ol className="how-it-works">
            <li>
              <span className="step">1</span>
              <div>
                <strong>Upload Report</strong>
                <p>Upload a clear image or PDF of your medical report</p>
              </div>
            </li>
            <li>
              <span className="step">2</span>
              <div>
                <strong>AI Processing</strong>
                <p>Our OCR extracts text and AI analyzes the values</p>
              </div>
            </li>
            <li>
              <span className="step">3</span>
              <div>
                <strong>Get Insights</strong>
                <p>Receive detailed analysis with explanations</p>
              </div>
            </li>
          </ol>
        </div>

        <div className="info-card tips">
          <h3>Tips for Best Results</h3>
          <ul>
            <li>Ensure the report image is clear and readable</li>
            <li>Include the full page with all values visible</li>
            <li>Avoid blurry or low-resolution images</li>
            <li>PDF files work best for multi-page reports</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default ReportAnalyzer;
