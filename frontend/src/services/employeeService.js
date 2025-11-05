
import api from './api';

export const employeeService = {
  getMySchedule: async (month = null) => {
    const params = month ? { month } : {};
    const response = await api.get('/employee/schedule', { params });
    return response.data;
  },

  getScheduleData: async (scheduleDefId = null) => {
    const params = scheduleDefId ? { schedule_def_id: scheduleDefId } : {};
    const response = await api.get('/employee/schedule-data', { params });
    return response.data;
  },

  // New endpoint for schedule data with trace logging
  getSchedule: async (month = null) => {
    try {
      console.log(`[TRACE] Frontend: Fetching schedule for month=${month}`);
      console.log(`[TRACE] Frontend: API base URL: ${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'}`);
      
      const params = month ? { month } : {};
      const response = await api.get('/schedule/', { params });
      
      console.log(`[DEBUG] ========== FRONTEND API RESPONSE ==========`);
      console.log(`[DEBUG] Response status:`, response.status);
      console.log(`[DEBUG] Response data type:`, typeof response.data, Array.isArray(response.data) ? 'Array' : 'Object');
      console.log(`[DEBUG] Response data:`, response.data);
      console.log(`[DEBUG] Response data keys:`, response.data && typeof response.data === 'object' && !Array.isArray(response.data) ? Object.keys(response.data) : 'N/A');
      
      // Log structure details
      if (response.data && typeof response.data === 'object' && !Array.isArray(response.data)) {
        console.log(`[DEBUG] Response structure:`);
        console.log(`[DEBUG]   - success:`, response.data.success);
        console.log(`[DEBUG]   - schedule:`, response.data.schedule, `(type: ${typeof response.data.schedule}, isArray: ${Array.isArray(response.data.schedule)}, length: ${Array.isArray(response.data.schedule) ? response.data.schedule.length : 'N/A'})`);
        console.log(`[DEBUG]   - month:`, response.data.month);
        console.log(`[DEBUG]   - error:`, response.data.error);
        if (response.data.schedule && Array.isArray(response.data.schedule)) {
          console.log(`[DEBUG]   - schedule entries: ${response.data.schedule.length}`);
          if (response.data.schedule.length > 0) {
            console.log(`[DEBUG]   - First entry:`, response.data.schedule[0]);
          }
        }
      } else if (Array.isArray(response.data)) {
        console.log(`[DEBUG] ⚠️ Response is array directly, length:`, response.data.length);
        if (response.data.length > 0) {
          console.log(`[DEBUG]   - First array item:`, response.data[0]);
        }
      }
      console.log(`[DEBUG] ===========================================`);
      
      // Handle case where backend returns array directly
      if (Array.isArray(response.data)) {
        console.log(`[TRACE] Frontend: Response is array, converting to object format`);
        return {
          success: true,
          schedule: response.data,
          month: month
        };
      }
      
      // Handle both success and non-success responses
      if (response.data && typeof response.data === 'object' && response.data.success !== false) {
        console.log(`[TRACE] Frontend: Schedule loaded successfully, entries=${response.data.schedule?.length || 0}`);
        return response.data;
      } else if (response.data && typeof response.data === 'object') {
        console.error(`[TRACE] Frontend: Schedule fetch failed - ${response.data?.error || 'Unknown error'}`);
        return response.data || { success: false, error: 'Unknown error', schedule: [] };
      } else {
        // Unknown format
        console.warn(`[TRACE] Frontend: Unexpected response format, treating as empty`);
        return { success: true, schedule: [], month: month };
      }
    } catch (error) {
      console.error('[DEBUG] ========== FRONTEND API ERROR ==========');
      console.error('[DEBUG] Error type:', error.name);
      console.error('[DEBUG] Error message:', error.message);
      console.error('[DEBUG] Response status:', error.response?.status);
      console.error('[DEBUG] Response data:', error.response?.data);
      console.error('[DEBUG] =========================================');
      
      // Return a structured error response instead of throwing
      return {
        success: false,
        error: error.response?.data?.error || error.message || 'Failed to fetch schedule',
        schedule: []
      };
    }
  },

  submitLeaveRequest: async (data) => {
    const response = await api.post('/employee/requests/leave', data);
    return response.data;
  },
};
