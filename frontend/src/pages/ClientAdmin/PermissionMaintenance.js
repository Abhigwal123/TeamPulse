import { useState, useEffect } from 'react';
import { scheduleService } from '../../services/scheduleService';
import { userService } from '../../services/userService';
import LoadingSpinner from '../../components/LoadingSpinner';
import Button from '../../components/Button';

export default function PermissionMaintenance() {
  const [scheduleManagers, setScheduleManagers] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [permissions, setPermissions] = useState(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      
      console.log('[TRACE] ClientAdmin Permissions: Loading data...');
      
      // Load schedule managers (ScheduleManager role users) and schedules
      const [userResponse, scheduleResponse, permissionResponse] = await Promise.all([
        userService.getAll(1, 100),
        scheduleService.getDefinitions(1, 100, { active: 'true' }),
        scheduleService.getPermissions(1, 100),
      ]);

      console.log('[TRACE] ClientAdmin Permissions: Users response:', userResponse);
      console.log('[TRACE] ClientAdmin Permissions: Schedules response:', scheduleResponse);
      console.log('[TRACE] ClientAdmin Permissions: Permissions response:', permissionResponse);

      const allUsers = userResponse.data || [];
      const allSchedules = scheduleResponse.items || scheduleResponse.data || [];
      const allPermissions = permissionResponse.data || permissionResponse.items || [];
      
      console.log('[TRACE] ClientAdmin Permissions: Data counts:', {
        users: allUsers.length,
        schedules: allSchedules.length,
        permissions: allPermissions.length,
      });

      // Filter only ScheduleManager users
      const managers = allUsers.filter(u => 
        u.role === 'ScheduleManager' || u.role === 'Schedule_Manager'
      );

      setScheduleManagers(managers);
      setSchedules(allSchedules);

      // Build permission map: Map<`${userID}_${scheduleDefID}`, permission>
      const permissionMap = new Map();
      allPermissions.forEach(perm => {
        if (perm.canRunJob || perm.can_view) {
          const key = `${perm.userID}_${perm.scheduleDefID}`;
          permissionMap.set(key, perm);
        }
      });
      setPermissions(permissionMap);
    } catch (err) {
      setError(err.response?.data?.error || '載入權限資料失敗');
      console.error('Error loading permissions:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTogglePermission = (userId, scheduleId) => {
    const key = `${userId}_${scheduleId}`;
    const newPermissions = new Map(permissions);
    
    if (newPermissions.has(key)) {
      newPermissions.delete(key);
    } else {
      newPermissions.set(key, {
        userID: userId,
        scheduleDefID: scheduleId,
        canRunJob: true,
        can_view: true,
      });
    }
    
    setPermissions(newPermissions);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError('');

      // Collect all permission changes
      const permissionUpdates = [];
      
      // Create/update permissions
      permissions.forEach((perm, key) => {
        permissionUpdates.push(
          scheduleService.createPermission({
            userID: perm.userID,
            scheduleDefID: perm.scheduleDefID,
            canRunJob: true,
            can_view: true,
          }).catch(err => {
            // If permission exists, update it
            if (err.response?.status === 400) {
              // Find existing permission and update
              return scheduleService.getPermissions(1, 100, {
                user_id: perm.userID,
                schedule_def_id: perm.scheduleDefID,
              }).then(response => {
                const existing = response.data?.[0];
                if (existing) {
                  return scheduleService.updatePermission(existing.permissionID, {
                    canRunJob: true,
                    can_view: true,
                  });
                }
              });
            }
            throw err;
          })
        );
      });

      // Delete permissions that were unchecked
      // Get all existing permissions first
      const allExistingPerms = await scheduleService.getPermissions(1, 100);
      const existingPermsList = allExistingPerms.data || allExistingPerms.items || [];
      const existingMap = new Map();
      existingPermsList.forEach(perm => {
        const key = `${perm.userID}_${perm.scheduleDefID}`;
        existingMap.set(key, perm);
      });

      // Find permissions to deactivate (exist in backend but not in current state)
      existingMap.forEach((perm, key) => {
        if (!permissions.has(key) && (perm.canRunJob || perm.can_view)) {
          // Update to deactivate
          if (perm.permissionID) {
            permissionUpdates.push(
              scheduleService.updatePermission(perm.permissionID, {
                canRunJob: false,
                can_view: false,
                is_active: false,
              })
            );
          }
        }
      });

      await Promise.all(permissionUpdates);
      alert('權限已成功儲存');
      await loadData();
    } catch (err) {
      setError(err.response?.data?.error || '儲存權限失敗');
      console.error('Error saving permissions:', err);
    } finally {
      setSaving(false);
    }
  };

  const isPermissionChecked = (userId, scheduleId) => {
    const key = `${userId}_${scheduleId}`;
    return permissions.has(key);
  };

  const getUserDepartment = (user) => {
    // This would come from user.department relationship
    // For now, return a placeholder
    return user.departmentName || '未指定';
  };

  if (loading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="bg-gray-100 p-4 md:p-8">
      {/* C4.1: 頂部操作列 */}
      <div className="flex flex-col md:flex-row justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">排班權限維護</h1>
          <p className="mt-1 text-sm text-gray-600">
            請勾選允許「排班主管」存取及執行「班表」的權限。
          </p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="mt-4 md:mt-0 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none disabled:opacity-50"
        >
          <svg className="h-5 w-5 mr-2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
          {saving ? '儲存中...' : '儲存變更'}
        </button>
      </div>

      {error && (
        <div className="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* C4.2: 權限矩陣表格 */}
      <div className="w-full overflow-x-auto rounded-xl shadow-lg">
        <div className="bg-white rounded-xl overflow-hidden min-w-[800px]">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50 sticky-header">
              <tr>
                <th className="sticky-col px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  排班主管 (使用者)
                </th>
                {schedules.map((schedule) => (
                  <th
                    key={schedule.scheduleDefID}
                    className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    {schedule.scheduleName}
                  </th>
                ))}
                {schedules.length === 0 && (
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    暫無班表
                  </th>
                )}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {scheduleManagers.length === 0 ? (
                <tr>
                  <td colSpan={schedules.length + 1} className="px-6 py-4 text-center text-sm text-gray-500">
                    目前沒有排班主管
                  </td>
                </tr>
              ) : (
                scheduleManagers.map((manager) => (
                  <tr key={manager.userID} className="hover:bg-gray-50">
                    <td className="sticky-col px-6 py-4 whitespace-nowrap bg-white">
                      <div className="text-sm font-medium text-gray-900">
                        {manager.full_name || manager.username} ({manager.username})
                      </div>
                      <div className="text-sm text-gray-500">
                        {getUserDepartment(manager)}
                      </div>
                    </td>
                    {schedules.map((schedule) => (
                      <td key={schedule.scheduleDefID} className="px-6 py-4 whitespace-nowrap text-center">
                        <input
                          type="checkbox"
                          checked={isPermissionChecked(manager.userID, schedule.scheduleDefID)}
                          onChange={() => handleTogglePermission(manager.userID, schedule.scheduleDefID)}
                          className="h-5 w-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                        />
                      </td>
                    ))}
                    {schedules.length === 0 && (
                      <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                        --
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
