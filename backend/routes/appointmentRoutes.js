
const express = require('express');
const router = express.Router();
const appointmentController = require('../controllers/appointmentController');
const { optionalAuth } = require('../middlewares/authMiddleware');

// Public routes (or protected if you want)
router.get('/doctors', appointmentController.getDoctors);
router.post('/appointments/book', optionalAuth, appointmentController.bookAppointment);

// Doctor routes (Should be protected by doctor auth in real app)
router.get('/doctor/queue', appointmentController.getQueue);
router.post('/doctor/complete/:tokenId', appointmentController.completeAppointment);

module.exports = router;
