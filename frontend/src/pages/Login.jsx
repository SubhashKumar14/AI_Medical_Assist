import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { loginSuccess } from '../store/authSlice';

const Login = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const dispatch = useDispatch();
    const navigate = useNavigate();

    const handleLogin = (e) => {
        e.preventDefault();
        // Mock Login
        const mockUser = { id: '123', name: 'John Doe', email };
        const mockToken = 'mock-jwt-token';

        dispatch(loginSuccess({ user: mockUser, token: mockToken }));
        navigate('/dashboard');
    };

    return (
        <div className="glass-panel" style={{ maxWidth: '400px', margin: '60px auto', padding: '40px' }}>
            <h2>Login</h2>
            <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginTop: '20px' }}>
                <input
                    type="email"
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                />
                <input
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                />
                <button type="submit" className="primary-btn">Sign In</button>
            </form>
        </div>
    );
};

export default Login;
