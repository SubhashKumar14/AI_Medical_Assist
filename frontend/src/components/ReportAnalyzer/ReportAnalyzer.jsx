/**
 * ReportAnalyzer Component
 * 
 * Goal:
 * - Upload medical reports (PDF/image)
 * - Display extracted lab values and abnormalities
 * - Show AI-generated summary
 *
 * Non-goals:
 * - No diagnosis, only interpretation assistance
 * - No prescription recommendations
 */

import React, { useState, useCallback, useRef } from 'react';
import api from '../../services/api';

const ACCEPTED_FILE_TYPES = [
  'application/pdf',
  'image/png',
  'image/jpeg',
  'image/jpg'
];

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

const ReportAnalyzer = () => {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);
  const [consent, setConsent] = useState(false);
  const fileInputRef = useRef(null);

  // Handle file selection
  const handleFileSelect = useCallback((event) => {
    const selectedFile = event.target.files?.[0];
    setError(null);
    setResults(null);

    if (!selectedFile) return;

    // Validate file type
    if (!ACCEPTED_FILE_TYPES.includes(selectedFile.type)) {
      setError('Please upload a PDF or image file (PNG, JPG)');
      return;
    }

    // Validate file size
    if (selectedFile.size > MAX_FILE_SIZE) {
      setError('File size must be less than 10MB');
      return;
    }

    setFile(selectedFile);

    // Create preview for images
    if (selectedFile.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target.result);
      reader.readAsDataURL(selectedFile);
    } else {
      setPreview(null);
    }
  }, []);

  // Handle drag and drop
  const handleDrop = useCallback((event) => {
    event.preventDefault();
    event.stopPropagation();
    
    const droppedFile = event.dataTransfer.files?.[0];
    if (droppedFile) {
      // Simulate file input change
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(droppedFile);
      if (fileInputRef.current) {
        fileInputRef.current.files = dataTransfer.files;
        handleFileSelect({ target: { files: dataTransfer.files } });
      }
    }
  }, [handleFileSelect]);

  const handleDragOver = (event) => {
    event.preventDefault();
    event.stopPropagation();
  };

  // Submit report for analysis
  const handleAnalyze = useCallback(async () => {
    if (!file) {
      setError('Please select a file to analyze');
      return;
    }

    if (!consent) {
      setError('Please provide consent to proceed with AI analysis');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('consent', 'true');

      const response = await api.post('/api/report/analyze', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      setResults(response.data);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to analyze report');
    } finally {
      setLoading(false);
    }
  }, [file, consent]);

  // Reset state
  const handleReset = () => {
    setFile(null);
    setPreview(null);
    setResults(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Render abnormal findings
  const renderFindings = (findings) => {
    if (!findings || findings.length === 0) {
      return <p className="no-findings">No abnormal findings detected.</p>;
    }

    return (
      <ul className="findings-list">
        {findings.map((finding, idx) => (
          <li key={idx} className={`finding-item ${finding.severity}`}>
            <div className="finding-header">
              <span className="finding-name">{finding.test_name}</span>
              <span className={`severity-badge ${finding.severity}`}>
                {finding.severity}
              </span>
            </div>
            <div className="finding-details">
              <span className="finding-value">
                Value: {finding.value} {finding.unit}
              </span>
              <span className="finding-range">
                Reference: {finding.reference_range}
              </span>
            </div>
            {finding.interpretation && (
              <p className="finding-interpretation">{finding.interpretation}</p>
            )}
          </li>
        ))}
      </ul>
    );
  };

  return (
    <div className="report-analyzer">
      <h2>Medical Report Analysis</h2>

      {/* Disclaimer */}
      <div className="disclaimer">
        <p>
          <strong>⚠️ Important:</strong> This tool extracts and highlights 
          information from medical reports. It does not provide diagnosis. 
          Always consult a healthcare professional for interpretation.
        </p>
      </div>

      {/* File upload area */}
      {!results && (
        <div 
          className="upload-area"
          onDrop={handleDrop}
          onDragOver={handleDragOver}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            onChange={handleFileSelect}
            disabled={loading}
            id="file-upload"
            className="file-input"
          />
          
          <label htmlFor="file-upload" className="upload-label">
            <div className="upload-icon">📄</div>
            <p>Drag & drop or click to upload</p>
            <small>PDF, PNG, JPG (max 10MB)</small>
          </label>

          {/* File preview */}
          {file && (
            <div className="file-preview">
              <p className="file-name">📎 {file.name}</p>
              {preview && (
                <img 
                  src={preview} 
                  alt="Report preview" 
                  className="image-preview"
                />
              )}
            </div>
          )}

          {/* Consent checkbox */}
          <div className="consent-section">
            <label>
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                disabled={loading}
              />
              I consent to AI-assisted analysis of this medical report.
            </label>
          </div>

          <button
            onClick={handleAnalyze}
            disabled={loading || !file || !consent}
            className="primary-btn"
          >
            {loading ? 'Analyzing...' : 'Analyze Report'}
          </button>
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="error-message">
          <p>❌ {error}</p>
        </div>
      )}

      {/* Analysis results */}
      {results && (
        <div className="results-section">
          {/* Extracted text summary */}
          {results.extracted_text && (
            <div className="extracted-text">
              <h3>📝 Extracted Content</h3>
              <div className="text-content">
                {results.extracted_text.substring(0, 500)}
                {results.extracted_text.length > 500 && '...'}
              </div>
            </div>
          )}

          {/* Lab values */}
          <div className="lab-values">
            <h3>🔬 Lab Values</h3>
            {results.lab_values && results.lab_values.length > 0 ? (
              <table className="lab-table">
                <thead>
                  <tr>
                    <th>Test</th>
                    <th>Value</th>
                    <th>Unit</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {results.lab_values.map((lab, idx) => (
                    <tr key={idx} className={lab.is_abnormal ? 'abnormal' : ''}>
                      <td>{lab.name}</td>
                      <td>{lab.value}</td>
                      <td>{lab.unit}</td>
                      <td>
                        <span className={`status ${lab.is_abnormal ? 'abnormal' : 'normal'}`}>
                          {lab.is_abnormal ? '⚠️ Abnormal' : '✓ Normal'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p>No lab values extracted.</p>
            )}
          </div>

          {/* Abnormal findings */}
          <div className="abnormal-findings">
            <h3>⚠️ Abnormal Findings</h3>
            {renderFindings(results.abnormal_findings)}
          </div>

          {/* AI Summary */}
          {results.summary && (
            <div className="ai-summary">
              <h3>📋 AI Summary</h3>
              <p className="summary-disclaimer">
                <em>This summary is AI-generated and requires professional review.</em>
              </p>
              <div className="summary-content">
                {results.summary}
              </div>
            </div>
          )}

          {/* Red flags warning */}
          {results.red_flags && results.red_flags.length > 0 && (
            <div className="red-flags-warning">
              <h3>🚨 Critical Findings</h3>
              <p>The following findings require immediate medical attention:</p>
              <ul>
                {results.red_flags.map((flag, idx) => (
                  <li key={idx}>{flag}</li>
                ))}
              </ul>
            </div>
          )}

          <button onClick={handleReset} className="secondary-btn">
            Analyze Another Report
          </button>
        </div>
      )}
    </div>
  );
};

export default ReportAnalyzer;
