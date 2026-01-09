/**
 * AI Routes
 * 
 * Routes for AI-related endpoints (triage, report analysis)
 */

const express = require('express');
const multer = require('multer');
const router = express.Router();

const aiProxyController = require('../controllers/aiProxyController');
const consentMiddleware = require('../middlewares/consentMiddleware');
const auditMiddleware = require('../middlewares/auditMiddleware');
const { optionalAuth } = require('../middlewares/authMiddleware');

// Configure multer for file uploads
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 10 * 1024 * 1024 // 10MB limit
  },
  fileFilter: (req, file, cb) => {
    const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
    if (allowedTypes.includes(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error('Invalid file type. Only PDF and images are allowed.'));
    }
  }
});

// Apply common middlewares
router.use(optionalAuth);
router.use(auditMiddleware);

/**
 * POST /api/triage/start
 * Start a new triage session
 */
router.post('/triage/start', consentMiddleware, aiProxyController.startTriage);

/**
 * POST /api/triage/next
 * Submit answer and get next question
 */
router.post('/triage/next', consentMiddleware, aiProxyController.nextQuestion);

/**
 * GET /api/triage/session/:sessionId
 * Get session state
 */
router.get('/triage/session/:sessionId', aiProxyController.getSession);

/**
 * POST /api/report/analyze
 * Analyze uploaded medical report
 */
router.post(
  '/report/analyze',
  upload.single('file'),
  consentMiddleware,
  aiProxyController.analyzeReport
);

module.exports = router;
