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
import { triageAPI } from '../../services/api';

const SymptomChecker = () => {
  // Core State
  const [symptomText, setSymptomText] = useState('');
  const [consent, setConsent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionState, setSessionState] = useState(null);
  const [probabilities, setProbabilities] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [isComplete, setIsComplete] = useState(false);
  const [safeSummary, setSafeSummary] = useState(null);
  const [selectedModel, setSelectedModel] = useState('auto'); // Added Model State

  /* State for AIChat Modal */
  const [showChat, setShowChat] = useState(false);
  const [extendNeeded, setExtendNeeded] = useState(false);

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
      const response = await triageAPI.start(symptomText, true, selectedModel);

      const { session_id, probabilities: probs, next_question, is_complete, safe_summary, extend_needed } = response.data;

      setSessionState({ sessionId: session_id });
      setProbabilities(probs || []);
      setCurrentQuestion(next_question);
      setIsComplete(is_complete || false);
      setSafeSummary(safe_summary);
      setExtendNeeded(extend_needed || false);
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
      const response = await triageAPI.next(sessionState.sessionId, answer, true);

      const { probabilities: probs, next_question, is_complete, safe_summary, extend_needed } = response.data;

      setProbabilities(probs || []);
      setCurrentQuestion(next_question);
      setIsComplete(is_complete || false);
      setSafeSummary(safe_summary);
      setExtendNeeded(extend_needed || false);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to process answer');
    } finally {
      setLoading(false);
    }
  }, [sessionState]);

  const handleReset = () => {
    setSymptomText('');
    setSessionState(null);
    setCurrentQuestion(null);
    setProbabilities([]);
    setSafeSummary(null);
    setError(null);
    setIsComplete(false);
    setExtendNeeded(false);
    setShowChat(false);
  };

  // Calculate Progress
  const questionCount = sessionState?.sessionId ? (probabilities.length > 0 ? 3 : 0) : 0; // approximate or track in state?
  // Better to track in state but for now let's assume unknown. 
  // Wait, API doesn't return question_count! PROPOSAL: Add it to response? 
  // For MVP, just show "Analyzing..."

  return (
    <div className="symptom-checker">
      <h2>AI-Assisted Symptom Analysis</h2>

      {/* AIChat Modal */}
      {showChat && (
        <div className="ai-chat-modal" style={{
          position: 'fixed', top: '10%', left: '10%', right: '10%', bottom: '10%',
          backgroundColor: 'white', zIndex: 1000, padding: '20px',
          boxShadow: '0 0 20px rgba(0,0,0,0.5)', borderRadius: '10px', display: 'flex', flexDirection: 'column'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
            <h3>AI Health Assistant ({selectedModel === 'auto' ? 'Auto' : selectedModel})</h3>
            <button onClick={() => setShowChat(false)} style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer' }}>×</button>
          </div>

          {/* Chat History */}
          <div style={{ flex: 1, backgroundColor: '#f9f9f9', padding: '10px', borderRadius: '5px', overflowY: 'auto', marginBottom: '10px' }}>
            {/* Simple internal chat state would be needed here, for now just showing system hello */}
            <div className="message system">
              <p><strong>AI:</strong> I have reviewed your case (symptoms: {symptomText}). How can I help explain the results? (Note: I cannot diagnose).</p>
            </div>
            {/* If we had full chat state, we'd map it here. For MVP, let's just do single turn or assume separate component handles history */}
            <p><em>(Chat is connected to model: {selectedModel})</em></p>
          </div>

          <div style={{ display: 'flex' }}>
            <input
              type="text"
              id="chat-input-box"
              placeholder="Ask a question..."
              style={{ flex: 1, padding: '10px' }}
              onKeyPress={async (e) => {
                if (e.key === 'Enter') {
                  const msg = e.target.value;
                  if (!msg) return;
                  e.target.value = 'Sending...';
                  try {
                    const res = await import('../../services/api').then(m => m.chatAPI.sendMessage(sessionState.sessionId, msg, selectedModel));
                    alert(`AI Reply: ${res.data.reply}`); // MVP: Simple Alert for now, or append to DOM
                    e.target.value = '';
                  } catch (err) {
                    alert("Error sending message");
                    e.target.value = msg;
                  }
                }
              }}
            />
            <button className="primary-btn" style={{ marginLeft: '10px' }} onClick={() => document.getElementById('chat-input-box').focus()}>Tip: Press Enter</button>
          </div>
        </div>
      )}

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
          {/* Model Selection */}
          <div style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#f0f9ff', borderRadius: '5px', border: '1px solid #bae6fd' }}>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold', color: '#0369a1' }}>🤖 AI Model Provider:</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
            >
              <option value="auto">Auto (Best Available)</option>
              <option value="gemini">Google Gemini Pro (Fast & Smart)</option>
              <option value="openrouter">OpenRouter (Claude/GPT-4 Fallback)</option>
            </select>
          </div>

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

      {/* Progress Bar (Mock) */}
      {sessionState && !isComplete && (
        <div style={{ width: '100%', height: '5px', backgroundColor: '#eee', margin: '10px 0' }}>
          <div style={{ width: '60%', height: '100%', backgroundColor: '#3498db' }}></div>
        </div>
      )}

      {/* EXTEND NEEDED PROMPT */}
      {extendNeeded && (
        <div className="extend-prompt" style={{ backgroundColor: '#fff3cd', padding: '15px', borderRadius: '5px', margin: '15px 0' }}>
          <h3>Probe Further?</h3>
          <p>The analysis is still inconclusive. Would you like to answer 2 more questions to improve accuracy?</p>
          <button onClick={() => handleAnswer('continue')} className="primary-btn" style={{ marginRight: '10px' }}>Yes, continue</button>
          <button onClick={() => handleAnswer('stop')} className="secondary-btn">No, show results</button>
        </div>
      )}

      {/* Follow-up questions */}
      {currentQuestion && !isComplete && !extendNeeded && (
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

      {/* Safe Summary Display (MANDATORY SAFETY OUTPUT) */}
      {safeSummary && (
        <div className="safe-summary-section" style={{
          backgroundColor: '#fdfefe',
          padding: '24px',
          borderRadius: '12px',
          borderLeft: '6px solid #2c3e50',
          marginTop: '24px',
          boxShadow: '0 4px 6px rgba(0,0,0,0.05)'
        }}>
          {safeSummary.split('\n').map((line, i) => {
            if (line.includes('**DISCLAIMER')) {
              return <p key={i} style={{ color: '#c0392b', fontWeight: 'bold', fontSize: '0.9rem', marginBottom: '16px', textTransform: 'uppercase' }}>{line.replace(/\*\*/g, '')}</p>;
            }
            if (line.includes('**')) {
              const parts = line.split('**');
              return (
                <p key={i} style={{ margin: '12px 0 8px 0', fontSize: '1.05rem', color: '#2c3e50' }}>
                  {parts.map((part, index) =>
                    index % 2 === 1 ? <strong key={index}>{part}</strong> : part
                  )}
                </p>
              );
            }
            if (line.trim().startsWith('•')) {
              return <p key={i} style={{ margin: '4px 0 4px 16px', color: '#34495e' }}>{line}</p>;
            }
            return <p key={i} style={{ margin: '4px 0', lineHeight: '1.5', color: '#555' }}>{line}</p>;
          })}

          {/* ACTION BUTTONS */}
          <div style={{ marginTop: '20px', display: 'flex', gap: '10px' }}>
            <button onClick={() => setShowChat(true)} className="primary-btn" style={{ backgroundColor: '#8e44ad' }}>💬 Chat with AI Agent</button>
            <button className="primary-btn" style={{ backgroundColor: '#27ae60' }}>📅 Book Specialist</button>
            <button className="secondary-btn">📂 Upload Report</button>
          </div>
        </div>
      )}

      {/* Probability results (Visual Aid - Only show if not complete or below summary) */}
      {probabilities.length > 0 && !safeSummary && (
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

      {/* Session complete (Legacy fallback) */}
      {isComplete && !safeSummary && (
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
