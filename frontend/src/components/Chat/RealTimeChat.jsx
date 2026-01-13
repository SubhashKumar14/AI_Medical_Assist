import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';

const RealTimeChat = ({ roomId, senderName }) => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const socketRef = useRef();
    const chatEndRef = useRef(null);

    useEffect(() => {
        socketRef.current = io('http://localhost:5000/consultation');

        socketRef.current.emit('join-chat', roomId);

        socketRef.current.on('chat-history', (history) => {
            setMessages(history);
        });

        socketRef.current.on('receive-message', (msg) => {
            setMessages((prev) => [...prev, msg]);
        });

        return () => socketRef.current.disconnect();
    }, [roomId]);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const sendMessage = (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        const payload = {
            roomId,
            message: input,
            senderId: socketRef.current.id,
            senderName: senderName || 'User'
        };

        socketRef.current.emit('send-message', payload);
        setInput('');
    };

    return (
        <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', borderRadius: '16px', overflow: 'hidden' }}>
            <div className="glass-header" style={{ padding: '15px' }}>
                <h4 style={{ margin: 0 }}>💬 Live Chat</h4>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: '15px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {messages.map((msg, idx) => (
                    <div key={idx} style={{
                        alignSelf: msg.senderId === socketRef.current.id ? 'flex-end' : 'flex-start',
                        background: msg.senderId === socketRef.current.id ? 'var(--primary-500)' : 'var(--gray-200)',
                        color: msg.senderId === socketRef.current.id ? 'white' : 'var(--gray-900)',
                        padding: '8px 12px',
                        borderRadius: '12px',
                        maxWidth: '80%',
                        fontSize: '0.9rem'
                    }}>
                        <div style={{ fontSize: '0.7em', opacity: 0.8, marginBottom: '2px' }}>{msg.senderName}</div>
                        {msg.message}
                    </div>
                ))}
                <div ref={chatEndRef} />
            </div>

            <form onSubmit={sendMessage} style={{ padding: '15px', borderTop: '1px solid rgba(0,0,0,0.1)', display: 'flex', gap: '10px' }}>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Type a message..."
                    style={{ flex: 1, padding: '10px', borderRadius: '8px', border: '1px solid #ccc' }}
                />
                <button type="submit" className="primary-btn" style={{ padding: '10px 15px' }}>Send</button>
            </form>
        </div>
    );
};

export default RealTimeChat;
