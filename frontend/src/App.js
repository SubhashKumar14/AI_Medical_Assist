import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';

// Context
import { AuthProvider } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';

// Layout Components
import Navbar from './components/Layout/Navbar';
import Sidebar from './components/Layout/Sidebar';

// Pages
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';

// Feature Components (Acting as Pages)
import SymptomChecker from './components/SymptomChecker/SymptomChecker';
import ReportAnalyzer from './components/ReportAnalyzer/ReportAnalyzer';
import Booking from './components/Booking/Booking';
import DoctorDashboard from './components/DoctorDashboard/DoctorDashboard';
import VideoConsultation from './components/VideoConsultation/VideoConsultation';

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <AuthProvider>
      <ToastProvider>
        <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <div className="app">
            <Navbar onMenuClick={() => setSidebarOpen(!sidebarOpen)} />
            <div className="app-container">
              <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
              <main className="main-content">
                <Routes>
                  <Route path="/" element={<Home />} />
                  <Route path="/symptom-checker" element={<SymptomChecker />} />
                  <Route path="/report-analyzer" element={<ReportAnalyzer />} />
                  <Route path="/booking" element={<Booking />} />
                  <Route path="/consultation/:roomId" element={<VideoConsultation />} />
                  <Route path="/doctor/dashboard" element={<DoctorDashboard />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/login" element={<Login />} />
                  <Route path="/register" element={<Register />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </main>
            </div>
          </div>
        </Router>
      </ToastProvider>
    </AuthProvider>
  );
}

export default App;
