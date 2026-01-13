
const mongoose = require('mongoose');

const appointmentSchema = new mongoose.Schema({
    token_id: {
        type: String,
        required: true,
        unique: true
    },
    patient_id: {
        type: String, // Can be user ID or 'anonymous'
        required: true
    },
    doctor_id: {
        type: String,
        required: true
    },
    doctor_name: {
        type: String,
        required: true
    },
    severity: {
        type: String,
        enum: ['critical', 'high', 'normal', 'low'],
        default: 'normal'
    },
    status: {
        type: String,
        enum: ['confirmed', 'completed', 'cancelled'],
        default: 'confirmed'
    },
    time_slot: {
        type: String,
        required: true
    },
    estimated_wait_minutes: {
        type: Number,
        default: 0
    },
    created_at: {
        type: Date,
        default: Date.now
    },
    completed_at: {
        type: Date
    }
});

// Index for queue sorting
appointmentSchema.index({ status: 1, severity: 1, created_at: 1 });

module.exports = mongoose.model('Appointment', appointmentSchema);
