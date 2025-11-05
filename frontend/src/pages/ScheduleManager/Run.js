import { useState, useEffect } from 'react';
import { scheduleService } from '../../services/scheduleService';
import DataTable from '../../components/DataTable';
import Button from '../../components/Button';
import Modal from '../../components/Modal';

export default function Run() {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedSchedule, setSelectedSchedule] = useState(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    loadSchedules();
  }, []);

  const loadSchedules = async () => {
    try {
      setLoading(true);
      setError('');
      
      console.log('[TRACE] ScheduleManager Run: Loading schedules...');
      
      const response = await scheduleService.getDefinitions(1, 100, { active: 'true' });
      
      console.log('[TRACE] ScheduleManager Run: Response:', response);
      console.log('[DEBUG] Checking Schedule Logs → count:', response.items?.length || 0);
      
      setSchedules(response.items || []);
      
      console.log('[DEBUG] Frontend Response Rendered Successfully');
    } catch (err) {
      console.error('[TRACE] ScheduleManager Run: Error loading data:', err);
      console.error('[TRACE] ScheduleManager Run: Error details:', {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status,
      });
      setError(err.response?.data?.error || 'Failed to load schedules');
    } finally {
      setLoading(false);
    }
  };

  const handleRun = (schedule) => {
    setSelectedSchedule(schedule);
    setIsModalOpen(true);
  };

  const confirmRun = async () => {
    try {
      setRunning(true);
      setError('');
      
      console.log('[DEBUG] Received Schedule Run Request');
      console.log('[DEBUG] Job Params:', { scheduleDefID: selectedSchedule.scheduleDefID });
      
      const response = await scheduleService.runJob({
        scheduleDefID: selectedSchedule.scheduleDefID,
      });
      
      console.log('[DEBUG] Schedule run response:', response);
      console.log('[DEBUG] Response status:', response.success, 'job_id:', response.celery_task_id || response.data?.logID);
      
      if (response.success) {
        setIsModalOpen(false);
        alert('Schedule job started successfully');
        // Reload schedules to show updated job status
        loadSchedules();
      } else {
        setError(response.error || 'Failed to run schedule job');
      }
    } catch (err) {
      console.error('[DEBUG] Schedule run error:', err);
      console.error('[DEBUG] Error details:', {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status,
      });
      setError(err.response?.data?.error || err.response?.data?.details || 'Failed to run schedule job');
    } finally {
      setRunning(false);
    }
  };

  const columns = [
    { key: 'scheduleName', label: 'Schedule Name' },
    { key: 'scheduleDefID', label: 'Schedule ID' },
  ];

  const actions = (row) => (
    <Button size="sm" onClick={() => handleRun(row)}>
      Run
    </Button>
  );

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-6">執行排班</h1>

      {error && (
        <div className="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      <DataTable
        columns={columns}
        data={schedules}
        loading={loading}
        actions={actions}
        emptyMessage="No schedules available"
      />

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Run Schedule"
      >
        {selectedSchedule && (
          <div>
            <p className="mb-4">Are you sure you want to run <strong>{selectedSchedule.scheduleName}</strong>?</p>
            <div className="flex justify-end space-x-3">
              <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
                Cancel
              </Button>
              <Button onClick={confirmRun} loading={running}>
                Run
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
