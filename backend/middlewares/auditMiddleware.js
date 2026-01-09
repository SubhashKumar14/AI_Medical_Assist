/**
 * Audit Middleware
 * 
 * Log every AI decision for compliance and review.
 * Stores audit trails for human-in-the-loop verification.
 */

/**
 * Create audit log entry
 */
const createAuditLog = (req, res, responseData) => {
  return {
    timestamp: new Date().toISOString(),
    userId: req.user?.id || 'anonymous',
    sessionId: req.body?.session_id || responseData?.session_id || null,
    action: `${req.method} ${req.path}`,
    requestData: {
      body: sanitizeBody(req.body),
      params: req.params,
      query: req.query
    },
    responseStatus: res.statusCode,
    consentTimestamp: req.consentTimestamp || null,
    ipAddress: req.ip || req.connection?.remoteAddress,
    userAgent: req.get('User-Agent')
  };
};

/**
 * Sanitize request body - remove sensitive data
 */
const sanitizeBody = (body) => {
  if (!body) return null;
  
  const sanitized = { ...body };
  
  // Remove potentially sensitive fields
  delete sanitized.password;
  delete sanitized.token;
  delete sanitized.authToken;
  
  // Truncate large text fields
  if (sanitized.text && sanitized.text.length > 500) {
    sanitized.text = sanitized.text.substring(0, 500) + '...[truncated]';
  }
  
  return sanitized;
};

/**
 * Audit middleware - logs all AI-related requests
 */
const auditMiddleware = (req, res, next) => {
  // Store original json method
  const originalJson = res.json.bind(res);
  
  // Override json method to capture response
  res.json = (data) => {
    // Create audit log
    const auditLog = createAuditLog(req, res, data);
    
    // Log to console (in production, send to logging service)
    console.log('[AUDIT]', JSON.stringify(auditLog));
    
    // TODO: In production, save to database or logging service
    // await AuditLog.create(auditLog);
    
    // Call original json method
    return originalJson(data);
  };
  
  next();
};

module.exports = auditMiddleware;
