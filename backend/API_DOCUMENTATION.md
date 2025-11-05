# Backend API Documentation

This document provides detailed documentation for all backend API endpoints.

**Base URL**: `/api/v1`

**Authentication**: Most endpoints require JWT authentication via `Authorization: Bearer <token>` header.

---

## Table of Contents

- [Authentication Endpoints](#authentication-endpoints)
- [Common Endpoints](#common-endpoints)
- [User Management](#user-management)
- [Department Management](#department-management)
- [Tenant Management](#tenant-management)
- [Schedule Definitions](#schedule-definitions)
- [Schedule Job Logs](#schedule-job-logs)
- [Schedule Permissions](#schedule-permissions)
- [Schedule Endpoints](#schedule-endpoints)
- [Employee Endpoints](#employee-endpoints)
- [Google Sheets Endpoints](#google-sheets-endpoints)
- [Client Admin Endpoints](#client-admin-endpoints)
- [Schedule Manager Endpoints](#schedule-manager-endpoints)
- [System Admin Endpoints](#system-admin-endpoints)
- [Analytics Endpoints](#analytics-endpoints)
- [Dashboard Endpoints](#dashboard-endpoints)
- [Data Endpoints](#data-endpoints)

---

## Authentication Endpoints

### POST /api/v1/auth/login
Authenticate user and return access token.

**Request Body:**
```json
{
  "username": "string (required)",
  "password": "string (required)"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Login successful",
  "access_token": "JWT token string",
  "user": {
    "userID": 1,
    "username": "string",
    "role": "string",
    "email": "string",
    "full_name": "string",
    "tenantID": 1
  },
  "tenant": {
    "tenantID": 1,
    "tenantName": "string",
    "is_active": true
  }
}
```

**Error Responses:**
- `400`: Invalid login data
- `401`: Invalid credentials or inactive account

---

### POST /api/v1/auth/register
Register a new user.

**Request Body:**
```json
{
  "username": "string (required)",
  "password": "string (required)",
  "email": "string (optional)",
  "role": "string (optional, default: 'employee')",
  "full_name": "string (optional)",
  "tenant_id": "integer (optional)"
}
```

**Alternative Format (with tenant):**
```json
{
  "tenant": {
    "tenantName": "string"
  },
  "user": {
    "username": "string",
    "password": "string",
    "email": "string",
    "role": "string"
  }
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "User registered successfully",
  "access_token": "JWT token string",
  "user": { /* user object */ },
  "tenant": { /* tenant object */ }
}
```

**Error Responses:**
- `400`: Invalid data or missing required fields
- `409`: Username or email already exists

---

### GET /api/v1/auth/register
Get registration information (helpful message).

**Response (200):**
```json
{
  "message": "Use POST to register a new user at this endpoint.",
  "example_body": { /* example */ },
  "note": "You can also send {...} to create a tenant and user together."
}
```

---

### GET /api/v1/auth/me
Get current authenticated user information.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "user": {
    "userID": 1,
    "username": "string",
    "role": "string",
    "email": "string",
    "full_name": "string",
    "tenantID": 1,
    "status": "active"
  },
  "tenant": { /* tenant object */ }
}
```

**Error Responses:**
- `401`: Authentication required
- `404`: User not found
- `401`: Account is inactive

---

### POST /api/v1/auth/logout
Logout user by blacklisting the current token.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "message": "Logout successful"
}
```

---

### POST /api/v1/auth/change-password
Change user password.

**Authentication:** Required

**Request Body:**
```json
{
  "current_password": "string (required)",
  "new_password": "string (required)"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Password changed successfully"
}
```

**Error Responses:**
- `400`: Current password and new password are required, or password validation failed
- `401`: Current password is incorrect
- `404`: User not found

---

### POST /api/v1/auth/refresh
Refresh access token.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "access_token": "new JWT token string"
}
```

**Error Responses:**
- `401`: User not found or inactive

---

## Common Endpoints

### GET /api/v1/health
Health check endpoint.

**Response (200):**
```json
{
  "status": "ok" | "degraded",
  "components": {
    "flask": true,
    "redis": true | false,
    "celery": true | false
  }
}
```

---

### GET /api/v1/routes
List all registered routes (useful for debugging).

**Response (200):**
```json
{
  "count": 108,
  "routes": [
    {
      "endpoint": "string",
      "rule": "string",
      "methods": "string"
    }
  ]
}
```

---

### GET /api/v1/login
Redirect to `/api/v1/auth/login` (301 redirect).

---

### GET /api/v1/dashboard
Unified dashboard endpoint that routes to role-specific dashboard.

**Authentication:** Required

**Response:** Redirects to role-specific dashboard:
- `Client_Admin` → `/api/v1/clientadmin/dashboard`
- `SysAdmin` → `/api/v1/sysadmin/dashboard`
- `Schedule_Manager` → `/api/v1/schedulemanager/dashboard`
- `Department_Employee` → `/api/v1/employee/schedule`

---

### GET /api/v1/dashboard/stats
Dashboard statistics for current user.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "data": {
    "total_jobs": 0,
    "active_schedules": 0,
    "recent_activity": 0
  }
}
```

---

### GET /api/v1/dashboard/activities
Recent activities for dashboard.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "type": "schedule_run",
      "description": "Schedule job status",
      "timestamp": "ISO datetime string"
    }
  ]
}
```

---

### GET /api/v1/dashboard/notifications
Dashboard notifications.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "data": []
}
```

---

### GET /api/v1/dashboard/chart-data
Chart data for dashboard.

**Authentication:** Required

**Query Parameters:**
- `type`: Chart type (default: "performance")

**Response (200):**
```json
{
  "success": true,
  "type": "performance",
  "data": []
}
```

---

### GET /api/v1/dashboard/system-health
System health check endpoint.

**Authentication:** Required

**Response (200):**
```json
{
  "status": "ok" | "degraded",
  "components": {
    "flask": true,
    "database": true,
    "redis": true | false,
    "celery": true | false
  }
}
```

---

### GET /api/v1/dashboard/schedule-data
Dashboard schedule data endpoint (for employees).

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "data": {
    "user_id": 1,
    "schedule": []
  }
}
```

---

### POST /api/v1/admin/sync
Manual sync trigger for Google Sheets to database.

**Authentication:** Required

**Request Body:**
```json
{
  "schedule_def_id": "integer (optional)",
  "force": "boolean (optional, default: false)"
}
```

**Response (200):**
```json
{
  "success": true,
  "schedules": [
    {
      "schedule_def_id": 1,
      "schedule_name": "string",
      "success": true,
      "rows_synced": 100,
      "users_synced": 10
    }
  ],
  "total_synced": 1
}
```

---

### GET /api/v1/admin/sync/status
Get sync status for schedule definitions.

**Authentication:** Required

**Query Parameters:**
- `schedule_def_id`: Schedule definition ID (optional)

**Response (200):**
```json
{
  "success": true,
  "last_synced_at": "ISO datetime string",
  "status": "completed" | "never_synced",
  "rows_synced": 0,
  "users_synced": 0,
  "duration_seconds": 0
}
```

---

### GET /api/v1/system/health
System health check endpoint (no auth required for monitoring).

**Response (200):**
```json
{
  "status": "ok" | "degraded",
  "components": {
    "flask": true,
    "database": true,
    "mysql": true | false,
    "redis": true | false,
    "celery": true | false
  }
}
```

---

## User Management

### GET /api/v1/users
Get users for current tenant.

**Authentication:** Required

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)
- `role`: Filter by role (optional)
- `status`: Filter by status (optional)

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "userID": 1,
      "username": "string",
      "role": "string",
      "email": "string",
      "full_name": "string",
      "status": "active",
      "tenantID": 1
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

---

### POST /api/v1/users
Create a new user (admin only).

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "username": "string (required)",
  "password": "string (required)",
  "role": "string (required)",
  "email": "string (optional)",
  "full_name": "string (optional)",
  "status": "active (optional, default: 'active')"
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "User created successfully",
  "data": { /* user object */ }
}
```

**Error Responses:**
- `400`: Invalid user data
- `403`: Admin access required
- `409`: Username already exists

---

### GET /api/v1/users/<user_id>
Get specific user information.

**Authentication:** Required (Admin or self)

**Response (200):**
```json
{
  "success": true,
  "data": { /* user object */ }
}
```

**Error Responses:**
- `403`: Access denied
- `404`: User not found

---

### PUT /api/v1/users/<user_id>
Update user information.

**Authentication:** Required (Admin or self)

**Request Body:**
```json
{
  "username": "string (optional)",
  "role": "string (optional, admin only)",
  "status": "string (optional, admin only)",
  "email": "string (optional)",
  "full_name": "string (optional)"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "User updated successfully",
  "data": { /* user object */ }
}
```

---

### DELETE /api/v1/users/<user_id>
Delete user (soft delete - admin only).

**Authentication:** Required (Admin)

**Response (200):**
```json
{
  "success": true,
  "message": "User deactivated successfully"
}
```

---

## Department Management

### GET /api/v1/departments
Get departments for current tenant (or all for SysAdmin).

**Authentication:** Required

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)
- `active`: Filter by active status (optional)

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "departmentID": 1,
      "departmentName": "string",
      "description": "string",
      "is_active": true,
      "tenantID": 1
    }
  ],
  "pagination": { /* pagination object */ }
}
```

---

### POST /api/v1/departments
Create a new department.

**Authentication:** Required (Admin or Scheduler)

**Request Body:**
```json
{
  "departmentName": "string (required)",
  "description": "string (optional)",
  "is_active": "boolean (optional, default: true)"
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "Department created successfully",
  "data": { /* department object */ }
}
```

**Error Responses:**
- `400`: Invalid department data
- `403`: Admin or scheduler access required
- `409`: Department with this name already exists

---

### GET /api/v1/departments/<department_id>
Get specific department information.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "data": { /* department object */ }
}
```

---

### PUT /api/v1/departments/<department_id>
Update department information.

**Authentication:** Required (Admin or Scheduler)

**Request Body:**
```json
{
  "departmentName": "string (optional)",
  "description": "string (optional)",
  "is_active": "boolean (optional)"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Department updated successfully",
  "data": { /* department object */ }
}
```

---

### DELETE /api/v1/departments/<department_id>
Delete department (soft delete).

**Authentication:** Required (Admin or Scheduler)

**Response (200):**
```json
{
  "success": true,
  "message": "Department deactivated successfully"
}
```

---

## Tenant Management

### GET /api/v1/tenants
Get all tenants (admin only).

**Authentication:** Required (Admin)

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "tenantID": 1,
      "tenantName": "string",
      "is_active": true,
      "created_at": "ISO datetime",
      "updated_at": "ISO datetime"
    }
  ],
  "pagination": { /* pagination object */ }
}
```

---

### POST /api/v1/tenants
Create a new tenant (admin only).

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "tenantName": "string (required)",
  "is_active": "boolean (optional, default: true)"
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "Tenant created successfully",
  "data": { /* tenant object */ }
}
```

---

### GET /api/v1/tenants/<tenant_id>
Get specific tenant information.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "data": { /* tenant object */ }
}
```

---

### PUT /api/v1/tenants/<tenant_id>
Update tenant information (admin only).

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "tenantName": "string (optional)",
  "is_active": "boolean (optional)"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Tenant updated successfully",
  "data": { /* tenant object */ }
}
```

---

### DELETE /api/v1/tenants/<tenant_id>
Delete tenant (soft delete - admin only).

**Authentication:** Required (Admin)

**Response (200):**
```json
{
  "success": true,
  "message": "Tenant deactivated successfully"
}
```

---

### GET /api/v1/tenants/<tenant_id>/stats
Get tenant statistics.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "data": {
    "tenant": { /* tenant object */ },
    "users": {
      "total": 10,
      "active": 8,
      "by_role": { "role": "count" }
    },
    "departments": {
      "total": 5,
      "active": 4
    },
    "schedule_definitions": {
      "total": 3,
      "active": 2
    },
    "recent_jobs": 5
  }
}
```

---

### GET /api/v1/tenants/<tenant_id>/users
Get all users for a specific tenant.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "data": [ /* user objects */ ]
}
```

---

## Schedule Definitions

### GET /api/v1/schedule-definitions
Get schedule definitions for current tenant (or all for SysAdmin).

**Authentication:** Required

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)
- `department_id`: Filter by department (optional)
- `active`: Filter by active status (optional)

**Response (200):**
```json
{
  "page": 1,
  "per_page": 20,
  "total": 10,
  "items": [
    {
      "scheduleDefID": 1,
      "scheduleName": "string",
      "departmentID": 1,
      "paramsSheetURL": "string",
      "prefsSheetURL": "string",
      "resultsSheetURL": "string",
      "schedulingAPI": "string",
      "remarks": "string",
      "is_active": true,
      "tenantID": 1
    }
  ]
}
```

---

### POST /api/v1/schedule-definitions
Create a new schedule definition.

**Authentication:** Required (Admin or Scheduler)

**Request Body:**
```json
{
  "scheduleName": "string (required)",
  "departmentID": "integer (required)",
  "paramsSheetURL": "string (required)",
  "prefsSheetURL": "string (required)",
  "resultsSheetURL": "string (required)",
  "schedulingAPI": "string (required)",
  "remarks": "string (optional)",
  "is_active": "boolean (optional, default: true)"
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "Schedule definition created successfully",
  "data": { /* schedule definition object */ }
}
```

---

### GET /api/v1/schedule-definitions/<definition_id>
Get specific schedule definition information.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "data": { /* schedule definition object */ }
}
```

---

### PUT /api/v1/schedule-definitions/<definition_id>
Update schedule definition information.

**Authentication:** Required (Admin or Scheduler)

**Request Body:**
```json
{
  "scheduleName": "string (optional)",
  "departmentID": "integer (optional)",
  "paramsSheetURL": "string (optional)",
  "prefsSheetURL": "string (optional)",
  "resultsSheetURL": "string (optional)",
  "schedulingAPI": "string (optional)",
  "remarks": "string (optional)",
  "is_active": "boolean (optional)"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Schedule definition updated successfully",
  "data": { /* schedule definition object */ }
}
```

---

### DELETE /api/v1/schedule-definitions/<definition_id>
Delete schedule definition (soft delete).

**Authentication:** Required (Admin or Scheduler)

**Response (200):**
```json
{
  "success": true,
  "message": "Schedule definition deactivated successfully"
}
```

---

## Schedule Job Logs

### GET /api/v1/schedule-job-logs
Get schedule job logs for current tenant.

**Authentication:** Required

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)
- `user_id`: Filter by user (optional)
- `schedule_def_id`: Filter by schedule definition (optional)
- `status`: Filter by status (optional)
- `date_from`: Filter from date (ISO format, optional)
- `date_to`: Filter to date (ISO format, optional)

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "logID": 1,
      "scheduleDefID": 1,
      "runByUserID": 1,
      "startTime": "ISO datetime",
      "endTime": "ISO datetime",
      "status": "pending" | "running" | "completed" | "failed" | "cancelled",
      "resultSummary": "string",
      "error_message": "string",
      "metadata": {}
    }
  ],
  "pagination": { /* pagination object */ }
}
```

---

### POST /api/v1/schedule-job-logs
Create a new schedule job log.

**Authentication:** Required (Admin or Scheduler)

**Request Body:**
```json
{
  "scheduleDefID": "integer (required)",
  "runByUserID": "integer (required)",
  "startTime": "ISO datetime (optional)",
  "status": "string (optional, default: 'pending')",
  "metadata": "object (optional)"
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "Schedule job log created successfully",
  "data": { /* job log object */ }
}
```

---

### POST /api/v1/schedule-job-logs/run
Run a schedule job.

**Authentication:** Required

**Request Body:**
```json
{
  "scheduleDefID": "integer (required)",
  "parameters": "object (optional)",
  "priority": "string (optional, default: 'normal')"
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "Schedule job started successfully",
  "data": { /* job log object */ },
  "celery_task_id": "string (optional)"
}
```

---

### GET /api/v1/schedule-job-logs/<log_id>
Get specific schedule job log information.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "data": { /* job log object */ }
}
```

---

### PUT /api/v1/schedule-job-logs/<log_id>
Update schedule job log information.

**Authentication:** Required (Admin or Scheduler)

**Request Body:**
```json
{
  "endTime": "ISO datetime (optional)",
  "status": "string (optional)",
  "resultSummary": "string (optional)",
  "error_message": "string (optional)",
  "metadata": "object (optional)"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Schedule job log updated successfully",
  "data": { /* job log object */ }
}
```

---

### POST /api/v1/schedule-job-logs/<log_id>/cancel
Cancel a running schedule job.

**Authentication:** Required

**Request Body:**
```json
{
  "reason": "string (optional)"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Schedule job cancelled successfully",
  "data": { /* job log object */ }
}
```

---

### GET /api/v1/schedule-job-logs/<log_id>/export
Export schedule results for a completed job as CSV.

**Authentication:** Required

**Response (200):** CSV file download

**Error Responses:**
- `400`: Job is not completed yet
- `404`: Job log or schedule data not found

---

## Schedule Permissions

### GET /api/v1/schedule-permissions
Get schedule permissions for current tenant.

**Authentication:** Required

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)
- `user_id`: Filter by user (optional)
- `schedule_def_id`: Filter by schedule definition (optional)
- `active`: Filter by active status (optional)

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "permissionID": 1,
      "userID": 1,
      "scheduleDefID": 1,
      "canRunJob": true,
      "granted_by": 1,
      "expires_at": "ISO datetime",
      "is_active": true,
      "tenantID": 1
    }
  ],
  "pagination": { /* pagination object */ }
}
```

---

### POST /api/v1/schedule-permissions
Create a new schedule permission.

**Authentication:** Required (Admin or Scheduler)

**Request Body:**
```json
{
  "userID": "integer (required)",
  "scheduleDefID": "integer (required)",
  "canRunJob": "boolean (required)",
  "expires_at": "ISO datetime (optional)",
  "is_active": "boolean (optional, default: true)"
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "Schedule permission created successfully",
  "data": { /* permission object */ }
}
```

---

### GET /api/v1/schedule-permissions/<permission_id>
Get specific schedule permission information.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "data": { /* permission object */ }
}
```

---

### PUT /api/v1/schedule-permissions/<permission_id>
Update schedule permission information.

**Authentication:** Required (Admin or Scheduler)

**Request Body:**
```json
{
  "canRunJob": "boolean (optional)",
  "expires_at": "ISO datetime (optional)",
  "is_active": "boolean (optional)"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Schedule permission updated successfully",
  "data": { /* permission object */ }
}
```

---

### DELETE /api/v1/schedule-permissions/<permission_id>
Delete schedule permission.

**Authentication:** Required (Admin or Scheduler)

**Response (200):**
```json
{
  "success": true,
  "message": "Schedule permission deleted successfully"
}
```

---

## Schedule Endpoints

### GET /api/v1/schedule/
Get employee schedule from database cache or job logs.

**Authentication:** Required

**Query Parameters:**
- `month`: Month in YYYY-MM format (optional)

**Response (200):**
```json
{
  "success": true,
  "month": "2025-11",
  "schedule": [
    {
      "date": "2025-11-01",
      "shift_type": "D",
      "shiftType": "D",
      "time_range": "08:00 - 17:00",
      "timeRange": "08:00 - 17:00"
    }
  ],
  "source": "database",
  "last_synced_at": "ISO datetime",
  "cache_empty": false
}
```

**Note:** If no month parameter is provided, returns job logs (backward compatibility).

---

## Employee Endpoints

### GET /api/v1/employee/schedule
Get schedule for current employee from database cache.

**Authentication:** Required

**Query Parameters:**
- `month`: Month in YYYY-MM format (optional)

**Response (200):**
```json
{
  "success": true,
  "user_id": 1,
  "month": "2025-11",
  "schedule": [
    {
      "date": "ISO date string",
      "shift_type": "D",
      "shiftType": "D",
      "time_range": "08:00 - 17:00",
      "timeRange": "08:00 - 17:00"
    }
  ],
  "source": "database",
  "last_synced_at": "ISO datetime",
  "cache_count": 30
}
```

---

### GET /api/v1/employee/schedule-data
Employee schedule data: Try cache first, fallback to Google Sheets.

**Authentication:** Required

**Query Parameters:**
- `schedule_def_id`: Schedule definition ID (optional)
- `month`: Month in YYYY-MM format (optional)

**Response (200):**
```json
{
  "success": true,
  "source": "database_cache" | "google_sheets",
  "data": {
    "my_schedule": {
      "rows": [
        {
          "日期": "2025-11-01",
          "星期": "週一",
          "班別": "D",
          "時段": "08:00 - 17:00"
        }
      ],
      "columns": ["日期", "星期", "班別", "時段"]
    }
  },
  "last_synced_at": "ISO datetime (optional)"
}
```

---

## Google Sheets Endpoints

### GET /api/v1/sheets/list
List all sheets in a spreadsheet.

**Authentication:** Required

**Query Parameters (GET) or Request Body (POST):**
- `spreadsheet_url`: URL of the spreadsheet (required)

**Response (200):**
```json
{
  "success": true,
  "count": 5,
  "sheets": ["Sheet1", "Sheet2", ...],
  "spreadsheet_title": "Spreadsheet Name"
}
```

**Error Responses:**
- `400`: spreadsheet_url is required
- `503`: Google Sheets service not available

---

### POST /api/v1/sheets/validate
Validate Parameters and Preschedule sheets.

**Authentication:** Required

**Request Body:**
```json
{
  "params_url": "string (required)",
  "preschedule_url": "string (optional)"
}
```

**Response (200):**
```json
{
  "success": true,
  "valid": true,
  "errors": []
}
```

---

### GET /api/v1/sheets/fetch/<schedule_def_id>
Fetch all schedule data for a schedule definition (all 6 sheets).

**Authentication:** Required

**Query Parameters:**
- `month`: Month filter (optional)

**Response (200):**
```json
{
  "success": true,
  "sheets": {
    "parameters": { "data": [], "columns": [] },
    "employee": { "data": [], "columns": [] },
    "preferences": { "data": [], "columns": [] },
    "preschedule": { "data": [], "columns": [] },
    "designation_flow": { "data": [], "columns": [] },
    "final_output": { "data": [], "columns": [] }
  }
}
```

---

## Client Admin Endpoints

### GET /api/v1/clientadmin/dashboard
Client Admin dashboard.

**Authentication:** Required (ClientAdmin role)

**Response (200):**
```json
{
  "success": true,
  "dashboard": "clientadmin",
  "user": { /* user object */ },
  "tenant": { /* tenant object */ },
  "stats": {
    "tenants": 1,
    "departments": 5,
    "users": 20,
    "active_users": 18
  },
  "views": ["C1: Tenant", "C2: Department", "C3: User Account", "C4: Permissions"]
}
```

---

### GET /api/v1/clientadmin/c1-tenant
C1 Tenant Dashboard - Tenant overview.

**Authentication:** Required (ClientAdmin role)

**Response (200):**
```json
{
  "success": true,
  "data": { /* dashboard data */ }
}
```

---

### GET /api/v1/clientadmin/c2-department
C2 Department Management Dashboard.

**Authentication:** Required (ClientAdmin role)

**Response (200):**
```json
{
  "success": true,
  "data": { /* dashboard data */ }
}
```

---

### GET /api/v1/clientadmin/c3-user-account
C3 User Account Management Dashboard.

**Authentication:** Required (ClientAdmin role)

**Response (200):**
```json
{
  "success": true,
  "data": { /* dashboard data */ }
}
```

---

### GET /api/v1/clientadmin/c4-permissions
C4 Permission Maintenance Dashboard.

**Authentication:** Required (ClientAdmin role)

**Response (200):**
```json
{
  "success": true,
  "data": {
    "designation_flow": {
      "rows": [],
      "columns": []
    },
    /* other permission data */
  }
}
```

---

### POST /api/v1/clientadmin/department
Create department (ClientAdmin).

**Authentication:** Required (ClientAdmin role)

**Response (201):**
```json
{
  "created": true
}
```

---

### PUT /api/v1/clientadmin/department/<dept_id>
Update department (ClientAdmin).

**Authentication:** Required (ClientAdmin role)

**Response (200):**
```json
{
  "updated": true,
  "id": 1
}
```

---

### POST /api/v1/clientadmin/user
Create user (ClientAdmin).

**Authentication:** Required (ClientAdmin role)

**Response (201):**
```json
{
  "created": true
}
```

---

### PUT /api/v1/clientadmin/user/<user_id>
Update user (ClientAdmin).

**Authentication:** Required (ClientAdmin role)

**Response (200):**
```json
{
  "updated": true,
  "id": 1
}
```

---

### PUT /api/v1/clientadmin/schedule/access
Update schedule access (ClientAdmin).

**Authentication:** Required (ClientAdmin role)

**Response (200):**
```json
{
  "access_updated": true
}
```

---

## Schedule Manager Endpoints

### GET /api/v1/schedulemanager/dashboard
Schedule Manager dashboard.

**Authentication:** Required (ScheduleManager role)

**Response (200):**
```json
{
  "success": true,
  "dashboard": "schedulemanager",
  "user": { /* user object */ },
  "accessible_schedules": 5,
  "recent_jobs": [ /* job log objects */ ],
  "views": ["D1: Scheduling", "D2: Run", "D3: Export"]
}
```

---

### GET /api/v1/schedulemanager/d1-scheduling
D1 Scheduling Dashboard - View scheduling data from Google Sheets.

**Authentication:** Required (ScheduleManager role)

**Query Parameters:**
- `schedule_def_id`: Schedule definition ID (optional)

**Response (200):**
```json
{
  "success": true,
  "data": { /* dashboard data */ }
}
```

---

### GET /api/v1/schedulemanager/d2-run
D2 Run Dashboard - Data needed to run schedule from Google Sheets.

**Authentication:** Required (ScheduleManager role)

**Query Parameters:**
- `schedule_def_id`: Schedule definition ID (optional)

**Response (200):**
```json
{
  "success": true,
  "data": { /* dashboard data */ }
}
```

---

### GET /api/v1/schedulemanager/d3-export
D3 Export Dashboard - Final output from Google Sheets for export.

**Authentication:** Required (ScheduleManager role)

**Query Parameters:**
- `schedule_def_id`: Schedule definition ID (optional)

**Response (200):**
```json
{
  "success": true,
  "data": { /* dashboard data */ }
}
```

---

### POST /api/v1/schedulemanager/run-task
Run a scheduling task - redirects to schedule-job-logs/run endpoint.

**Authentication:** Required (ScheduleManager role)

**Request Body:**
```json
{
  "scheduleDefID": "integer (required)"
}
```

**Response:** Redirects to `/api/v1/schedule-job-logs/run`

---

### GET /api/v1/schedulemanager/task-status/<task_id>
Get task status.

**Authentication:** Required (ScheduleManager role)

**Response (200):**
```json
{
  "state": "PENDING" | "SUCCESS" | "FAILURE",
  "result": "object (if SUCCESS)",
  "error": "string (if FAILURE)"
}
```

---

### GET /api/v1/schedulemanager/logs
Get schedule job logs for current user.

**Authentication:** Required (ScheduleManager role)

**Query Parameters:**
- `limit`: Number of logs (default: 50)
- `hours`: Hours to look back (default: 24)

**Response (200):**
```json
{
  "success": true,
  "logs": [ /* job log objects */ ],
  "data": [ /* job log objects */ ],
  "count": 10
}
```

---

### GET /api/v1/schedulemanager/results/<sheet_id>
Get schedule results summary.

**Authentication:** Required (ScheduleManager role)

**Response (200):**
```json
{
  /* sheet summary data */
}
```

---

## System Admin Endpoints

### GET /api/v1/sysadmin/dashboard
SysAdmin dashboard.

**Authentication:** Required (SysAdmin role)

**Response (200):**
```json
{
  "success": true,
  "dashboard": "sysadmin",
  "user": { /* user object */ },
  "stats": {
    "total_tenants": 10,
    "totalTenants": 10,
    "active_tenants": 8,
    "activeTenants": 8,
    "total_schedules": 25,
    "totalSchedules": 25,
    "active_schedules": 20,
    "activeSchedules": 20
  },
  "views": ["B1: Organization", "B2: Schedule List", "B3: Schedule Maintenance"]
}
```

---

### GET /api/v1/sysadmin/b1-organization
B1 Organization Dashboard - Overview from Google Sheets.

**Authentication:** Required (SysAdmin role)

**Response (200):**
```json
{
  "success": true,
  "data": { /* dashboard data */ }
}
```

---

### GET /api/v1/sysadmin/b2-schedule-list
B2 Schedule List Maintenance - List all schedules.

**Authentication:** Required (SysAdmin role)

**Response (200):**
```json
{
  "success": true,
  "data": { /* dashboard data */ }
}
```

---

### GET /api/v1/sysadmin/b3-schedule-maintenance
B3 Schedule Maintenance - Detailed schedule sheets from Google Sheets.

**Authentication:** Required (SysAdmin role)

**Query Parameters:**
- `schedule_def_id`: Schedule definition ID (optional)

**Response (200):**
```json
{
  "success": true,
  "data": { /* dashboard data */ }
}
```

---

### POST /api/v1/sysadmin/tenant
Create tenant (SysAdmin).

**Authentication:** Required (SysAdmin role)

**Response (201):**
```json
{
  "created": true
}
```

---

### PUT /api/v1/sysadmin/tenant/<tenant_id>
Update tenant (SysAdmin).

**Authentication:** Required (SysAdmin role)

**Response (200):**
```json
{
  "updated": true,
  "id": 1
}
```

---

### GET /api/v1/sysadmin/logs
Get system logs.

**Authentication:** Required (SysAdmin role)

**Query Parameters:**
- `limit`: Number of logs (default: 10)

**Response (200):**
```json
{
  "success": true,
  "logs": [
    {
      "id": 1,
      "logID": 1,
      "action": "schedule_job_execution",
      "timestamp": "ISO datetime",
      "details": {
        "message": "string",
        "schedule_def_id": 1,
        "status": "completed"
      }
    }
  ],
  "data": [ /* same as logs */ ]
}
```

---

### GET /api/v1/sysadmin/system-health
System health check for SysAdmin.

**Authentication:** Required (SysAdmin role)

**Response (200):**
```json
{
  "success": true,
  "components": {
    "database": true,
    "redis": true | false,
    "celery": true | false
  },
  "status": "ok" | "degraded"
}
```

---

## Analytics Endpoints

### GET /api/v1/analytics/schedule-performance
Schedule performance analytics.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "data": {
    "total_jobs": 100,
    "success_rate": 0.95,
    "performance_metrics": []
  }
}
```

---

### GET /api/v1/analytics/task-trends
Task trends analytics.

**Authentication:** Required

**Query Parameters:**
- `days`: Number of days to analyze (default: 7)

**Response (200):**
```json
{
  "success": true,
  "data": {
    "period_days": 7,
    "total_tasks": 50,
    "trends": []
  }
}
```

---

### GET /api/v1/analytics/department-analytics
Department analytics (ClientAdmin only).

**Authentication:** Required (ClientAdmin role)

**Response (200):**
```json
{
  "success": true,
  "data": {
    "departments": 5,
    "analytics": []
  }
}
```

---

### GET /api/v1/analytics/user-activity
User activity analytics (ClientAdmin only).

**Authentication:** Required (ClientAdmin role)

**Response (200):**
```json
{
  "success": true,
  "data": {
    "total_users": 20,
    "activity": []
  }
}
```

---

### GET /api/v1/analytics/system-metrics
System metrics (SysAdmin only).

**Authentication:** Required (SysAdmin role)

**Response (200):**
```json
{
  "success": true,
  "data": {
    "total_tenants": 10,
    "total_schedules": 25,
    "metrics": []
  }
}
```

---

## Dashboard Endpoints

All dashboard endpoints are documented above. See:
- `/api/v1/dashboard` - Unified dashboard
- `/api/v1/dashboard/stats` - Dashboard statistics
- `/api/v1/dashboard/activities` - Recent activities
- `/api/v1/dashboard/notifications` - Notifications
- `/api/v1/dashboard/chart-data` - Chart data
- `/api/v1/dashboard/system-health` - System health
- `/api/v1/dashboard/schedule-data` - Schedule data

---

## Data Endpoints

### POST /api/v1/data/validate-source
Validate data source (Excel or Google Sheets).

**Authentication:** Required

**Request Body:**
```json
{
  "source_type": "excel" | "google_sheets"
}
```

**Response (200):**
```json
{
  "success": true,
  "valid": true,
  "source_type": "google_sheets"
}
```

---

### POST /api/v1/data/employee
Get employee data.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "data": []
}
```

---

### POST /api/v1/data/demand
Get demand data.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "data": []
}
```

---

### POST /api/v1/data/rules
Get rules data.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "data": []
}
```

---

### POST /api/v1/data/all
Get all data types.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "data": {
    "employee": [],
    "demand": [],
    "rules": []
  }
}
```

---

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "error": "Error message",
  "details": "Additional error details (optional)"
}
```

### 401 Unauthorized
```json
{
  "error": "Authentication required" | "Invalid credentials" | "Account is inactive"
}
```

### 403 Forbidden
```json
{
  "error": "Access denied" | "Admin access required" | "Permission denied"
}
```

### 404 Not Found
```json
{
  "error": "Resource not found"
}
```

### 409 Conflict
```json
{
  "error": "Resource already exists"
}
```

### 500 Internal Server Error
```json
{
  "error": "Error message",
  "details": "Error details (optional)"
}
```

---

## Notes

1. **Authentication**: Most endpoints require JWT authentication. Include the token in the `Authorization` header: `Bearer <token>`

2. **Pagination**: List endpoints support pagination with `page` and `per_page` query parameters.

3. **CORS**: All endpoints support CORS with appropriate headers.

4. **Soft Deletes**: Delete operations are soft deletes (deactivation) rather than hard deletes.

5. **Tenant Isolation**: Most endpoints automatically filter data by the user's tenant. SysAdmin users can access all tenants.

6. **Role-Based Access**: Different endpoints require different roles. Check the authentication requirements for each endpoint.

