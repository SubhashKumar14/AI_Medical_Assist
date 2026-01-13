import React, { useState, useEffect } from 'react';
import { doctorAPI } from '../../services/api';

const DoctorDashboard = () => {
    const [queue, setQueue] = useState([]);
    const [loading, setLoading] = useState(false);

    const fetchQueue = async () => {
        setLoading(true);
        try {
            const res = await doctorAPI.getQueue();
            setQueue(res.data);
        } catch (err) {
            console.error("Failed to fetch queue", err);
        } finally {
            setLoading(false);
        }
    };

    const handleComplete = async (tokenId) => {
        try {
            await doctorAPI.complete(tokenId);
            fetchQueue(); // Refresh
        } catch (err) {
            alert("Failed to complete appointment");
        }
    };

    useEffect(() => {
        fetchQueue();
        const interval = setInterval(fetchQueue, 30000); // Poll every 30s
        return () => clearInterval(interval);
    }, []);

    // Stats
    const criticalCount = queue.filter(p => p.severity === 'critical').length;
    // Calculate real average wait time from queue
    const avgWait = queue.length > 0
        ? Math.round(queue.reduce((acc, curr) => acc + (curr.estimated_wait_minutes || 0), 0) / queue.length)
        : 0;

    return (
        <div className="doctor-dashboard" style={{ padding: '20px', backgroundColor: '#f3f4f6', minHeight: '100vh' }}>
            <div className="header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
                <div>
                    <h1 style={{ margin: 0, color: '#111827' }}>👨‍⚕️ Doctor Dashboard</h1>
                    <p style={{ margin: 0, color: '#6b7280' }}>Dr. Sarah Smith • General Physician</p>
                </div>
                <div className="stats-bar" style={{ display: 'flex', gap: '20px' }}>
                    <div className="stat-card" style={{ backgroundColor: 'white', padding: '15px 25px', borderRadius: '10px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
                        <div style={{ fontSize: '0.9rem', color: '#6b7280' }}>Waiting</div>
                        <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{queue.length}</div>
                    </div>
                    <div className="stat-card" style={{ backgroundColor: '#fee2e2', padding: '15px 25px', borderRadius: '10px', border: '1px solid #ef4444' }}>
                        <div style={{ fontSize: '0.9rem', color: '#b91c1c' }}>Critical</div>
                        <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#b91c1c' }}>{criticalCount}</div>
                    </div>
                    <div className="stat-card" style={{ backgroundColor: 'white', padding: '15px 25px', borderRadius: '10px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
                        <div style={{ fontSize: '0.9rem', color: '#6b7280' }}>Avg Wait</div>
                        <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{avgWait}m</div>
                    </div>
                </div>
            </div>

            <div className="queue-section">
                <h2 style={{ color: '#374151', marginBottom: '20px' }}>Priority Patient Queue</h2>

                {loading && queue.length === 0 && <p>Loading queue...</p>}

                {queue.length === 0 && !loading ? (
                    <div style={{ textAlign: 'center', padding: '50px', color: '#6b7280' }}>
                        <h3>🎉 All caught up!</h3>
                        <p>No pending appointments in your queue.</p>
                    </div>
                ) : (
                    <div className="appointment-list" style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                        {queue.map((apt) => (
                            <div key={apt.token_id} className="apt-card" style={{
                                backgroundColor: 'white',
                                padding: '20px',
                                borderRadius: '12px',
                                boxShadow: '0 2px 5px rgba(0,0,0,0.05)',
                                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                borderLeft: `6px solid ${apt.severity === 'critical' ? '#dc2626' : apt.severity === 'high' ? '#d97706' : '#3b82f6'}`
                            }}>
                                <div className="apt-info">
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                        <h3 style={{ margin: 0 }}>{apt.token_id}</h3>
                                        <span style={{
                                            padding: '4px 8px', borderRadius: '4px', fontSize: '0.8rem', fontWeight: 'bold', textTransform: 'uppercase',
                                            backgroundColor: apt.severity === 'critical' ? '#fee2e2' : '#eff6ff',
                                            color: apt.severity === 'critical' ? '#dc2626' : '#1d4ed8'
                                        }}>
                                            {apt.severity}
                                        </span>
                                    </div>
                                    <p style={{ margin: '5px 0 0 0', color: '#6b7280' }}>
                                        Patient ID: {apt.patient_id} • Waited: {apt.estimated_wait_minutes}m
                                    </p>
                                </div>

                                <div className="apt-actions" style={{ display: 'flex', gap: '10px' }}>
                                    <button className="secondary-btn" style={{ padding: '10px 20px', border: '1px solid #d1d5db', borderRadius: '6px', background: 'white', cursor: 'pointer' }}>
                                        📄 View History
                                    </button>
                                    <button className="primary-btn" style={{ padding: '10px 20px', borderRadius: '6px', background: '#3b82f6', color: 'white', border: 'none', cursor: 'pointer' }}>
                                        📹 Call Patient
                                    </button>
                                    <button
                                        onClick={() => handleComplete(apt.token_id)}
                                        className="success-btn"
                                        style={{ padding: '10px 20px', borderRadius: '6px', background: '#10b981', color: 'white', border: 'none', cursor: 'pointer' }}
                                    >
                                        ✅ Complete
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default DoctorDashboard;
