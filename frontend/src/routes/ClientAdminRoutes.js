import { Routes, Route } from 'react-router-dom';
import ClientAdminLayout from '../layouts/ClientAdminLayout';
import ProtectedRoute from './ProtectedRoute';
import {
  Dashboard,
  Department,
  UserAccountManagement,
  PermissionMaintenance,
} from '../pages/ClientAdmin';

export default function ClientAdminRoutes() {
  return (
    <ProtectedRoute requiredRole="ClientAdmin">
      <Routes>
        <Route path="/*" element={<ClientAdminLayout />}>
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="department" element={<Department />} />
          <Route path="users" element={<UserAccountManagement />} />
          <Route path="permissions" element={<PermissionMaintenance />} />
          <Route index element={<Dashboard />} />
        </Route>
      </Routes>
    </ProtectedRoute>
  );
}

