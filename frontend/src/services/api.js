import axios from 'axios';

// Detect development environment - check for localhost on any port
const origin = window.location.origin;
const isDevelopment = origin.includes('localhost') || origin.includes('127.0.0.1');

// Determine API base URL
const baseURL = isDevelopment
  ? 'http://localhost:8000/api/v1' // Full absolute URL for dev
  : (import.meta.env.VITE_API_BASE_URL || '/api/v1'); // Relative for production

// Log API configuration with [TRACE] prefix
console.log('[TRACE] API Base URL:', baseURL);
console.log('[TRACE] API Config:', { baseURL, isDevelopment, origin, port: window.location.port });

// Create axios instance
const api = axios.create({
  baseURL: baseURL,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  timeout: 30000, // 30 second timeout
  withCredentials: true,
});

// Request interceptor - add auth token
api.interceptors.request.use(
  (config) => {
    const method = config.method?.toUpperCase() || 'UNKNOWN';
    const url = config.url || 'unknown';
    const fullUrl = `${config.baseURL}${url}`;
    
    // Get token from localStorage
    const token = localStorage.getItem('token') || localStorage.getItem('access_token');
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    console.error('[api] Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor - handle errors
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Log network errors
    if (!error.response) {
      console.error('[api] Network error:', {
        message: error.message,
        code: error.code,
        url: error.config?.url,
      });
      return Promise.reject(error);
    }
    
    // Handle 401 Unauthorized
    if (error.response.status === 401) {
      const url = error.config?.url || '';
      const isAuthMe = url.includes('/auth/me');
      const isAuthLogin = url.includes('/auth/login');
      const isAuthLogout = url.includes('/auth/logout');
      const isLoginPage = window.location.pathname === '/login' || window.location.pathname === '/';
      
      // Don't clear tokens for auth endpoints or when on login page
      if (isAuthMe || isAuthLogin || isAuthLogout || isLoginPage) {
        // Just reject - don't clear tokens
        return Promise.reject(error);
      }
      
      // For protected routes - clear tokens and redirect
      console.warn('[api] 401 on protected route - clearing tokens');
      localStorage.removeItem('token');
      localStorage.removeItem('access_token');
      localStorage.removeItem('auth');
      
      // Redirect to login with small delay
      if (!isLoginPage) {
        setTimeout(() => {
          window.location.href = '/login';
        }, 100);
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;
