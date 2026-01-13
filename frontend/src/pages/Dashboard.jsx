import React from 'react';
import { Link } from 'react-router-dom';

const Dashboard = () => {
    return (
        <div style={{ padding: '20px' }}>
            <h1>Patient Dashboard</h1>
            <div className="dashboard-grid" style={{ marginTop: '20px' }}>
                <Link to="/symptom-checker" className="card" style={{ textDecoration: 'none', color: 'inherit' }}>
                    <h3>Check Symptoms</h3>
                    <p>Start a new triage session.</p>
                </Link>
                <Link to="/booking" className="card" style={{ textDecoration: 'none', color: 'inherit' }}>
                    <h3>Book Appointment</h3>
                    <p>Schedule a visit with a specialist.</p>
                </Link>
                <Link to="/report-analyzer" className="card" style={{ textDecoration: 'none', color: 'inherit' }}>
                    <h3>My Reports</h3>
                    <p>Analyze and view medical records.</p>
                </Link>
            </div>
        </div>
    );
};

export default Dashboard;
