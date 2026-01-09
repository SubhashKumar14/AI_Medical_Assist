/**
 * Report Analysis Model
 * Stores medical report analysis results
 */

const mongoose = require('mongoose');

const reportAnalysisSchema = new mongoose.Schema({
  user: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: false
  },
  reportId: {
    type: String,
    required: true,
    unique: true
  },
  reportType: {
    type: String,
    enum: ['cbc', 'lipid', 'liver', 'kidney', 'thyroid', 'sugar', 'other'],
    default: 'other'
  },
  originalFileName: {
    type: String
  },
  extractedText: {
    type: String
  },
  parameters: [{
    name: String,
    value: String,
    unit: String,
    referenceRange: String,
    status: {
      type: String,
      enum: ['normal', 'high', 'low', 'critical'],
      default: 'normal'
    }
  }],
  summary: {
    type: String
  },
  redFlags: [String],
  recommendations: [String],
  explanation: {
    type: String
  },
  aiModelUsed: {
    type: String,
    default: 'local'
  },
  consent: {
    type: Boolean,
    required: true
  },
  processingTime: {
    type: Number // in milliseconds
  }
}, {
  timestamps: true
});

// Indexes
reportAnalysisSchema.index({ reportId: 1 });
reportAnalysisSchema.index({ user: 1, createdAt: -1 });

module.exports = mongoose.model('ReportAnalysis', reportAnalysisSchema);
