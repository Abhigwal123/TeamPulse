"""
Integration module to bridge the original scheduling system with the SaaS backend
"""

import os
import sys
import shutil
from typing import Dict, Any, Optional
from pathlib import Path

# Add the original app directory to Python path
original_app_path = Path(__file__).parent.parent.parent / "app"
if str(original_app_path) not in sys.path:
    sys.path.insert(0, str(original_app_path))

try:
    from run_refactored import run_schedule_task
    from app.data_provider import create_data_provider
    from app.data_writer import create_data_writer, write_all_results_to_excel, write_all_results_to_google_sheets
    from app.schedule_cpsat import process_input_data, solve_cpsat
    from app.schedule_helpers import (
        build_rows, build_daily_analysis_report, check_hard_constraints, 
        check_soft_constraints, generate_soft_constraint_report, 
        create_schedule_chart, debug_schedule
    )
    from app.utils.logger import setup_logging, get_logger
except ImportError as e:
    print(f"Warning: Could not import original scheduling modules: {e}")
    # Create dummy functions for development
    def run_schedule_task(*args, **kwargs):
        return {"error": "Original scheduling modules not available"}
    
    def create_data_provider(*args, **kwargs):
        return None
    
    def process_input_data(*args, **kwargs):
        return {}
    
    def solve_cpsat(*args, **kwargs):
        return {"error": "Solver not available"}


def run_scheduling_task_saas(
    input_source: str,
    input_config: Dict[str, Any],
    output_destination: str,
    output_config: Dict[str, Any],
    time_limit: float = 90.0,
    debug_shift: Optional[str] = None,
    log_level: str = "INFO",
    user_id: Optional[int] = None,
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run scheduling task with SaaS-specific modifications
    
    Args:
        input_source: 'excel' or 'google_sheets'
        input_config: Configuration for input source
        output_destination: 'excel' or 'google_sheets'
        output_config: Configuration for output destination
        time_limit: Time limit for solving in seconds
        debug_shift: Optional debug shift in format "YYYY/MM/DD,班別,崗位"
        log_level: Logging level
        user_id: User ID for file organization
        task_id: Task ID for file organization
    
    Returns:
        Dictionary containing results and status
    """
    
    # Setup logging with file handler
    log_file = "logs/system.log" if user_id and task_id else None
    setup_logging(level=log_level, log_file=log_file)
    logger = get_logger(__name__)
    logger.info(f"Starting SaaS scheduling task for user {user_id}, task {task_id}")
    logger.info(f"Input: {input_source} -> Output: {output_destination}")
    
    try:
        # Create user-specific directories
        if user_id and task_id:
            user_dir = f"uploads/{user_id}"
            task_dir = f"{user_dir}/{task_id}"
            os.makedirs(task_dir, exist_ok=True)
            
            # Update file paths to be user/task specific
            if input_source == "excel" and "file_path" in input_config:
                original_path = input_config["file_path"]
                filename = os.path.basename(original_path)
                new_path = f"{task_dir}/input_{filename}"
                shutil.copy2(original_path, new_path)
                input_config = input_config.copy()
                input_config["file_path"] = new_path
            
            if output_destination == "excel" and "output_path" in output_config:
                original_path = output_config["output_path"]
                filename = os.path.basename(original_path)
                new_path = f"{task_dir}/output_{filename}"
                output_config = output_config.copy()
                output_config["output_path"] = new_path
        
        # Run the original scheduling task
        result = run_schedule_task(
            input_source=input_source,
            input_config=input_config,
            output_destination=output_destination,
            output_config=output_config,
            time_limit=time_limit,
            debug_shift=debug_shift,
            log_level=log_level
        )
        
        # Add SaaS-specific metadata
        if isinstance(result, dict) and "error" not in result:
            result["user_id"] = user_id
            result["task_id"] = task_id
            result["saas_version"] = "2.0.0"
        
        logger.info(f"SaaS scheduling task completed for user {user_id}, task {task_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error in SaaS scheduling task: {e}")
        return {"error": str(e)}


def validate_input_config(input_source: str, input_config: Dict[str, Any]) -> bool:
    """
    Validate input configuration
    
    Args:
        input_source: Input source type
        input_config: Input configuration
    
    Returns:
        True if valid, False otherwise
    """
    if input_source == "excel":
        if "file_path" not in input_config:
            return False
        if not os.path.exists(input_config["file_path"]):
            return False
    elif input_source == "google_sheets":
        if "spreadsheet_url" not in input_config:
            return False
        # Basic URL validation
        url = input_config["spreadsheet_url"]
        if not url.startswith("https://docs.google.com/spreadsheets/"):
            return False
    else:
        return False
    
    return True


def validate_output_config(output_destination: str, output_config: Dict[str, Any]) -> bool:
    """
    Validate output configuration
    
    Args:
        output_destination: Output destination type
        output_config: Output configuration
    
    Returns:
        True if valid, False otherwise
    """
    if output_destination == "excel":
        if "output_path" not in output_config:
            return False
    elif output_destination == "google_sheets":
        if "spreadsheet_url" not in output_config:
            return False
        # Basic URL validation
        url = output_config["spreadsheet_url"]
        if not url.startswith("https://docs.google.com/spreadsheets/"):
            return False
    else:
        return False
    
    return True


def cleanup_task_files(user_id: int, task_id: str) -> bool:
    """
    Clean up task-specific files
    
    Args:
        user_id: User ID
        task_id: Task ID
    
    Returns:
        True if cleanup successful, False otherwise
    """
    try:
        task_dir = f"uploads/{user_id}/{task_id}"
        if os.path.exists(task_dir):
            shutil.rmtree(task_dir)
        return True
    except Exception as e:
        print(f"Error cleaning up task files: {e}")
        return False
