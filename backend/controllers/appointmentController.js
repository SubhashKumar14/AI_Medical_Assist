
const Appointment = require('../models/Appointment');
const { v4: uuidv4 } = require('uuid');

// Server-side source of truth for doctors
// In a full system, this would come from a User/Doctor collection
const DOCTORS = [
    { id: 'dr_smith', name: 'Dr. Sarah Smith', specialty: 'General Physician', available: true },
    { id: 'dr_lee', name: 'Dr. Bruce Lee', specialty: 'Cardiologist', available: true },
    { id: 'dr_patel', name: 'Dr. Aniya Patel', specialty: 'Dermatologist', available: true },
];

/**
 * Generate Smart Token
 * Format: [Current Daily Count for Severity]-[SeverityCode]
 * e.g., CRIT-001, REG-102
 */
const generateToken = async (severity) => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const count = await Appointment.countDocuments({
        created_at: { $gte: today },
        severity: severity
    });

    const prefix = severity === 'critical' ? 'CRIT' : severity === 'high' ? 'HIGH' : 'REG';
    const seq = String(count + 1).padStart(3, '0');
    return `${prefix}-${seq}`;
};

/**
 * Estimate Wait Time
 * Logic: 15 mins per patient in queue
 */
const estimateWaitTime = async (severity) => {
    if (severity === 'critical') return 0; // Immediate

    const queueLength = await Appointment.countDocuments({
        status: 'confirmed',
        severity: { $in: ['high', 'normal'] } // Count people ahead
    });

    // Simple logic: 15 mins per person
    // If high priority, maybe jump queue? 
    // Keeping it simple for now: valid wait time logic
    return Math.max(0, queueLength * 15);
};

// GET /api/doctors
exports.getDoctors = (req, res) => {
    res.json(DOCTORS);
};

// POST /api/appointments/book
exports.bookAppointment = async (req, res) => {
    try {
        const { doctor_id, time_slot, severity, patient_id } = req.body;
        const userId = req.user?.id || patient_id || 'anonymous';

        // Validate doctor
        const doctor = DOCTORS.find(d => d.id === doctor_id);
        if (!doctor) {
            return res.status(400).json({ error: 'Invalid doctor ID' });
        }

        const token_id = await generateToken(severity);
        const wait_time = await estimateWaitTime(severity);

        const appointment = new Appointment({
            token_id,
            patient_id: userId,
            doctor_id,
            doctor_name: doctor.name,
            severity,
            time_slot: severity === 'critical' ? 'IMMEDIATE' : time_slot,
            estimated_wait_minutes: wait_time
        });

        await appointment.save();

        res.json(appointment);
    } catch (error) {
        console.error("Booking Error:", error);
        res.status(500).json({ error: "Failed to book appointment" });
    }
};

// GET /api/doctor/queue
exports.getQueue = async (req, res) => {
    try {
        // Fetch confirmed appointments
        const appointments = await Appointment.find({ status: 'confirmed' });

        // Sort logic: Critical First, then High, then Normal. Then by Time.
        const severityWeight = { 'critical': 0, 'high': 1, 'normal': 2, 'low': 3 };

        appointments.sort((a, b) => {
            const weightA = severityWeight[a.severity];
            const weightB = severityWeight[b.severity];

            if (weightA !== weightB) return weightA - weightB;
            return new Date(a.created_at) - new Date(b.created_at);
        });

        res.json(appointments);
    } catch (error) {
        res.status(500).json({ error: "Failed to fetch queue" });
    }
};

// POST /api/doctor/complete/:tokenId
exports.completeAppointment = async (req, res) => {
    try {
        const { tokenId } = req.params;
        const apt = await Appointment.findOneAndUpdate(
            { token_id: tokenId },
            { status: 'completed', completed_at: new Date() },
            { new: true }
        );

        if (!apt) return res.status(404).json({ error: "Appointment not found" });

        res.json({ status: 'success', appointment: apt });
    } catch (error) {
        res.status(500).json({ error: "Failed to update appointment" });
    }
};
