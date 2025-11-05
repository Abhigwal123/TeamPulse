import { useState, useEffect } from 'react';
import { departmentService } from '../../services/departmentService';
import { useAuth } from '../../context/AuthContext';
import { userService } from '../../services/userService';
import LoadingSpinner from '../../components/LoadingSpinner';
import Modal from '../../components/Modal';
import Button from '../../components/Button';

const formatDeptId = (deptId) => {
  if (!deptId) return 'DEPT-000';
  const str = String(deptId);
  return str.length > 8 ? `DEPT-${str.substring(str.length - 3)}` : `DEPT-${str.padStart(3, '0')}`;
};

const getStatusBadge = (isActive) => {
  if (isActive) {
    return (
      <span className="px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
        啟用
      </span>
    );
  }
  return (
    <span className="px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">
      停用
    </span>
  );
};

export default function Department() {
  const { tenant } = useAuth();
  const [departments, setDepartments] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingDepartment, setEditingDepartment] = useState(null);
  const [formData, setFormData] = useState({
    departmentID: '',
    departmentName: '',
    managerName: '',
    is_active: true,
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      
      console.log('[TRACE] ClientAdmin Department: Loading data...');
      
      const [deptResponse, userResponse] = await Promise.all([
        departmentService.getAll(1, 100),
        userService.getAll(1, 100),
      ]);

      console.log('[TRACE] ClientAdmin Department: Departments response:', deptResponse);
      console.log('[TRACE] ClientAdmin Department: Users response:', userResponse);

      const depts = deptResponse.data || [];
      const allUsers = userResponse.data || [];
      
      console.log('[TRACE] ClientAdmin Department: Data counts:', {
        departments: depts.length,
        users: allUsers.length,
      });

      // Map departments with managers (assume first ScheduleManager or ClientAdmin user as manager)
      const departmentsWithManagers = depts.map(dept => {
        const manager = allUsers.find(u => 
          u.departmentID === dept.departmentID && 
          (u.role === 'ScheduleManager' || u.role === 'ClientAdmin')
        ) || allUsers.find(u => u.departmentID === dept.departmentID);
        
        return {
          ...dept,
          managerName: manager?.full_name || manager?.username || '未指定',
        };
      });

      setDepartments(departmentsWithManagers);
      setUsers(allUsers);
    } catch (err) {
      setError(err.response?.data?.error || '載入部門資料失敗');
      console.error('Error loading departments:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingDepartment(null);
    setFormData({
      departmentID: '',
      departmentName: '',
      managerName: '',
      is_active: true,
    });
    setIsModalOpen(true);
  };

  const handleEdit = (dept) => {
    setEditingDepartment(dept);
    setFormData({
      departmentID: dept.departmentID,
      departmentName: dept.departmentName || '',
      managerName: dept.managerName || '',
      is_active: dept.is_active !== undefined ? dept.is_active : true,
    });
    setIsModalOpen(true);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError('');

      // For now, we'll save without manager - manager assignment would be a separate operation
      const saveData = {
        departmentName: formData.departmentName,
        is_active: formData.is_active,
      };

      if (editingDepartment) {
        await departmentService.update(editingDepartment.departmentID, saveData);
      } else {
        await departmentService.create(saveData);
      }

      setIsModalOpen(false);
      await loadData();
    } catch (err) {
      setError(err.response?.data?.error || '儲存部門失敗');
      console.error('Error saving department:', err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <LoadingSpinner />;
  }

  const tenantName = tenant?.tenantName || '機構';

  return (
    <div className="bg-gray-100 p-4 md:p-8">
      {/* C2.1: 頂部操作列 */}
      <div className="flex flex-col md:flex-row justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">部門管理</h1>
          <p className="mt-1 text-sm text-gray-600">管理貴機構 ({tenantName}) 內的所有部門。</p>
        </div>
        <button
          onClick={handleCreate}
          className="mt-4 md:mt-0 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none"
        >
          <svg className="h-5 w-5 mr-2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
          </svg>
          新增部門
        </button>
      </div>

      {error && (
        <div className="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* C2.2: 部門列表表格 */}
      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="w-full overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  部門 ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  部門名稱
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  部門主管
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  狀態
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {departments.length === 0 ? (
                <tr>
                  <td colSpan="5" className="px-6 py-4 text-center text-sm text-gray-500">
                    目前沒有部門資料
                  </td>
                </tr>
              ) : (
                departments.map((dept) => (
                  <tr key={dept.departmentID}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDeptId(dept.departmentID)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {dept.departmentName}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {dept.managerName}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(dept.is_active)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => handleEdit(dept)}
                        className="text-indigo-600 hover:text-indigo-900"
                      >
                        編輯
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* C2.3: 新增/編輯部門 Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setEditingDepartment(null);
        }}
        title=""
        size="md"
      >
        <div className="sm:flex sm:items-start">
          <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-indigo-100 sm:mx-0 sm:h-10 sm:w-10">
            <svg className="h-6 w-6 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
            </svg>
          </div>
          <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
            <h3 className="text-lg leading-6 font-medium text-gray-900">
              {editingDepartment ? '編輯部門' : '新增部門'}
            </h3>
            <div className="mt-4 space-y-4">
              <div>
                <label htmlFor="dept-id" className="block text-sm font-medium text-gray-700">
                  部門 ID
                </label>
                <input
                  type="text"
                  name="dept-id"
                  id="dept-id"
                  value={formatDeptId(formData.departmentID)}
                  readOnly={!!editingDepartment}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm bg-gray-50"
                  placeholder="DEPT-005"
                />
              </div>
              <div>
                <label htmlFor="dept-name" className="block text-sm font-medium text-gray-700">
                  部門名稱
                </label>
                <input
                  type="text"
                  name="dept-name"
                  id="dept-name"
                  value={formData.departmentName}
                  onChange={(e) => setFormData({ ...formData, departmentName: e.target.value })}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  placeholder="請輸入部門名稱"
                  required
                />
              </div>
              <div>
                <label htmlFor="dept-manager" className="block text-sm font-medium text-gray-700">
                  部門主管
                </label>
                <input
                  type="text"
                  name="dept-manager"
                  id="dept-manager"
                  value={formData.managerName}
                  onChange={(e) => setFormData({ ...formData, managerName: e.target.value })}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  placeholder="請輸入主管姓名"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">狀態</label>
                <select
                  value={formData.is_active ? 'active' : 'inactive'}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.value === 'active' })}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                >
                  <option value="active">啟用</option>
                  <option value="inactive">停用</option>
                </select>
              </div>
            </div>
          </div>
        </div>
        <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse mt-6">
          <Button
            onClick={handleSave}
            loading={saving}
            className="w-full sm:ml-3 sm:w-auto"
          >
            儲存
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              setIsModalOpen(false);
              setEditingDepartment(null);
            }}
            className="mt-3 w-full sm:mt-0 sm:ml-3 sm:w-auto"
          >
            取消
          </Button>
        </div>
      </Modal>
    </div>
  );
}
