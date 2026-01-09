/**
 * Triage Session Model
 * Stores symptom checker sessions and results
 */

const mongoose = require('mongoose');

const triageSessionSchema = new mongoose.Schema({
  user: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: false // Allow anonymous sessions
  },
  sessionId: {
    type: String,
    required: true,
    unique: true
  },
  initialSymptoms: {
    type: String,
    required: true
  },
  questionsAnswered: [{
    question: String,
    answer: String,
    timestamp: {
      type: Date,
      default: Date.now
    }
  }],
  results: {
    probabilities: [{
      disease: String,
      probability: Number,
      contributingSymptoms: [String]
    }],
    redFlags: [String],
    urgencyLevel: {
      type: String,
      enum: ['low', 'medium', 'high', 'emergency'],
      default: 'low'
    }
  },
  isComplete: {
    type: Boolean,
    default: false
  },
  consent: {
    type: Boolean,
    required: true
  },
  status: {
    type: String,
    enum: ['active', 'completed', 'abandoned'],
    default: 'active'
  }
}, {
  timestamps: true
});

// Index for faster lookups
triageSessionSchema.index({ sessionId: 1 });
triageSessionSchema.index({ user: 1, createdAt: -1 });

module.exports = mongoose.model('TriageSession', triageSessionSchema);
