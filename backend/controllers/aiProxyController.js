/**
 * AI Proxy Controller
 * 
 * Responsibility:
 * - Forward requests to AI service
 * - Enforce consent before AI processing
 * - Log every AI decision for audit
 * - Handle rate limits and retries
 */

const axios = require('axios');

const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8000';
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 1000;

/**
 * Helper: Retry with exponential backoff
 */
const retryWithBackoff = async (fn, retries = MAX_RETRIES) => {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      const isRateLimited = error.response?.status === 429;
      const isServerError = error.response?.status >= 500;

      if (attempt === retries || (!isRateLimited && !isServerError)) {
        throw error;
      }

      const delay = RETRY_DELAY_MS * Math.pow(2, attempt - 1);
      console.log(`Retry attempt ${attempt}/${retries} after ${delay}ms`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
};

/**
 * POST /api/triage/start
 * Start a new triage session with initial symptoms
 */
exports.startTriage = async (req, res) => {
  try {
    const { text } = req.body;
    const userId = req.user?.id || 'anonymous';

    if (!text || typeof text !== 'string') {
      return res.status(400).json({
        error: 'Invalid request: symptom text is required'
      });
    }

    // Call AI service with retry
    const response = await retryWithBackoff(async () => {
      return axios.post(`${AI_SERVICE_URL}/start`, {
        text,
        user_id: userId,
        model_provider: req.body.model_provider || 'auto' // Forward model selection
      }, {
        timeout: 30000
      });
    });

    // Log for audit
    console.log(`[AUDIT] Triage started - User: ${userId}, SessionID: ${response.data.session_id}`);

    res.json(response.data);
  } catch (error) {
    console.error('Error in startTriage:', error.message);

    if (error.response?.status === 429) {
      return res.status(429).json({
        error: 'AI service rate limit exceeded. Please try again later.'
      });
    }

    res.status(502).json({
      error: 'AI Service temporarily unavailable. Please try again.'
    });
  }
};

/**
 * POST /api/triage/next
 * Submit answer to follow-up question, get next question or final results
 */
exports.nextQuestion = async (req, res) => {
  try {
    const { session_id, answer } = req.body;
    const userId = req.user?.id || 'anonymous';

    if (!session_id || answer === undefined) {
      return res.status(400).json({
        error: 'Invalid request: session_id and answer are required'
      });
    }

    // Call AI service with retry
    const response = await retryWithBackoff(async () => {
      return axios.post(`${AI_SERVICE_URL}/next`, {
        session_id,
        answer,
        user_id: userId
      }, {
        timeout: 30000
      });
    });

    // Log for audit
    console.log(`[AUDIT] Triage next - User: ${userId}, SessionID: ${session_id}, Answer: ${answer}`);

    res.json(response.data);
  } catch (error) {
    console.error('Error in nextQuestion:', error.message);

    if (error.response?.status === 404) {
      return res.status(404).json({
        error: 'Session not found or expired'
      });
    }

    res.status(502).json({
      error: 'AI Service temporarily unavailable. Please try again.'
    });
  }
};

/**
 * POST /api/report/analyze
 * Analyze uploaded medical report (PDF/image)
 */
exports.analyzeReport = async (req, res) => {
  try {
    const userId = req.user?.id || 'anonymous';

    if (!req.file) {
      return res.status(400).json({
        error: 'No file uploaded'
      });
    }

    // Create form data for AI service
    const FormData = require('form-data');
    const formData = new FormData();
    formData.append('file', req.file.buffer, {
      filename: req.file.originalname,
      contentType: req.file.mimetype
    });
    formData.append('user_id', userId);
    formData.append('model_provider', req.body.model_provider || 'auto'); // Forward model selection

    // Call AI service with retry
    const response = await retryWithBackoff(async () => {
      return axios.post(`${AI_SERVICE_URL}/report/analyze`, formData, {
        headers: formData.getHeaders(),
        timeout: 60000,
        maxContentLength: 15 * 1024 * 1024
      });
    });

    // Log for audit
    console.log(`[AUDIT] Report analyzed - User: ${userId}, File: ${req.file.originalname}`);

    res.json(response.data);
  } catch (error) {
    console.error('Error in analyzeReport:', error.message);

    res.status(502).json({
      error: 'Report analysis failed. Please try again.'
    });
  }
};

/**
 * GET /api/triage/session/:sessionId
 * Get current session state
 */
exports.getSession = async (req, res) => {
  try {
    const { sessionId } = req.params;
    const userId = req.user?.id || 'anonymous';

    const response = await axios.get(`${AI_SERVICE_URL}/session/${sessionId}`, {
      params: { user_id: userId },
      timeout: 10000
    });

    res.json(response.data);
  } catch (error) {
    console.error('Error in getSession:', error.message);

    if (error.response?.status === 404) {
      return res.status(404).json({
        error: 'Session not found'
      });
    }

    res.status(502).json({
      error: 'Failed to retrieve session'
    });
  }
};

/**
 * Legacy: Extract symptoms (for backwards compatibility)
 */
exports.extractSymptoms = async (req, res) => {
  try {
    const { text } = req.body;
    const response = await axios.post(`${AI_SERVICE_URL}/extract_symptoms`, { text });
    res.json(response.data);
  } catch (error) {
    console.error('Error calling AI service:', error);
    res.status(502).json({ error: 'AI Service Unavailable' });
  }
};

/**
 * POST /api/ai/chat
 * Chat with AI Assistant (Context-aware)
 */
exports.chatWithAi = async (req, res) => {
  try {
    const { session_id, message, model_provider } = req.body;
    const userId = req.user?.id || 'anonymous';

    const response = await retryWithBackoff(async () => {
      return axios.post(`${AI_SERVICE_URL}/ai/chat`, {
        session_id,
        message,
        user_id: userId,
        model_provider: model_provider || 'auto'
      }, {
        timeout: 30000
      });
    });

    res.json(response.data);
  } catch (error) {
    console.error('Error in chatWithAi:', error.message);
    res.status(502).json({ error: 'AI Chat unavailable' });
  }
};
