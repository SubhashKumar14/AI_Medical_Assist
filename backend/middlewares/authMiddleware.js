/**
 * Authentication Middleware
 * 
 * Verify JWT tokens for protected routes.
 */

const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key-change-in-production';

/**
 * Verify JWT token middleware
 */
const authMiddleware = (req, res, next) => {
  // Get token from header
  const authHeader = req.headers.authorization;
  
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({
      error: 'Authentication required',
      message: 'Please log in to access this resource',
      code: 'AUTH_REQUIRED'
    });
  }
  
  const token = authHeader.split(' ')[1];
  
  try {
    // Verify token
    const decoded = jwt.verify(token, JWT_SECRET);
    
    // Attach user info to request
    req.user = {
      id: decoded.id || decoded.userId,
      email: decoded.email,
      role: decoded.role || 'user'
    };
    
    next();
  } catch (error) {
    if (error.name === 'TokenExpiredError') {
      return res.status(401).json({
        error: 'Token expired',
        message: 'Your session has expired. Please log in again.',
        code: 'TOKEN_EXPIRED'
      });
    }
    
    return res.status(401).json({
      error: 'Invalid token',
      message: 'Authentication failed. Please log in again.',
      code: 'INVALID_TOKEN'
    });
  }
};

/**
 * Optional auth - attach user if token exists, but don't require it
 */
const optionalAuth = (req, res, next) => {
  const authHeader = req.headers.authorization;
  
  if (authHeader && authHeader.startsWith('Bearer ')) {
    const token = authHeader.split(' ')[1];
    
    try {
      const decoded = jwt.verify(token, JWT_SECRET);
      req.user = {
        id: decoded.userId,
        email: decoded.email,
        role: decoded.role || 'patient'
      };
    } catch (error) {
      // Token invalid but continue without user
      req.user = null;
    }
  } else {
    req.user = null;
  }
  
  next();
};

/**
 * Role-based access control
 */
const requireRole = (...roles) => {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({
        error: 'Authentication required',
        code: 'AUTH_REQUIRED'
      });
    }
    
    if (!roles.includes(req.user.role)) {
      return res.status(403).json({
        error: 'Access denied',
        message: 'You do not have permission to access this resource',
        code: 'INSUFFICIENT_ROLE'
      });
    }
    
    next();
  };
};

module.exports = {
  authMiddleware,
  protect: authMiddleware,
  optionalAuth,
  requireRole
};
