import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useSelector } from 'react-redux'; // Added
import { bookingAPI } from '../../services/api';

const Booking = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const { user } = useSelector(state => state.auth); // Get real user

    // Get triage state passed from SymptomChecker (if available)
    const { triageSeverity, triageSummary } = location.state || {};

    const [doctors, setDoctors] = useState([]); // State for doctors
    const [selectedDoctor, setSelectedDoctor] = useState(null);
    const [selectedSlot, setSelectedSlot] = useState(null);
    const [loading, setLoading] = useState(false);
    const [bookingSuccess, setBookingSuccess] = useState(null);
    const [error, setError] = useState(null);

    // Fetch Doctors on mount
    useEffect(() => {
        const fetchDoctors = async () => {
            try {
                const res = await bookingAPI.getDoctors();
                setDoctors(res.data);
            } catch (err) {
                console.error("Failed to load doctors", err);
            }
        };
        fetchDoctors();
    }, []);

    // Auto-select urgency based on severity
    const isCritical = triageSeverity === 'high' || triageSeverity === 'critical';

    const handleBook = async () => {
        if (!selectedDoctor || (!selectedSlot && !isCritical)) {
            setError("Please select a doctor and time slot.");
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const response = await bookingAPI.book({
                patient_id: user?.id || "anonymous", // Real User ID
                doctor_id: selectedDoctor.id,
                severity: isCritical ? 'critical' : 'normal',
                time_slot: isCritical ? 'IMMEDIATE' : selectedSlot // Auto-assign immediate for critical
            });

            setBookingSuccess(response.data);
        } catch (err) {
            setError(err.response?.data?.detail || "Booking failed");
        } finally {
            setLoading(false);
        }
    };

    if (bookingSuccess) {
        return (
            <div className="booking-confirmation" style={{ textAlign: 'center', padding: '40px' }}>
                <div style={{ backgroundColor: '#ecfdf5', padding: '30px', borderRadius: '15px', border: '2px solid #10b981', display: 'inline-block' }}>
                    <h1 style={{ fontSize: '3rem', margin: '0 0 10px 0' }}>✅</h1>
                    <h2>Booking Confirmed!</h2>

                    <div className="token-card" style={{
                        marginTop: '20px',
                        padding: '20px',
                        backgroundColor: 'white',
                        borderRadius: '10px',
                        boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
                        borderTop: `5px solid ${bookingSuccess.token_id.startsWith('CRIT') ? '#dc2626' : '#3b82f6'}`
                    }}>
                        <p style={{ fontSize: '0.9rem', color: '#666', marginBottom: '5px' }}>YOUR TOKEN NUMBER</p>
                        <h1 style={{ fontSize: '2.5rem', margin: '0', color: '#1f2937' }}>{bookingSuccess.token_id}</h1>
                        <p style={{ marginTop: '10px', fontWeight: 'bold' }}>
                            Estimated Wait: <span style={{ color: '#d97706' }}>{bookingSuccess.estimated_wait_minutes} mins</span>
                        </p>
                    </div>

                    <p style={{ marginTop: '20px' }}>
                        Doctor: <strong>{doctors.find(d => d.id === bookingSuccess.doctor_id)?.name}</strong><br />
                        Time: <strong>{bookingSuccess.time_slot}</strong>
                    </p>

                    <button onClick={() => navigate('/')} className="primary-btn" style={{ marginTop: '20px' }}>Return Home</button>
                </div>
            </div>
        );
    }

    return (
        <div className="booking-container" style={{ maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
            <h2>📅 Book Appointment</h2>

            {triageSeverity && (
                <div className="triage-alert" style={{
                    backgroundColor: isCritical ? '#fee2e2' : '#e0f2fe',
                    padding: '15px', borderRadius: '8px', marginBottom: '20px',
                    borderLeft: `5px solid ${isCritical ? '#dc2626' : '#0ea5e9'}`
                }}>
                    <strong>Note from Triage:</strong>
                    {isCritical ? " Your condition was flagged as High Risk. We have prioritized your slot." : " Standard appointment booking."}
                </div>
            )}

            <div className="doctor-selection" style={{ marginBottom: '30px' }}>
                <h3>1. Select Specialist</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '15px' }}>
                    {doctors.map(doc => (
                        <div
                            key={doc.id}
                            onClick={() => setSelectedDoctor(doc)}
                            style={{
                                padding: '15px',
                                border: selectedDoctor?.id === doc.id ? '2px solid #3b82f6' : '1px solid #ddd',
                                borderRadius: '8px', cursor: 'pointer',
                                backgroundColor: selectedDoctor?.id === doc.id ? '#eff6ff' : 'white'
                            }}
                        >
                            <div style={{ fontWeight: 'bold' }}>{doc.name}</div>
                            <div style={{ fontSize: '0.9rem', color: '#666' }}>{doc.specialty}</div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="slot-selection">
                <h3>2. Select Time Slot</h3>
                {isCritical ? (
                    <div style={{ padding: '15px', backgroundColor: '#fff3cd', borderRadius: '8px', textAlign: 'center' }}>
                        <p>⚡ <strong>Emergency Priority Active</strong></p>
                        <p>We are booking you into the earliest possible slot automatically.</p>
                    </div>
                ) : (
                    <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                        {['09:00 AM', '10:00 AM', '11:30 AM', '02:00 PM', '04:00 PM'].map(slot => (
                            <button
                                key={slot}
                                onClick={() => setSelectedSlot(slot)}
                                style={{
                                    padding: '10px 20px',
                                    border: '1px solid #ccc', borderRadius: '5px',
                                    backgroundColor: selectedSlot === slot ? '#3b82f6' : 'white',
                                    color: selectedSlot === slot ? 'white' : 'black',
                                    cursor: 'pointer'
                                }}
                            >
                                {slot}
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {error && <p style={{ color: 'red', marginTop: '20px' }}>{error}</p>}

            <button
                onClick={handleBook}
                disabled={loading}
                className="primary-btn"
                style={{
                    marginTop: '30px', width: '100%', padding: '15px', fontSize: '1.2rem',
                    backgroundColor: isCritical ? '#dc2626' : undefined
                }}
            >
                {loading ? 'Processing...' : (isCritical ? '🚨 Book Immediate Priority Slot' : 'Confirm Appointment')}
            </button>
        </div>
    );
};

export default Booking;
