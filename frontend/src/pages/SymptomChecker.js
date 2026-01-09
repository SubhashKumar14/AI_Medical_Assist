import React, { useState, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import api from '../services/api';
import './SymptomChecker.css';

const SymptomChecker = () => {
  const [symptomText, setSymptomText] = useState('');
  const [sessionState, setSessionState] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [probabilities, setProbabilities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [consent, setConsent] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [questionHistory, setQuestionHistory] = useState([]);

  const { user } = useAuth();
  const toast = useToast();

  // Common symptoms quick select
  const commonSymptoms = [
    'Fever', 'Headache', 'Cough', 'Fatigue', 'Body aches',
    'Sore throat', 'Shortness of breath', 'Nausea', 'Dizziness'
  ];

  const addSymptom = (symptom) => {
    setSymptomText(prev => {
      if (prev.trim()) {
        return `${prev}, ${symptom.toLowerCase()}`;
      }
      return symptom.toLowerCase();
    });
  };

  // Start triage session
  const handleStartTriage = useCallback(async () => {
    if (!symptomText.trim()) {
      toast.error('Please describe your symptoms');
      return;
    }

    if (!consent) {
      toast.error('Please provide consent to proceed');
      return;
    }

    setLoading(true);

    try {
      const response = await api.post('/triage/start', {
        text: symptomText,
        consent: true
      });

      const { session_id, probabilities: probs, next_question, is_complete } = response.data;
      
      setSessionState({ sessionId: session_id });
      setProbabilities(probs || []);
      setCurrentQuestion(next_question);
      setIsComplete(is_complete || false);
      toast.success('Analysis started');
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to start analysis');
    } finally {
      setLoading(false);
    }
  }, [symptomText, consent, toast]);

  // Answer follow-up question
  const handleAnswer = useCallback(async (answer) => {
    if (!sessionState?.sessionId) return;

    setLoading(true);

    try {
      // Save question to history
      setQuestionHistory(prev => [...prev, {
        question: currentQuestion?.text,
        answer: answer
      }]);

      const response = await api.post('/triage/next', {
        session_id: sessionState.sessionId,
        answer: answer,
        consent: true
      });

      const { probabilities: probs, next_question, is_complete } = response.data;
      
      setProbabilities(probs || []);
      setCurrentQuestion(next_question);
      setIsComplete(is_complete || false);
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to process answer');
    } finally {
      setLoading(false);
    }
  }, [sessionState, currentQuestion, toast]);

  // Reset session
  const handleReset = () => {
    setSymptomText('');
    setSessionState(null);
    setCurrentQuestion(null);
    setProbabilities([]);
    setIsComplete(false);
    setQuestionHistory([]);
    setConsent(false);
  };

  // Get urgency color
  const getUrgencyColor = (probability) => {
    if (probability > 0.7) return 'high';
    if (probability > 0.4) return 'medium';
    return 'low';
  };

  return (
    <div className="symptom-checker-page">
      <div className="page-header">
        <div className="header-content">
          <h1>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
            Symptom Analysis
          </h1>
          <p>AI-powered preliminary health assessment</p>
        </div>
      </div>

      <div className="checker-layout">
        {/* Main Panel */}
        <div className="main-panel">
          {/* Disclaimer */}
          <div className="disclaimer-card">
            <div className="disclaimer-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <div className="disclaimer-content">
              <strong>Medical Disclaimer</strong>
              <p>This tool provides preliminary insights only. It is NOT a medical diagnosis. Always consult a licensed healthcare professional for proper evaluation.</p>
            </div>
          </div>

          {/* Initial Input Section */}
          {!sessionState && (
            <div className="input-section">
              <div className="section-header">
                <h2>Describe Your Symptoms</h2>
                <p>Be as detailed as possible - include duration, severity, and any associated symptoms.</p>
              </div>

              <div className="symptom-input-container">
                <textarea
                  value={symptomText}
                  onChange={(e) => setSymptomText(e.target.value)}
                  placeholder="Example: I've had a persistent headache for 3 days, accompanied by mild fever and fatigue. The headache is worse in the morning and seems to get better after taking painkillers..."
                  rows={6}
                  disabled={loading}
                  className="symptom-textarea"
                />
                <div className="char-count">{symptomText.length} characters</div>
              </div>

              <div className="quick-symptoms">
                <span className="quick-label">Quick add:</span>
                <div className="symptom-chips">
                  {commonSymptoms.map((symptom, idx) => (
                    <button
                      key={idx}
                      className="symptom-chip"
                      onClick={() => addSymptom(symptom)}
                    >
                      + {symptom}
                    </button>
                  ))}
                </div>
              </div>

              <div className="consent-box">
                <label className="consent-label">
                  <input
                    type="checkbox"
                    checked={consent}
                    onChange={(e) => setConsent(e.target.checked)}
                    disabled={loading}
                  />
                  <span className="checkmark"></span>
                  <span className="consent-text">
                    I understand that this is an AI-assisted tool and does not replace professional medical advice. 
                    I consent to the analysis of my symptoms.
                  </span>
                </label>
              </div>

              <button 
                onClick={handleStartTriage} 
                disabled={loading || !consent || !symptomText.trim()}
                className="btn btn-primary btn-lg start-btn"
              >
                {loading ? (
                  <>
                    <span className="spinner spinner-sm"></span>
                    Analyzing...
                  </>
                ) : (
                  <>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                    </svg>
                    Start Analysis
                  </>
                )}
              </button>
            </div>
          )}

          {/* Question Section */}
          {currentQuestion && !isComplete && (
            <div className="question-section">
              <div className="progress-indicator">
                <div className="progress-step active">
                  <span>1</span>
                  <label>Symptoms</label>
                </div>
                <div className="progress-line active"></div>
                <div className="progress-step active">
                  <span>2</span>
                  <label>Questions</label>
                </div>
                <div className="progress-line"></div>
                <div className="progress-step">
                  <span>3</span>
                  <label>Results</label>
                </div>
              </div>

              <div className="question-card">
                <div className="question-number">
                  Question {questionHistory.length + 1}
                </div>
                <p className="question-text">{currentQuestion.text}</p>
                
                <div className="answer-options">
                  {currentQuestion.options?.map((option, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleAnswer(option)}
                      disabled={loading}
                      className="answer-btn"
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </div>

              {/* Question History */}
              {questionHistory.length > 0 && (
                <div className="history-section">
                  <h4>Previous Answers</h4>
                  <div className="history-list">
                    {questionHistory.map((item, idx) => (
                      <div key={idx} className="history-item">
                        <span className="history-q">Q{idx + 1}: {item.question}</span>
                        <span className="history-a">{item.answer}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <button onClick={handleReset} className="btn btn-outline reset-btn">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                  <path d="M3 3v5h5" />
                </svg>
                Start Over
              </button>
            </div>
          )}

          {/* Results Section */}
          {isComplete && probabilities.length > 0 && (
            <div className="results-section">
              <div className="results-header">
                <div className="results-icon success">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                    <polyline points="22,4 12,14.01 9,11.01" />
                  </svg>
                </div>
                <h2>Analysis Complete</h2>
                <p>Based on your symptoms and responses, here are the possible conditions:</p>
              </div>

              <div className="probability-results">
                {probabilities.slice(0, 5).map((item, idx) => (
                  <div key={idx} className={`result-card urgency-${getUrgencyColor(item.probability)}`}>
                    <div className="result-rank">#{idx + 1}</div>
                    <div className="result-content">
                      <h3 className="disease-name">{item.disease}</h3>
                      <div className="probability-bar">
                        <div 
                          className="probability-fill"
                          style={{ width: `${(item.probability * 100).toFixed(1)}%` }}
                        ></div>
                        <span className="probability-value">
                          {(item.probability * 100).toFixed(1)}%
                        </span>
                      </div>
                      {item.contributing_symptoms && item.contributing_symptoms.length > 0 && (
                        <div className="contributing-symptoms">
                          <span className="symptoms-label">Key indicators:</span>
                          <div className="symptom-tags">
                            {item.contributing_symptoms.map((symptom, sIdx) => (
                              <span key={sIdx} className="symptom-tag">{symptom}</span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <div className="next-steps">
                <h3>Recommended Next Steps</h3>
                <div className="steps-grid">
                  <div className="step-card">
                    <div className="step-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                        <circle cx="12" cy="7" r="4" />
                      </svg>
                    </div>
                    <h4>Consult a Doctor</h4>
                    <p>Schedule an appointment with a healthcare provider for proper evaluation.</p>
                  </div>
                  <div className="step-card">
                    <div className="step-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14,2 14,8 20,8" />
                        <line x1="16" y1="13" x2="8" y2="13" />
                        <line x1="16" y1="17" x2="8" y2="17" />
                        <polyline points="10,9 9,9 8,9" />
                      </svg>
                    </div>
                    <h4>Save Results</h4>
                    <p>Keep these results for reference during your consultation.</p>
                  </div>
                  <div className="step-card">
                    <div className="step-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10" />
                        <polyline points="12,6 12,12 16,14" />
                      </svg>
                    </div>
                    <h4>Monitor Symptoms</h4>
                    <p>Track any changes in your symptoms over time.</p>
                  </div>
                </div>
              </div>

              <div className="results-actions">
                <button onClick={handleReset} className="btn btn-primary">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                    <path d="M3 3v5h5" />
                  </svg>
                  New Analysis
                </button>
                <button className="btn btn-outline">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7,10 12,15 17,10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                  Download Report
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Side Panel */}
        <div className="side-panel">
          <div className="info-card">
            <h3>How it Works</h3>
            <div className="info-steps">
              <div className="info-step">
                <span className="step-num">1</span>
                <div>
                  <strong>Describe Symptoms</strong>
                  <p>Enter your symptoms in detail</p>
                </div>
              </div>
              <div className="info-step">
                <span className="step-num">2</span>
                <div>
                  <strong>Answer Questions</strong>
                  <p>Respond to follow-up questions</p>
                </div>
              </div>
              <div className="info-step">
                <span className="step-num">3</span>
                <div>
                  <strong>Get Insights</strong>
                  <p>Review AI-generated analysis</p>
                </div>
              </div>
            </div>
          </div>

          <div className="info-card warning">
            <h3>When to Seek Immediate Care</h3>
            <ul className="warning-list">
              <li>Difficulty breathing</li>
              <li>Chest pain or pressure</li>
              <li>Sudden confusion</li>
              <li>Severe bleeding</li>
              <li>High fever (over 103°F)</li>
            </ul>
            <p className="emergency-note">
              <strong>If experiencing any of these, call emergency services immediately.</strong>
            </p>
          </div>

          {user && (
            <div className="info-card">
              <h3>Your Health Profile</h3>
              <p className="profile-name">{user.name}</p>
              <p className="profile-detail">Analyses completed: 0</p>
              <a href="/dashboard" className="profile-link">View Dashboard →</a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SymptomChecker;
