/**
 * API Service
 * 
 * Centralized axios instance for all API calls.
 * Handles authentication, error handling, and base URL configuration.
 */

import axios from 'axios';

// Base URL from environment or default to localhost
const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

// Create axios instance
const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000, // 30 second timeout
  headers: {
    'Content-Type': 'application/json'
  }
});

// Request interceptor - add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handle errors globally
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle specific error codes
    if (error.response) {
      switch (error.response.status) {
        case 401:
          // Unauthorized - clear token and redirect
          localStorage.removeItem('token');
          if (window.location.pathname !== '/login') {
            window.location.href = '/login';
          }
          break;
        case 403:
          // Forbidden - consent or permission issue
          console.error('Permission denied:', error.response.data);
          break;
        case 429:
          // Rate limited
          console.error('Rate limit exceeded. Please try again later.');
          break;
        case 502:
        case 503:
          // AI service unavailable
          console.error('AI service temporarily unavailable');
          break;
        default:
          break;
      }
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  register: (data) => api.post('/auth/register', data),
  getProfile: () => api.get('/auth/me'),
  updateProfile: (data) => api.put('/auth/profile', data)
};

// AI Triage API
export const triageAPI = {
  start: (text, consent = true, model = 'auto') => api.post('/triage/start', { text, consent, model_provider: model }),
  next: (sessionId, answer, consent = true) => api.post('/triage/next', { session_id: sessionId, answer, consent }),
  getSession: (sessionId) => api.get(`/triage/session/${sessionId}`)
};

// AI Chat API
export const chatAPI = {
  sendMessage: (sessionId, message, model = 'auto') => api.post('/ai/chat', {
    session_id: sessionId,
    message,
    model_provider: model,
    consent: true // Required by backend
  })
};

// Report API
export const reportAPI = {
  analyze: (formData) => api.post('/report/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  getHistory: () => api.get('/reports'),
  getReport: (id) => api.get(`/reports/${id}`)
};

// Health Records API
export const recordsAPI = {
  getAll: () => api.get('/records'),
  create: (data) => api.post('/records', data),
  update: (id, data) => api.put(`/records/${id}`, data),
  delete: (id) => api.delete(`/records/${id}`)
};

// Booking API
export const bookingAPI = {
  book: (data) => api.post('/appointments/book', data),
  getDoctors: () => api.get('/doctors')
};

// Doctor Portal API
export const doctorAPI = {
  getQueue: () => api.get('/doctor/queue'),
  complete: (tokenId) => api.post(`/doctor/complete/${tokenId}`)
};

export default api;
