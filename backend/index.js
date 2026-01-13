/**
 * Backend Server Entry Point
 * 
 * AI Telemedicine CDSS - Node.js/Express API Gateway
 */

require('dotenv').config();

const express = require('express');
const cors = require('cors');
const mongoose = require('mongoose');

// Routes
const aiRoutes = require('./routes/aiRoutes');
const authRoutes = require('./routes/authRoutes');

const http = require('http');
const { Server } = require('socket.io');

const app = express();
const server = http.createServer(app); // Create HTTP server
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors({
  origin: process.env.CORS_ORIGIN || 'http://localhost:3000',
  credentials: true
}));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Socket.io Setup
const io = new Server(server, {
  cors: {
    origin: "http://localhost:3000",
    methods: ["GET", "POST"]
  }
});

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// API Routes
app.use('/api/auth', authRoutes);
app.use('/api', aiRoutes);
// app.use('/api/records', recordRoutes); // Disabled until created
app.use('/api', require('./routes/appointmentRoutes')); // Added Appointment Routes

// Socket Handlers
require('./sockets/signalingHandler')(io);
require('./sockets/chatHandler')(io);

// Error handling
app.use((err, req, res, next) => {
  console.error('Error:', err.message);
  res.status(500).json({
    error: 'Internal server error',
    message: err.message
  });
});

// Database
const connectDB = async () => {
  try {
    if (process.env.MONGODB_URI) {
      await mongoose.connect(process.env.MONGODB_URI);
      console.log('MongoDB connected');
    } else {
      console.log('MongoDB URI not configured - running without database');
    }
  } catch (error) {
    console.error('MongoDB connection error:', error.message);
  }
};

// Start Server (Listen on HTTP Server, not App)
const startServer = async () => {
  await connectDB();

  server.listen(PORT, () => {
    console.log(`🚀 Backend server running on port ${PORT}`);
    console.log(`📍 Health check: http://localhost:${PORT}/health`);
    console.log(`🔌 Socket.io initialized`);
  });
};

startServer();

module.exports = app;
