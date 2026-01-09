import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import './Dashboard.css';

const Dashboard = () => {
  const { user } = useAuth();
  // eslint-disable-next-line no-unused-vars
  const [recentActivity, setRecentActivity] = useState([]);

  // Mock data for dashboard
  const stats = [
    {
      label: 'Symptom Checks',
      value: 12,
      change: '+3 this week',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
        </svg>
      ),
      color: 'primary'
    },
    {
      label: 'Reports Analyzed',
      value: 5,
      change: '+1 this week',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14,2 14,8 20,8" />
        </svg>
      ),
      color: 'success'
    },
    {
      label: 'Red Flags Detected',
      value: 1,
      change: 'Reviewed',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      ),
      color: 'danger'
    },
    {
      label: 'Health Score',
      value: '85%',
      change: 'Good',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
      ),
      color: 'warning'
    }
  ];

  const activities = [
    { type: 'symptom', title: 'Symptom Check Completed', description: 'Headache, Fever - Probable: Viral Fever', time: '2 hours ago' },
    { type: 'report', title: 'Report Analyzed', description: 'Blood Test Report - 2 abnormal values', time: '1 day ago' },
    { type: 'alert', title: 'Red Flag Detected', description: 'High fever with chills - Immediate attention advised', time: '3 days ago' }
  ];

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div>
          <h1>Welcome back, {user?.name || 'User'}!</h1>
          <p>Here's your health overview</p>
        </div>
        <div className="header-actions">
          <button className="btn btn-primary">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            New Check
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="stats-cards">
        {stats.map((stat, idx) => (
          <div key={idx} className={`stat-card stat-${stat.color}`}>
            <div className="stat-icon">{stat.icon}</div>
            <div className="stat-info">
              <span className="stat-value">{stat.value}</span>
              <span className="stat-label">{stat.label}</span>
              <span className="stat-change">{stat.change}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="dashboard-grid">
        {/* Recent Activity */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="20" height="20">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12,6 12,12 16,14" />
              </svg>
              Recent Activity
            </h3>
          </div>
          <div className="activity-list">
            {activities.map((activity, idx) => (
              <div key={idx} className={`activity-item activity-${activity.type}`}>
                <div className="activity-indicator"></div>
                <div className="activity-content">
                  <h4>{activity.title}</h4>
                  <p>{activity.description}</p>
                  <span className="activity-time">{activity.time}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="20" height="20">
                <polygon points="13,2 3,14 12,14 11,22 21,10 12,10" />
              </svg>
              Quick Actions
            </h3>
          </div>
          <div className="quick-actions">
            <a href="/symptom-checker" className="quick-action">
              <div className="action-icon primary">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                </svg>
              </div>
              <span>Check Symptoms</span>
            </a>
            <a href="/report-analyzer" className="quick-action">
              <div className="action-icon success">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14,2 14,8 20,8" />
                </svg>
              </div>
              <span>Upload Report</span>
            </a>
            <a href="/history" className="quick-action">
              <div className="action-icon warning">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12,6 12,12 16,14" />
                </svg>
              </div>
              <span>View History</span>
            </a>
            <a href="/profile" className="quick-action">
              <div className="action-icon danger">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
              </div>
              <span>Profile</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
