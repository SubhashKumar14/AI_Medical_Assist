import React, { useState } from 'react';
import { reportAPI } from '../../services/api';

const ReportAnalyzer = () => {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [selectedModel, setSelectedModel] = useState('auto'); // Added Model State

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      setPreviewUrl(URL.createObjectURL(selected));
      setResults(null);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a file first.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('user_id', 'anonymous');
      formData.append('model_provider', selectedModel); // Forward model selection

      // Call API
      const response = await reportAPI.analyze(formData);
      setResults(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to analyze report");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="report-analyzer-container" style={{ display: 'flex', gap: '20px', padding: '20px', height: 'calc(100vh - 100px)' }}>

      {/* LEFT PANEL: Upload & Preview */}
      <div className="left-panel" style={{ flex: 1, borderRight: '1px solid #ddd', paddingRight: '20px', display: 'flex', flexDirection: 'column' }}>
        <h2>📄 Upload Medical Report</h2>
        <p>Upload a clear photo or PDF of your lab report.</p>

        {/* Model Selection */}
        <div style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#f0f9ff', borderRadius: '5px', border: '1px solid #bae6fd' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold', color: '#0369a1' }}>🤖 AI Model Provider:</label>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
          >
            <option value="auto">Auto (Best Available)</option>
            <option value="gemini">Google Gemini Pro</option>
            <option value="openrouter">OpenRouter (Claude/GPT-4)</option>
          </select>
        </div>

        <input
          type="file"
          accept="image/*,application/pdf"
          onChange={handleFileChange}
          style={{ marginBottom: '20px' }}
        />

        {previewUrl && (
          <div className="preview-container" style={{ flex: 1, backgroundColor: '#f0f0f0', borderRadius: '8px', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {file.type.includes('image') ? (
              <img src={previewUrl} alt="Report Preview" style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
            ) : (
              <embed src={previewUrl} type="application/pdf" width="100%" height="100%" />
            )}
          </div>
        )}

        <button
          className="primary-btn"
          onClick={handleUpload}
          disabled={!file || loading}
          style={{ marginTop: '20px', padding: '15px', fontSize: '1.1rem' }}
        >
          {loading ? "🔍 Analyzing (this may take 10-20s)..." : "Analyze Report"}
        </button>
      </div>

      {/* RIGHT PANEL: Analysis Results */}
      <div className="right-panel" style={{ flex: 1, overflowY: 'auto', paddingLeft: '10px' }}>
        <h2>📊 AI Analysis Results</h2>

        {loading && (
          <div style={{ textAlign: 'center', marginTop: '50px' }}>
            <div className="spinner"></div>
            <p>Extracting text & values...</p>
            <p>Applying reference ranges...</p>
            <p>Generating clinical summary...</p>
          </div>
        )}

        {error && (
          <div className="error-message" style={{ color: 'red', marginTop: '20px' }}>
            ❌ {error}
          </div>
        )}

        {results && (
          <div className="results-content">
            {/* RED FLAGS */}
            {results.red_flags && results.red_flags.length > 0 && (
              <div className="red-flags-section" style={{ backgroundColor: '#fee2e2', border: '1px solid #ef4444', padding: '15px', borderRadius: '8px', marginBottom: '20px' }}>
                <h3 style={{ color: '#b91c1c', marginTop: 0 }}>🚨 CRITICAL ALERTS</h3>
                {results.red_flags.map((flag, i) => (
                  <p key={i} style={{ color: '#b91c1c', fontWeight: 'bold' }}>{flag}</p>
                ))}
              </div>
            )}

            {/* AI SUMMARY */}
            <div className="summary-card" style={{ backgroundColor: '#f0f9ff', padding: '20px', borderRadius: '8px', borderLeft: '5px solid #0ea5e9', marginBottom: '20px' }}>
              <h3 style={{ marginTop: 0, color: '#0369a1' }}>🤖 Clinical Summary</h3>
              <div style={{ whiteSpace: 'pre-line' }}>{results.summary}</div>
            </div>

            {/* ABNORMALITIES */}
            <div className="abnormalities-section">
              <h3>⚠️ Abnormal Findings</h3>
              {results.abnormal_findings.length === 0 ? (
                <p style={{ color: 'green' }}>✅ No significant abnormalities detected.</p>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '20px' }}>
                  <thead>
                    <tr style={{ backgroundColor: '#f3f4f6', textAlign: 'left' }}>
                      <th style={{ padding: '10px' }}>Test</th>
                      <th style={{ padding: '10px' }}>Value</th>
                      <th style={{ padding: '10px' }}>Ref Range</th>
                      <th style={{ padding: '10px' }}>Flag</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.abnormal_findings.map((item, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #eee', backgroundColor: item.severity === 'critical' ? '#fecaca' : '#fef3c7' }}>
                        <td style={{ padding: '10px', fontWeight: 'bold' }}>{item.test_name}</td>
                        <td style={{ padding: '10px' }}>{item.value} {item.unit}</td>
                        <td style={{ padding: '10px', fontSize: '0.9rem', color: '#666' }}>{item.reference_range}</td>
                        <td style={{ padding: '10px' }}>
                          <span style={{
                            padding: '4px 8px', borderRadius: '4px', fontSize: '0.8rem', fontWeight: 'bold',
                            backgroundColor: item.severity === 'critical' ? '#dc2626' : '#d97706',
                            color: 'white'
                          }}>
                            {item.direction.toUpperCase()} ({item.severity})
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* ALL VALUES ACCORDION (Simplified) */}
            <details style={{ marginTop: '20px', cursor: 'pointer', padding: '10px', border: '1px solid #eee', borderRadius: '8px' }}>
              <summary style={{ fontWeight: 'bold' }}>View All Extracted Values ({results.lab_values.length})</summary>
              <div style={{ marginTop: '10px', maxHeight: '300px', overflowY: 'auto' }}>
                {results.lab_values.map((val, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #f9f9f9' }}>
                    <span>{val.name}</span>
                    <span style={{ fontWeight: val.is_abnormal ? 'bold' : 'normal', color: val.is_abnormal ? 'orange' : 'inherit' }}>
                      {val.value} {val.unit}
                    </span>
                  </div>
                ))}
              </div>
            </details>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportAnalyzer;
