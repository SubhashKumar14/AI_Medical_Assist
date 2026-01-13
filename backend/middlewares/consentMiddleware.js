/**
 * Consent Middleware
 * 
 * Ensure user consent before AI processing.
 * This is a legal safety requirement.
 */

/**
 * Check if user has provided consent
 * Rejects request with 403 if consent is missing
 */
const consentMiddleware = (req, res, next) => {
  // DEBUG LOGGING
  console.log('[DEBUG] Consent Middleware Payload:', {
    body: req.body,
    headers: req.headers['content-type'],
    consentVal: req.body?.consent,
    isTrue: req.body?.consent === true
  });

  // Check consent in request body
  const consent = req.body?.consent;

  // For multipart/form-data (file uploads)
  const formConsent = req.body?.consent === 'true' || req.body?.consent === true;

  if (!consent && !formConsent) {
    // Log consent rejection
    console.log(`[CONSENT] Rejected - User: ${req.user?.id || 'anonymous'}, Path: ${req.path}`);

    return res.status(403).json({
      error: 'Consent required',
      message: 'You must provide consent before AI-assisted analysis. Please acknowledge the disclaimer and try again.',
      code: 'CONSENT_REQUIRED'
    });
  }

  // Log consent timestamp
  const consentTimestamp = new Date().toISOString();
  req.consentTimestamp = consentTimestamp;

  console.log(`[CONSENT] Accepted - User: ${req.user?.id || 'anonymous'}, Path: ${req.path}, Time: ${consentTimestamp}`);

  next();
};

module.exports = consentMiddleware;
