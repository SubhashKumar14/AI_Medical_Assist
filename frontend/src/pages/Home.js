import React from 'react';
import { Link } from 'react-router-dom';
import './Home.css';

const Home = () => {
  const features = [
    {
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
        </svg>
      ),
      title: 'AI Symptom Checker',
      description: 'Describe your symptoms and get AI-powered insights with probable conditions ranked by likelihood.',
      link: '/symptom-checker',
      color: 'primary'
    },
    {
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14,2 14,8 20,8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
        </svg>
      ),
      title: 'Report Analyzer',
      description: 'Upload medical reports (PDF/Image) for AI-assisted analysis and abnormal value detection.',
      link: '/report-analyzer',
      color: 'success'
    },
    {
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
      ),
      title: 'Explainable AI',
      description: 'Understand why the AI suggests certain conditions with transparent symptom contribution analysis.',
      link: '/symptom-checker',
      color: 'warning'
    },
    {
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
      ),
      title: 'Safety First',
      description: 'Critical symptoms are automatically detected and flagged for immediate medical attention.',
      link: '/symptom-checker',
      color: 'danger'
    }
  ];

  const stats = [
    { value: '90+', label: 'Disease Patterns' },
    { value: '15+', label: 'Red Flag Symptoms' },
    { value: '30+', label: 'Lab Parameters' },
    { value: '24/7', label: 'Available' }
  ];

  return (
    <div className="home">
      {/* Hero Section */}
      <section className="hero">
        <div className="hero-content">
          <div className="hero-badge">
            <span className="badge-icon">🏥</span>
            AI-Powered Clinical Decision Support
          </div>
          <h1 className="hero-title">
            Your Health Companion
            <span className="gradient-text"> Powered by AI</span>
          </h1>
          <p className="hero-description">
            Get intelligent health insights with our advanced symptom checker and medical report analyzer. 
            Our AI assists in understanding your health conditions while ensuring a doctor always has the final say.
          </p>
          <div className="hero-actions">
            <Link to="/symptom-checker" className="btn btn-primary btn-lg">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="20" height="20">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
              </svg>
              Check Symptoms
            </Link>
            <Link to="/report-analyzer" className="btn btn-outline btn-lg">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="20" height="20">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14,2 14,8 20,8" />
              </svg>
              Analyze Report
            </Link>
          </div>
        </div>
        <div className="hero-visual">
          <div className="visual-card">
            <div className="pulse-ring"></div>
            <div className="pulse-ring delay-1"></div>
            <div className="pulse-ring delay-2"></div>
            <div className="heart-icon">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
              </svg>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="stats-section">
        <div className="stats-grid">
          {stats.map((stat, idx) => (
            <div key={idx} className="stat-item">
              <div className="stat-value">{stat.value}</div>
              <div className="stat-label">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <div className="section-header">
          <h2 className="section-title">Intelligent Health Features</h2>
          <p className="section-description">
            Advanced AI capabilities to help you understand your health better
          </p>
        </div>
        <div className="features-grid">
          {features.map((feature, idx) => (
            <Link to={feature.link} key={idx} className={`feature-card feature-${feature.color}`}>
              <div className="feature-icon">{feature.icon}</div>
              <h3 className="feature-title">{feature.title}</h3>
              <p className="feature-description">{feature.description}</p>
              <span className="feature-link">
                Learn more
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12,5 19,12 12,19" />
                </svg>
              </span>
            </Link>
          ))}
        </div>
      </section>

      {/* Disclaimer Section */}
      <section className="disclaimer-section">
        <div className="disclaimer-card">
          <div className="disclaimer-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <div className="disclaimer-content">
            <h3>Important Medical Disclaimer</h3>
            <p>
              This AI system is a <strong>Clinical Decision Support System (CDSS)</strong>, not a diagnostic tool. 
              All AI outputs are assistive insights and must be reviewed by licensed healthcare professionals. 
              For medical emergencies, please contact emergency services immediately.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Home;
