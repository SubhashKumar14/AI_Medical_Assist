/**
 * SymptomChecker Component
 * 
 * Goal:
 * - Collect symptom text from user
 * - Display AI-generated follow-up questions
 * - Render probability results with confidence scores
 *
 * Non-goals:
 * - No medical advice
 * - No diagnosis - only assistive insights
 */

import React, { useState, useCallback } from 'react';
import api from '../../services/api';

const SymptomChecker = () => {
  const [symptomText, setSymptomText] = useState('');
  const [sessionState, setSessionState] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [probabilities, setProbabilities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [consent, setConsent] = useState(false);
  const [isComplete, setIsComplete] = useState(false);

  // Start triage session
  const handleStartTriage = useCallback(async () => {
    if (!symptomText.trim()) {
      setError('Please describe your symptoms');
      return;
    }

    if (!consent) {
      setError('Please provide consent to proceed with AI-assisted analysis');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.post('/api/triage/start', {
        text: symptomText,
        consent: true
      });

      const { session_id, probabilities: probs, next_question, is_complete } = response.data;
      
      setSessionState({ sessionId: session_id });
      setProbabilities(probs || []);
      setCurrentQuestion(next_question);
      setIsComplete(is_complete || false);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to start triage session');
    } finally {
      setLoading(false);
    }
  }, [symptomText, consent]);

  // Answer follow-up question
  const handleAnswer = useCallback(async (answer) => {
    if (!sessionState?.sessionId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await api.post('/api/triage/next', {
        session_id: sessionState.sessionId,
        answer: answer,
        consent: true
      });

      const { probabilities: probs, next_question, is_complete } = response.data;
      
      setProbabilities(probs || []);
      setCurrentQuestion(next_question);
      setIsComplete(is_complete || false);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to process answer');
    } finally {
      setLoading(false);
    }
  }, [sessionState]);

  // Reset session
  const handleReset = () => {
    setSymptomText('');
    setSessionState(null);
    setCurrentQuestion(null);
    setProbabilities([]);
    setError(null);
    setIsComplete(false);
  };

  return (
    <div className="symptom-checker">
      <h2>AI-Assisted Symptom Analysis</h2>
      
      {/* Disclaimer */}
      <div className="disclaimer">
        <p>
          <strong>⚠️ Important:</strong> This tool provides assistive insights only. 
          It does not provide medical diagnosis or advice. 
          Always consult a licensed healthcare professional.
        </p>
      </div>

      {/* Initial symptom input */}
      {!sessionState && (
        <div className="symptom-input-section">
          <label htmlFor="symptoms">Describe your symptoms:</label>
          <textarea
            id="symptoms"
            value={symptomText}
            onChange={(e) => setSymptomText(e.target.value)}
            placeholder="E.g., I have had a fever for 3 days with headache and body aches..."
            rows={5}
            disabled={loading}
          />

          {/* Consent checkbox */}
          <div className="consent-section">
            <label>
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                disabled={loading}
              />
              I consent to AI-assisted analysis of my symptoms. I understand this is not a medical diagnosis.
            </label>
          </div>

          <button 
            onClick={handleStartTriage} 
            disabled={loading || !consent}
            className="primary-btn"
          >
            {loading ? 'Analyzing...' : 'Start Analysis'}
          </button>
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="error-message">
          <p>❌ {error}</p>
        </div>
      )}

      {/* Follow-up questions */}
      {currentQuestion && !isComplete && (
        <div className="question-section">
          <h3>Follow-up Question</h3>
          <p className="question-text">{currentQuestion.text}</p>
          
          <div className="answer-buttons">
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
      )}

      {/* Probability results */}
      {probabilities.length > 0 && (
        <div className="results-section">
          <h3>Possible Conditions (Ranked by Probability)</h3>
          <p className="results-disclaimer">
            These are statistical probabilities, not diagnoses. A doctor will review these results.
          </p>
          
          <ul className="probability-list">
            {probabilities.slice(0, 5).map((item, idx) => (
              <li key={idx} className="probability-item">
                <span className="disease-name">{item.disease}</span>
                <div className="confidence-bar-container">
                  <div 
                    className="confidence-bar" 
                    style={{ width: `${(item.probability * 100).toFixed(1)}%` }}
                  />
                  <span className="confidence-value">
                    {(item.probability * 100).toFixed(1)}%
                  </span>
                </div>
                {/* Symptom contributions for explainability */}
                {item.contributing_symptoms && (
                  <div className="contributing-symptoms">
                    <small>Key symptoms: {item.contributing_symptoms.join(', ')}</small>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Session complete */}
      {isComplete && (
        <div className="complete-section">
          <h3>✅ Analysis Complete</h3>
          <p>
            Based on your responses, the above conditions have been identified as possibilities.
            Please schedule a consultation with a doctor for proper evaluation.
          </p>
          <button onClick={handleReset} className="secondary-btn">
            Start New Analysis
          </button>
        </div>
      )}

      {/* Reset button when session active */}
      {sessionState && !isComplete && (
        <button onClick={handleReset} className="reset-btn">
          Start Over
        </button>
      )}
    </div>
  );
};

export default SymptomChecker;
