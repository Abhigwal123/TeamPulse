import api from './api';

export const authService = {
  // Test backend connectivity before login
  checkBackendHealth: async () => {
    try {
      const response = await api.get('/health');
      return { reachable: true, status: response.data?.status || 'ok' };
    } catch (error) {
      return { 
        reachable: false, 
        error: error.code === 'ECONNREFUSED' ? 'Connection refused' : error.message 
      };
    }
  },

  login: async (username, password) => {
    try {
      console.log('Attempting login:', { 
        username, 
        endpoint: '/auth/login',
        baseURL: api.defaults.baseURL 
      });
      
      const response = await api.post('/auth/login', { username, password });
      
      console.log('Login response:', response.data);
      
      if (response.data && response.data.success && response.data.access_token) {
        // Store token as 'token' for compatibility with requirements
        localStorage.setItem('token', response.data.access_token);
        localStorage.setItem('access_token', response.data.access_token); // Keep for backward compatibility
        
        // Extract user data - handle both nested and flat structures
        const userData = response.data.user || {};
        const role = userData.role || response.data.role;
        const userID = userData.userID || userData.user_id || response.data.user_id;
        const fullName = userData.full_name || userData.fullName || userData.name;
        const usernameFromResponse = userData.username || username;
        
        // Store user and tenant info
        const authData = {
          isAuthenticated: true,
          user: {
            userID: userID,
            username: usernameFromResponse,
            role: role,
            full_name: fullName,
            ...userData, // Include any other user fields
          },
          tenant: response.data.tenant || null,
        };
        
        localStorage.setItem('auth', JSON.stringify(authData));
        console.log('Login successful, stored auth data:', authData);
        
        return {
          success: true,
          user: authData.user,
          tenant: authData.tenant,
        };
      }
      
      console.warn('Login response missing success or token:', response.data);
      return {
        success: false,
        error: response.data.error || 'Login failed',
      };
    } catch (error) {
      console.error('Login error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        statusText: error.response?.statusText,
        url: error.config?.url,
        baseURL: error.config?.baseURL,
      });
      
      // Handle different error types
      if (error.code === 'ECONNREFUSED' || error.message?.includes('Network Error')) {
        return {
          success: false,
          error: '無法連接到伺服器，請確認後端服務是否正在運行',
        };
      }
      
      if (error.response?.status === 401) {
        return {
          success: false,
          error: '帳號或密碼錯誤，請重試',
        };
      }
      
      return {
        success: false,
        error: error.response?.data?.error || error.message || '登入失敗，請檢查您的帳號和密碼',
      };
    }
  },

  logout: async () => {
    try {
      await api.post('/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      localStorage.removeItem('token');
      localStorage.removeItem('access_token');
      localStorage.removeItem('auth');
    }
  },

  getCurrentUser: async () => {
    try {
      console.log('[authService] Calling getCurrentUser()...');
      const response = await api.get('/auth/me');
      console.log('[authService] getCurrentUser response:', {
        hasData: !!response.data,
        dataKeys: response.data ? Object.keys(response.data) : [],
        hasUser: !!response.data?.user,
        hasTenant: !!response.data?.tenant,
        success: response.data?.success,
      });
      
      // Backend returns { success: true, user: {...}, tenant: {...} }
      // Ensure we always return success flag for consistency
      if (response.data && response.data.user) {
        const result = {
          success: true,
          user: response.data.user,
          tenant: response.data.tenant || null,
        };
        console.log('[authService] getCurrentUser returning success:', {
          success: result.success,
          hasUser: !!result.user,
          userRole: result.user?.role,
          hasTenant: !!result.tenant,
        });
        return result;
      }
      
      console.warn('[authService] getCurrentUser: Invalid response structure:', response.data);
      // Throw error so AuthContext can handle it properly (check for 401)
      const error = new Error('Invalid user data from getCurrentUser');
      error.response = { status: response.status || 500 };
      throw error;
    } catch (error) {
      console.error('[authService] getCurrentUser error:', {
        message: error.message,
        status: error.response?.status,
        code: error.code,
        responseData: error.response?.data,
      });
      // Re-throw error so AuthContext can check for 401 status
      // This allows AuthContext to distinguish between 401 (logout) and network errors (keep auth)
      throw error;
    }
  },
};

