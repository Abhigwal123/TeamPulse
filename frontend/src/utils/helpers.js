export const formatDate = (date) => {
  if (!date) return '';
  return new Date(date).toLocaleDateString();
};

export const formatDateTime = (date) => {
  if (!date) return '';
  return new Date(date).toLocaleString();
};

export const capitalize = (str) => {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
};

export const getRoleDisplayName = (role) => {
  const roleMap = {
    SysAdmin: 'System Administrator',
    ClientAdmin: 'Client Administrator',
    ScheduleManager: 'Schedule Manager',
    Employee: 'Employee',
  };
  return roleMap[role] || role;
};





