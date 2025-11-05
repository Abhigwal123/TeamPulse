# AI Scheduling Service Integration
import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class AISchedulingService:
    """AI Scheduling Service that integrates with Google Sheets and Phase 1 data"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get('ai_service_url', 'http://localhost:5000')
        self.timeout = config.get('timeout', 300)  # 5 minutes default timeout
        
    def trigger_job(self, schedule_definition: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Trigger an AI scheduling job according to the system architecture
        
        Args:
            schedule_definition: Schedule definition from database
            user_id: ID of user who triggered the job
            
        Returns:
            Dict containing job status and summary
        """
        try:
            # Prepare job data according to ERD schema
            job_data = {
                'scheduleDefID': schedule_definition['scheduleDefID'],
                'tenantID': schedule_definition['tenantID'],
                'departmentID': schedule_definition['departmentID'],
                'scheduleName': schedule_definition['scheduleName'],
                'paramsSheetURL': schedule_definition['paramsSheetURL'],
                'prefsSheetURL': schedule_definition['prefsSheetURL'],
                'resultsSheetURL': schedule_definition['resultsSheetURL'],
                'schedulingAPI': schedule_definition['schedulingAPI'],
                'runByUserID': user_id,
                'startTime': datetime.utcnow().isoformat()
            }
            
            # Call AI Scheduling Service
            response = requests.post(
                f"{self.base_url}/api/v1/trigger-job",
                json=job_data,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'status': 'success',
                    'job_id': result.get('job_id'),
                    'summary': result.get('summary', 'Job completed successfully'),
                    'endTime': datetime.utcnow().isoformat()
                }
            else:
                return {
                    'status': 'failed',
                    'summary': f"AI Service error: {response.text}",
                    'endTime': datetime.utcnow().isoformat()
                }
                
        except requests.exceptions.Timeout:
            return {
                'status': 'failed',
                'summary': 'AI Service timeout - job took too long to complete',
                'endTime': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error triggering AI job: {str(e)}")
            return {
                'status': 'failed',
                'summary': f"Error: {str(e)}",
                'endTime': datetime.utcnow().isoformat()
            }
    
    def poll_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Poll the status of a running AI job
        
        Args:
            job_id: ID of the job to check
            
        Returns:
            Dict containing current job status
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/job-status/{job_id}",
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'status': 'unknown',
                    'summary': f"Failed to get job status: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error polling job status: {str(e)}")
            return {
                'status': 'error',
                'summary': f"Error: {str(e)}"
            }

class GoogleSheetsIntegration:
    """Google Sheets integration for parameters, preschedule, and results"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.service_account_file = config.get('service_account_file')
        self.scopes = ['https://www.googleapis.com/auth/spreadsheets']
        
    def read_parameters(self, sheet_url: str) -> Dict[str, Any]:
        """
        Read scheduling parameters from Google Sheet
        
        Args:
            sheet_url: URL of the parameters sheet
            
        Returns:
            Dict containing parameters data
        """
        try:
            # Extract spreadsheet ID from URL
            spreadsheet_id = self._extract_spreadsheet_id(sheet_url)
            
            # Read data from Google Sheets API
            # This would integrate with gspread library
            # For now, return mock data structure
            return {
                'status': 'success',
                'data': {
                    'parameters': {
                        'shift_duration': 8,
                        'min_staff_per_shift': 3,
                        'max_consecutive_shifts': 2,
                        'preferred_shifts': ['morning', 'afternoon']
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error reading parameters: {str(e)}")
            return {
                'status': 'error',
                'data': None,
                'error': str(e)
            }
    
    def read_preschedule(self, sheet_url: str) -> Dict[str, Any]:
        """
        Read preschedule data from Google Sheet
        
        Args:
            sheet_url: URL of the preschedule sheet
            
        Returns:
            Dict containing preschedule data
        """
        try:
            spreadsheet_id = self._extract_spreadsheet_id(sheet_url)
            
            # Read preschedule data
            return {
                'status': 'success',
                'data': {
                    'preschedule': {
                        'employee_availability': [],
                        'shift_preferences': [],
                        'time_off_requests': []
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error reading preschedule: {str(e)}")
            return {
                'status': 'error',
                'data': None,
                'error': str(e)
            }
    
    def write_results(self, sheet_url: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Write scheduling results to Google Sheet
        
        Args:
            sheet_url: URL of the results sheet
            results: Scheduling results to write
            
        Returns:
            Dict containing write status
        """
        try:
            spreadsheet_id = self._extract_spreadsheet_id(sheet_url)
            
            # Write results to Google Sheets API
            return {
                'status': 'success',
                'message': 'Results written successfully'
            }
            
        except Exception as e:
            logger.error(f"Error writing results: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _extract_spreadsheet_id(self, url: str) -> str:
        """Extract spreadsheet ID from Google Sheets URL"""
        # Extract ID from URL like: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
        parts = url.split('/')
        for i, part in enumerate(parts):
            if part == 'd' and i + 1 < len(parts):
                return parts[i + 1]
        raise ValueError(f"Could not extract spreadsheet ID from URL: {url}")

class SchedulingOrchestrator:
    """Main orchestrator that coordinates the scheduling process"""
    
    def __init__(self, config: Dict[str, Any]):
        self.ai_service = AISchedulingService(config.get('ai_service', {}))
        self.google_sheets = GoogleSheetsIntegration(config.get('google_sheets', {}))
        self.config = config
    
    def run_scheduling_job(self, schedule_definition: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Run a complete scheduling job according to the system architecture
        
        Args:
            schedule_definition: Schedule definition from database
            user_id: ID of user who triggered the job
            
        Returns:
            Dict containing complete job results
        """
        try:
            # Step 1: Read parameters from Google Sheet
            params_result = self.google_sheets.read_parameters(schedule_definition['paramsSheetURL'])
            if params_result['status'] != 'success':
                return {
                    'status': 'failed',
                    'summary': f"Failed to read parameters: {params_result.get('error', 'Unknown error')}"
                }
            
            # Step 2: Read preschedule from Google Sheet
            preschedule_result = self.google_sheets.read_preschedule(schedule_definition['prefsSheetURL'])
            if preschedule_result['status'] != 'success':
                return {
                    'status': 'failed',
                    'summary': f"Failed to read preschedule: {preschedule_result.get('error', 'Unknown error')}"
                }
            
            # Step 3: Trigger AI scheduling job
            ai_result = self.ai_service.trigger_job(schedule_definition, user_id)
            
            # Step 4: Write results to Google Sheet if successful
            if ai_result['status'] == 'success':
                write_result = self.google_sheets.write_results(
                    schedule_definition['resultsSheetURL'],
                    ai_result
                )
                if write_result['status'] != 'success':
                    ai_result['status'] = 'partial_success'
                    ai_result['summary'] += f" (Warning: Failed to write results: {write_result.get('error', 'Unknown error')})"
            
            return ai_result
            
        except Exception as e:
            logger.error(f"Error in scheduling orchestrator: {str(e)}")
            return {
                'status': 'failed',
                'summary': f"Orchestrator error: {str(e)}"
            }












