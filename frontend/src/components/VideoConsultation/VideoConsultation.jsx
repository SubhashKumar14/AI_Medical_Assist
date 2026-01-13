import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useWebRTC } from '../../hooks/useWebRTC';
import RealTimeChat from '../Chat/RealTimeChat';

const VideoConsultation = () => {
    const { roomId } = useParams();
    const navigate = useNavigate();
    const { localVideoRef, remoteVideoRef, isCallActive } = useWebRTC(roomId);

    return (
        <div className="video-page-container" style={{ display: 'flex', height: 'calc(100vh - 80px)', gap: '20px', padding: '20px' }}>

            {/* Video Area (Main) */}
            <div className="video-consultation" style={{ flex: 3, background: '#111827', borderRadius: '16px', overflow: 'hidden', position: 'relative', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                {/* Main Remote Video */}
                <video
                    ref={remoteVideoRef}
                    autoPlay
                    playsInline
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />

                {!isCallActive && (
                    <div style={{ position: 'absolute', color: 'white', background: 'rgba(0,0,0,0.5)', padding: '20px', borderRadius: '10px' }}>
                        <h3>Waiting for Patient/Doctor to join...</h3>
                        <p>Room ID: {roomId}</p>
                    </div>
                )}

                {/* Local Video Overlay */}
                <div style={{ position: 'absolute', bottom: '20px', right: '20px', width: '200px', height: '150px', border: '2px solid white', borderRadius: '10px', overflow: 'hidden', boxShadow: '0 4px 6px rgba(0,0,0,0.3)' }}>
                    <video
                        ref={localVideoRef}
                        autoPlay
                        playsInline
                        muted
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                </div>

                {/* Controls */}
                <div className="controls glass-panel" style={{ position: 'absolute', bottom: '30px', left: '50%', transform: 'translateX(-50%)', padding: '15px 30px', borderRadius: '50px', display: 'flex', gap: '20px' }}>
                    <button className="btn btn-icon" style={{ background: '#ef4444', color: 'white' }} onClick={() => navigate('/dashboard')}>
                        ❌ End Call
                    </button>
                    <button className="btn btn-icon" style={{ background: 'white' }}>
                        🎤 Mute
                    </button>
                    <button className="btn btn-icon" style={{ background: 'white' }}>
                        📹 Cam
                    </button>
                </div>
            </div>

            {/* Chat Sidebar */}
            <div className="chat-sidebar" style={{ flex: 1, minWidth: '300px' }}>
                <RealTimeChat roomId={roomId} senderName="User" />
            </div>
        </div>
    );
};

export default VideoConsultation;
