# Frontend API Documentation

This document provides detailed documentation for how the frontend calls backend API endpoints.

**Base URL Configuration:**
- Development: `http://localhost:8000/api/v1`
- Production: `/api/v1` (relative) or `VITE_API_BASE_URL` environment variable

**Authentication:** Tokens are stored in `localStorage` as `token` and automatically added to requests via axios interceptors.

---

## Table of Contents

- [API Service Setup](#api-service-setup)
- [Authentication Service](#authentication-service)
- [User Service](#user-service)
- [Department Service](#department-service)
- [Tenant Service](#tenant-service)
- [Schedule Service](#schedule-service)
- [Employee Service](#employee-service)
- [Client Admin Service](#client-admin-service)
- [Schedule Manager Service](#schedule-manager-service)
- [System Admin Service](#system-admin-service)

---

## API Service Setup

### Location: `src/services/api.js`

The API service configures axios with:
- Base URL detection (development vs production)
- Automatic token injection from localStorage
- Response error handling (401 redirects to login)
- CORS support

**Example Usage:**
```javascript
import api from './api';

// GET request
const response = await api.get('/endpoint', { params: { key: 'value' } });

// POST request
const response = await api.post('/endpoint', { data: 'value' });
```

---

## Authentication Service

### Location: `src/services/authService.js`

### `checkBackendHealth()`
Check backend connectivity before login.

**Endpoint:** `GET /api/v1/health`

**Returns:**
```javascript
{
  reachable: true | false,
  status: 'ok' | 'degraded',
  error: 'string (if unreachable)'
}
```

**Example:**
```javascript
import { authService } from './services/authService';

const health = await authService.checkBackendHealth();
if (!health.reachable) {
  console.error('Backend is not reachable');
}
```

---

### `login(username, password)`
Authenticate user and store token.

**Endpoint:** `POST /api/v1/auth/login`

**Parameters:**
- `username`: String (required)
- `password`: String (required)

**Returns:**
```javascript
{
  success: true | false,
  user: {
    userID: 1,
    username: 'string',
    role: 'string',
    full_name: 'string',
    tenantID: 1
  },
  tenant: { /* tenant object */ },
  error: 'string (if failed)'
}
```

**Example:**
```javascript
const result = await authService.login('username', 'password');
if (result.success) {
  // Token stored in localStorage automatically
  // User data stored in localStorage as 'auth'
  console.log('Logged in as:', result.user.username);
} else {
  console.error('Login failed:', result.error);
}
```

**Side Effects:**
- Stores `token` and `access_token` in localStorage
- Stores auth data in localStorage as `auth`
- Handles network errors and 401 responses

---

### `logout()`
Logout user and clear tokens.

**Endpoint:** `POST /api/v1/auth/logout`

**Returns:** Promise (void)

**Example:**
```javascript
await authService.logout();
// Tokens and auth data cleared from localStorage
```

**Side Effects:**
- Removes `token`, `access_token`, and `auth` from localStorage
- Handles errors gracefully (clears tokens even if API call fails)

---

### `getCurrentUser()`
Get current authenticated user information.

**Endpoint:** `GET /api/v1/auth/me`

**Returns:**
```javascript
{
  success: true,
  user: {
    userID: 1,
    username: 'string',
    role: 'string',
    email: 'string',
    full_name: 'string',
    tenantID: 1
  },
  tenant: { /* tenant object */ }
}
```

**Example:**
```javascript
try {
  const result = await authService.getCurrentUser();
  if (result.success) {
    console.log('Current user:', result.user);
  }
} catch (error) {
  // Handles 401 by throwing error (AuthContext will handle logout)
  if (error.response?.status === 401) {
    // User will be logged out
  }
}
```

**Error Handling:**
- Throws error if 401 (AuthContext will handle logout)
- Logs errors to console

---

## User Service

### Location: `src/services/userService.js`

### `getAll(page, perPage, filters)`
Get all users for current tenant.

**Endpoint:** `GET /api/v1/users/`

**Parameters:**
- `page`: Number (default: 1)
- `perPage`: Number (default: 20)
- `filters`: Object with optional filters (role, status)

**Returns:**
```javascript
{
  success: true,
  data: [ /* user objects */ ],
  pagination: {
    page: 1,
    per_page: 20,
    total: 100,
    pages: 5,
    has_next: true,
    has_prev: false
  }
}
```

**Example:**
```javascript
import { userService } from './services/userService';

const result = await userService.getAll(1, 20, { role: 'employee' });
console.log('Users:', result.data);
console.log('Total pages:', result.pagination.pages);
```

---

### `getById(id)`
Get specific user by ID.

**Endpoint:** `GET /api/v1/users/<id>`

**Parameters:**
- `id`: Number (user ID)

**Returns:**
```javascript
{
  success: true,
  data: { /* user object */ }
}
```

**Example:**
```javascript
const user = await userService.getById(1);
console.log('User:', user.data);
```

---

### `create(data)`
Create a new user (admin only).

**Endpoint:** `POST /api/v1/users`

**Parameters:**
- `data`: Object
  ```javascript
  {
    username: 'string (required)',
    password: 'string (required)',
    role: 'string (required)',
    email: 'string (optional)',
    full_name: 'string (optional)',
    status: 'active' (optional)
  }
  ```

**Returns:**
```javascript
{
  success: true,
  message: 'User created successfully',
  data: { /* user object */ }
}
```

**Example:**
```javascript
const newUser = await userService.create({
  username: 'newuser',
  password: 'password123',
  role: 'employee',
  email: 'user@example.com'
});
```

---

### `update(id, data)`
Update user information.

**Endpoint:** `PUT /api/v1/users/<id>`

**Parameters:**
- `id`: Number (user ID)
- `data`: Object with fields to update

**Returns:**
```javascript
{
  success: true,
  message: 'User updated successfully',
  data: { /* updated user object */ }
}
```

**Example:**
```javascript
await userService.update(1, {
  email: 'newemail@example.com',
  full_name: 'New Name'
});
```

---

### `delete(id)`
Delete user (soft delete - admin only).

**Endpoint:** `DELETE /api/v1/users/<id>`

**Parameters:**
- `id`: Number (user ID)

**Returns:**
```javascript
{
  success: true,
  message: 'User deactivated successfully'
}
```

**Example:**
```javascript
await userService.delete(1);
```

---

### `updateRole(id, role)`
Update user role.

**Endpoint:** `PUT /api/v1/users/<id>/role`

**Parameters:**
- `id`: Number (user ID)
- `role`: String (new role)

**Returns:**
```javascript
{
  success: true,
  message: 'Role updated successfully'
}
```

**Note:** This endpoint may not be implemented in backend - verify before use.

---

### `getPermissions(id)`
Get user permissions.

**Endpoint:** `GET /api/v1/users/<id>/permissions`

**Note:** This endpoint may not be implemented in backend - verify before use.

---

### `updatePermissions(id, data)`
Update user permissions.

**Endpoint:** `PUT /api/v1/users/<id>/permissions`

**Note:** This endpoint may not be implemented in backend - verify before use.

---

## Department Service

### Location: `src/services/departmentService.js`

### `getAll(page, perPage, filters)`
Get all departments for current tenant.

**Endpoint:** `GET /api/v1/departments/`

**Parameters:**
- `page`: Number (default: 1)
- `perPage`: Number (default: 20)
- `filters`: Object with optional filters

**Returns:**
```javascript
{
  success: true,
  data: [
    {
      departmentID: 1,
      departmentName: 'string',
      description: 'string',
      is_active: true,
      tenantID: 1
    }
  ],
  pagination: { /* pagination object */ }
}
```

**Example:**
```javascript
import { departmentService } from './services/departmentService';

const result = await departmentService.getAll(1, 20);
console.log('Departments:', result.data);
```

---

### `getById(id)`
Get specific department by ID.

**Endpoint:** `GET /api/v1/departments/<id>`

**Returns:**
```javascript
{
  success: true,
  data: { /* department object */ }
}
```

---

### `create(data)`
Create a new department.

**Endpoint:** `POST /api/v1/departments`

**Parameters:**
- `data`: Object
  ```javascript
  {
    departmentName: 'string (required)',
    description: 'string (optional)',
    is_active: true (optional)
  }
  ```

**Returns:**
```javascript
{
  success: true,
  message: 'Department created successfully',
  data: { /* department object */ }
}
```

---

### `update(id, data)`
Update department information.

**Endpoint:** `PUT /api/v1/departments/<id>`

**Returns:**
```javascript
{
  success: true,
  message: 'Department updated successfully',
  data: { /* department object */ }
}
```

---

### `delete(id)`
Delete department (soft delete).

**Endpoint:** `DELETE /api/v1/departments/<id>`

**Returns:**
```javascript
{
  success: true,
  message: 'Department deactivated successfully'
}
```

---

## Tenant Service

### Location: `src/services/tenantService.js`

### `getAll(page, perPage)`
Get all tenants (admin only).

**Endpoint:** `GET /api/v1/tenants/`

**Parameters:**
- `page`: Number (default: 1)
- `perPage`: Number (default: 20)

**Returns:**
```javascript
{
  success: true,
  data: [ /* tenant objects */ ],
  pagination: { /* pagination object */ }
}
```

---

### `getById(id)`
Get specific tenant by ID.

**Endpoint:** `GET /api/v1/tenants/<id>`

**Returns:**
```javascript
{
  success: true,
  data: { /* tenant object */ }
}
```

---

### `create(data)`
Create a new tenant (admin only).

**Endpoint:** `POST /api/v1/tenants`

**Parameters:**
- `data`: Object
  ```javascript
  {
    tenantName: 'string (required)',
    is_active: true (optional)
  }
  ```

---

### `update(id, data)`
Update tenant information (admin only).

**Endpoint:** `PUT /api/v1/tenants/<id>`

---

### `delete(id)`
Delete tenant (soft delete - admin only).

**Endpoint:** `DELETE /api/v1/tenants/<id>`

---

### `getStats(id)`
Get tenant statistics.

**Endpoint:** `GET /api/v1/tenants/<id>/stats`

**Returns:**
```javascript
{
  success: true,
  data: {
    tenant: { /* tenant object */ },
    users: {
      total: 10,
      active: 8,
      by_role: { /* role counts */ }
    },
    departments: {
      total: 5,
      active: 4
    },
    schedule_definitions: {
      total: 3,
      active: 2
    },
    recent_jobs: 5
  }
}
```

---

## Schedule Service

### Location: `src/services/scheduleService.js`

### `getDefinitions(page, perPage, filters)`
Get schedule definitions.

**Endpoint:** `GET /api/v1/schedule-definitions/`

**Parameters:**
- `page`: Number (default: 1)
- `perPage`: Number (default: 20)
- `filters`: Object with optional filters (department_id, active)

**Returns:**
```javascript
{
  page: 1,
  per_page: 20,
  total: 10,
  items: [ /* schedule definition objects */ ]
}
```

**Example:**
```javascript
import { scheduleService } from './services/scheduleService';

const result = await scheduleService.getDefinitions(1, 20, { active: true });
console.log('Definitions:', result.items);
```

---

### `getDefinitionById(id)`
Get specific schedule definition by ID.

**Endpoint:** `GET /api/v1/schedule-definitions/<id>`

**Returns:**
```javascript
{
  success: true,
  data: { /* schedule definition object */ }
}
```

---

### `createDefinition(data)`
Create a new schedule definition.

**Endpoint:** `POST /api/v1/schedule-definitions`

**Parameters:**
- `data`: Object with schedule definition fields

---

### `updateDefinition(id, data)`
Update schedule definition.

**Endpoint:** `PUT /api/v1/schedule-definitions/<id>`

---

### `deleteDefinition(id)`
Delete schedule definition (soft delete).

**Endpoint:** `DELETE /api/v1/schedule-definitions/<id>`

---

### `getPermissions(page, perPage, filters)`
Get schedule permissions.

**Endpoint:** `GET /api/v1/schedule-permissions/`

**Parameters:**
- `page`: Number (default: 1)
- `perPage`: Number (default: 20)
- `filters`: Object with optional filters

**Returns:**
```javascript
{
  success: true,
  data: [ /* permission objects */ ],
  pagination: { /* pagination object */ }
}
```

---

### `createPermission(data)`
Create a new schedule permission.

**Endpoint:** `POST /api/v1/schedule-permissions`

---

### `updatePermission(id, data)`
Update schedule permission.

**Endpoint:** `PUT /api/v1/schedule-permissions/<id>`

---

### `getJobLogs(page, perPage, filters)`
Get schedule job logs.

**Endpoint:** `GET /api/v1/schedule-job-logs/`

**Parameters:**
- `page`: Number (default: 1)
- `perPage`: Number (default: 50)
- `filters`: Object with optional filters
  ```javascript
  {
    user_id: 1,
    schedule_def_id: 1,
    status: 'completed',
    date_from: '2025-01-01',
    date_to: '2025-01-31'
  }
  ```

**Returns:**
```javascript
{
  data: [ /* job log objects */ ],
  pagination: { /* pagination object */ }
}
```

**Example:**
```javascript
const logs = await scheduleService.getJobLogs(1, 50, {
  schedule_def_id: 1,
  status: 'completed'
});
console.log('Job logs:', logs.data);
```

---

### `runJob(data)`
Run a schedule job.

**Endpoint:** `POST /api/v1/schedule-job-logs/run`

**Parameters:**
- `data`: Object
  ```javascript
  {
    scheduleDefID: 1 (required),
    parameters: { /* optional */ },
    priority: 'normal' (optional)
  }
  ```

**Returns:**
```javascript
{
  success: true,
  message: 'Schedule job started successfully',
  data: { /* job log object */ },
  celery_task_id: 'string (optional)'
}
```

**Example:**
```javascript
const result = await scheduleService.runJob({
  scheduleDefID: 1,
  priority: 'high'
});
console.log('Job started:', result.data.logID);
```

---

### `getJobLogById(id)`
Get specific job log by ID.

**Endpoint:** `GET /api/v1/schedule-job-logs/<id>`

**Returns:**
```javascript
{
  success: true,
  data: { /* job log object */ }
}
```

---

### `cancelJob(id, reason)`
Cancel a running schedule job.

**Endpoint:** `POST /api/v1/schedule-job-logs/<id>/cancel`

**Parameters:**
- `id`: Number (job log ID)
- `reason`: String (optional cancellation reason)

**Returns:**
```javascript
{
  success: true,
  message: 'Schedule job cancelled successfully',
  data: { /* job log object */ }
}
```

---

### `getD1Data(scheduleDefId)`
Get D1 Scheduling Dashboard data.

**Endpoint:** `GET /api/v1/schedulemanager/d1-scheduling`

**Parameters:**
- `scheduleDefId`: Number (optional)

**Returns:**
```javascript
{
  success: true,
  data: { /* dashboard data */ }
}
```

---

### `getJobStatus(scheduleDefId)`
Get latest job status for a schedule.

**Endpoint:** `GET /api/v1/schedule-job-logs`

**Parameters:**
- `scheduleDefId`: Number (schedule definition ID)

**Returns:**
```javascript
{
  success: true,
  data: [ /* job log objects */ ],
  pagination: { /* pagination object */ }
}
```

---

### `exportJobLog(logId)`
Export schedule results as CSV.

**Endpoint:** `GET /api/v1/schedule-job-logs/<logId>/export`

**Parameters:**
- `logId`: Number (job log ID)

**Returns:** Blob (CSV file)

**Example:**
```javascript
const blob = await scheduleService.exportJobLog(1);
// Create download link
const url = window.URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = 'schedule_export.csv';
a.click();
```

---

## Employee Service

### Location: `src/services/employeeService.js`

### `getMySchedule(month)`
Get schedule for current employee from database cache.

**Endpoint:** `GET /api/v1/employee/schedule`

**Parameters:**
- `month`: String in YYYY-MM format (optional)

**Returns:**
```javascript
{
  success: true,
  user_id: 1,
  month: '2025-11',
  schedule: [
    {
      date: '2025-11-01',
      shift_type: 'D',
      shiftType: 'D',
      time_range: '08:00 - 17:00',
      timeRange: '08:00 - 17:00'
    }
  ],
  source: 'database',
  last_synced_at: 'ISO datetime',
  cache_count: 30
}
```

**Example:**
```javascript
import { employeeService } from './services/employeeService';

const schedule = await employeeService.getMySchedule('2025-11');
console.log('Schedule entries:', schedule.schedule.length);
```

---

### `getScheduleData(scheduleDefId)`
Get employee schedule data (cache first, fallback to Google Sheets).

**Endpoint:** `GET /api/v1/employee/schedule-data`

**Parameters:**
- `scheduleDefId`: Number (optional)

**Returns:**
```javascript
{
  success: true,
  source: 'database_cache' | 'google_sheets',
  data: {
    my_schedule: {
      rows: [
        {
          '日期': '2025-11-01',
          '星期': '週一',
          '班別': 'D',
          '時段': '08:00 - 17:00'
        }
      ],
      columns: ['日期', '星期', '班別', '時段']
    }
  },
  last_synced_at: 'ISO datetime (optional)'
}
```

---

### `getSchedule(month)`
Get employee schedule (alternative endpoint with trace logging).

**Endpoint:** `GET /api/v1/schedule/`

**Parameters:**
- `month`: String in YYYY-MM format (optional)

**Returns:**
```javascript
{
  success: true,
  user_id: 1,
  employee: 'EMP-1',
  month: '2025-11',
  schedule: [ /* schedule entries */ ],
  metadata: {
    total_rows: 100,
    total_entries: 30,
    month_pattern: '2025/11/',
    fallback_used: false
  }
}
```

**Example:**
```javascript
const schedule = await employeeService.getSchedule('2025-11');
if (schedule.success) {
  console.log('Schedule loaded:', schedule.schedule.length, 'entries');
} else {
  console.error('Error:', schedule.error);
}
```

**Note:** This method includes extensive trace logging for debugging.

---

### `submitLeaveRequest(data)`
Submit a leave request (may not be implemented).

**Endpoint:** `POST /api/v1/employee/requests/leave`

**Note:** Verify endpoint exists before use.

---

## Client Admin Service

### Location: `src/services/clientadminService.js`

### `getOverview()`
Get Client Admin dashboard overview.

**Endpoint:** `GET /api/v1/clientadmin/dashboard`

**Returns:**
```javascript
{
  success: true,
  dashboard: 'clientadmin',
  user: { /* user object */ },
  tenant: { /* tenant object */ },
  stats: {
    tenants: 1,
    departments: 5,
    users: 20,
    active_users: 18
  },
  views: ['C1: Tenant', 'C2: Department', 'C3: User Account', 'C4: Permissions']
}
```

**Example:**
```javascript
import { clientadminService } from './services/clientadminService';

const overview = await clientadminService.getOverview();
console.log('Departments:', overview.stats.departments);
```

---

## Schedule Manager Service

### Location: `src/services/scheduleManagerService.js`

### `getSchedules()`
Get schedules (legacy endpoint).

**Endpoint:** `GET /api/v1/schedule`

**Note:** This may redirect to schedule-user-tasks endpoint.

---

### `generateSchedule(data)`
Generate schedule (may not be implemented).

**Endpoint:** `POST /api/v1/schedule/generate`

**Note:** Verify endpoint exists before use.

---

### `getJobLogs(page, perPage)`
Get schedule job logs.

**Endpoint:** `GET /api/v1/schedule-job-logs`

**Parameters:**
- `page`: Number (default: 1)
- `perPage`: Number (default: 50)

**Returns:**
```javascript
{
  success: true,
  data: [ /* job log objects */ ],
  pagination: { /* pagination object */ }
}
```

---

## System Admin Service

### Location: `src/services/sysadminService.js`

### `getOverview()`
Get System Admin dashboard overview.

**Endpoint:** `GET /api/v1/sysadmin/dashboard`

**Returns:**
```javascript
{
  success: true,
  dashboard: 'sysadmin',
  user: { /* user object */ },
  stats: {
    total_tenants: 10,
    totalTenants: 10,
    active_tenants: 8,
    activeTenants: 8,
    total_schedules: 25,
    totalSchedules: 25,
    active_schedules: 20,
    activeSchedules: 20
  },
  views: ['B1: Organization', 'B2: Schedule List', 'B3: Schedule Maintenance']
}
```

**Example:**
```javascript
import { sysadminService } from './services/sysadminService';

const overview = await sysadminService.getOverview();
console.log('Total tenants:', overview.stats.total_tenants);
```

---

### `getStats()`
Get system statistics (same as getOverview but returns only stats).

**Endpoint:** `GET /api/v1/sysadmin/dashboard`

**Returns:** Same stats object as getOverview.

---

### `getLogs(page, perPage)`
Get system logs.

**Endpoint:** `GET /api/v1/sysadmin/logs`

**Parameters:**
- `page`: Number (default: 1)
- `perPage`: Number (default: 10)

**Returns:**
```javascript
{
  success: true,
  logs: [
    {
      id: 1,
      logID: 1,
      action: 'schedule_job_execution',
      timestamp: 'ISO datetime',
      details: {
        message: 'string',
        schedule_def_id: 1,
        status: 'completed'
      }
    }
  ],
  data: [ /* same as logs */ ]
}
```

**Example:**
```javascript
const logs = await sysadminService.getLogs(1, 10);
console.log('System logs:', logs.logs);
```

---

## Error Handling

All services use axios which automatically handles:
- Network errors
- HTTP errors (4xx, 5xx)
- 401 responses (redirect to login via api.js interceptor)

**Example Error Handling:**
```javascript
try {
  const result = await userService.getAll();
} catch (error) {
  if (error.response) {
    // HTTP error (4xx, 5xx)
    console.error('HTTP Error:', error.response.status);
    console.error('Error data:', error.response.data);
  } else if (error.request) {
    // Network error
    console.error('Network error:', error.message);
  } else {
    // Other error
    console.error('Error:', error.message);
  }
}
```

---

## Authentication Flow

1. **Login:**
   ```javascript
   const result = await authService.login(username, password);
   if (result.success) {
     // Token stored in localStorage
     // User data stored in localStorage
   }
   ```

2. **Get Current User:**
   ```javascript
   const user = await authService.getCurrentUser();
   // Returns user from token
   ```

3. **Logout:**
   ```javascript
   await authService.logout();
   // Clears all tokens and user data
   ```

---

## Best Practices

1. **Always handle errors:**
   ```javascript
   try {
     const result = await service.method();
   } catch (error) {
     // Handle error appropriately
   }
   ```

2. **Use pagination:**
   ```javascript
   const result = await service.getAll(page, perPage);
   // Check result.pagination for navigation
   ```

3. **Check response structure:**
   ```javascript
   if (result.success) {
     // Process data
   } else {
     // Handle error
   }
   ```

4. **Handle loading states:**
   ```javascript
   const [loading, setLoading] = useState(false);
   const [data, setData] = useState(null);
   
   useEffect(() => {
     setLoading(true);
     service.getAll()
       .then(result => setData(result))
       .finally(() => setLoading(false));
   }, []);
   ```

---

## Notes

1. **Token Management:** Tokens are automatically managed by `api.js`. No need to manually add tokens to requests.

2. **CORS:** All endpoints support CORS. The frontend is configured for development on `localhost:5174` and `localhost:5173`.

3. **Base URL:** Automatically detects development vs production environment.

4. **Error Responses:** Most services return error objects in the response rather than throwing errors. Check `success` field.

5. **Pagination:** List endpoints return pagination metadata. Use this for building pagination UI.

6. **Response Formats:** Some endpoints return different structures. Always check the response structure before accessing nested properties.

