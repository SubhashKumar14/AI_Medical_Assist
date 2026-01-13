import React from 'react';
import { Link } from 'react-router-dom';

const Home = () => {
    return (
        <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', maxWidth: '800px', margin: '40px auto' }}>
            <h1 style={{ fontSize: '3rem', bg: 'linear-gradient(to right, #3b82f6, #10b981)', backgroundClip: 'text', color: 'transparent' }}>
                AI Telemedicine Platform
            </h1>
            <p style={{ fontSize: '1.2rem', color: '#64748b', margin: '20px 0' }}>
                Advanced Healthcare at your fingertips. Triage, Analysis, and Consultation.
            </p>

            <div style={{ display: 'flex', gap: '20px', justifyContent: 'center', marginTop: '40px' }}>
                <Link to="/symptom-checker" className="primary-btn">Start Symptom Check</Link>
                <Link to="/login" className="secondary-btn">Login</Link>
            </div>

            <div className="dashboard-grid" style={{ marginTop: '60px', textAlign: 'left' }}>
                <div className="card">
                    <h3>🤖 AI Triage</h3>
                    <p>Check symptoms instantly with our advanced AI engine.</p>
                </div>
                <div className="card">
                    <h3>📄 Report Analysis</h3>
                    <p>Upload lab reports for instant summary and explanation.</p>
                </div>
                <div className="card">
                    <h3>📹 Video Consult</h3>
                    <p>Connect with doctors securely from home.</p>
                </div>
            </div>
        </div>
    );
};

export default Home;
