"""
Google Sheets Service Import Utility
Provides safe dynamic import with multiple fallback paths and detailed logging
"""
import logging
import sys
import os
import importlib.util
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Import trace logger
try:
    from app.utils.trace_logger import trace_log, trace_import_success, trace_import_failure
except ImportError:
    # Fallback if trace logger not available
    def trace_log(stage, filename, detail, extra=None):
        logger.info(f"[TRACE] Stage={stage} | File={filename} | Detail={detail}")
    
    def trace_import_success(module_name, import_path):
        trace_log('ImportSuccess', 'service_loader.py', f'Google Sheets loaded from {import_path}')
    
    def trace_import_failure(reason, attempts=0):
        trace_log('ImportFailFinal', 'service_loader.py', f'No valid module found: {reason}')

# Module-level state
SHEETS_AVAILABLE = False
fetch_schedule_data = None
GoogleSheetsService = None
list_sheets = None
validate_sheets = None
_import_attempted = False
_last_import_error = None


def _try_import_google_sheets(force_retry: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Try to import Google Sheets service with multiple fallback paths.
    
    Args:
        force_retry: If True, retry even if previous attempt failed
    
    Returns:
        Tuple of (success: bool, import_path: Optional[str])
    """
    global SHEETS_AVAILABLE, fetch_schedule_data, GoogleSheetsService, list_sheets, validate_sheets, _import_attempted, _last_import_error
    
    if SHEETS_AVAILABLE:
        return True, "already_loaded"
    
    if _import_attempted and not force_retry:
        logger.warning(f"Skipping import - previous attempt failed. Last error: {_last_import_error}")
        return False, f"previous_attempt_failed: {_last_import_error}"
    
    # Reset for retry
    if force_retry:
        _import_attempted = False
        _last_import_error = None
        logger.info("Force retry requested, resetting import state")
    
    _import_attempted = True
    
    # Calculate project root paths
    current_file = os.path.abspath(__file__)  # backend/app/services/google_sheets_import.py
    services_dir = os.path.dirname(current_file)  # backend/app/services
    app_dir = os.path.dirname(services_dir)  # backend/app
    backend_dir = os.path.dirname(app_dir)  # backend/
    project_root = os.path.dirname(backend_dir)  # Project_Up/
    
    # Normalize paths to handle Windows/Unix differences
    project_root = os.path.normpath(project_root)
    current_file = os.path.normpath(current_file)
    
    trace_log('Import', 'google_sheets_import.py', 'Starting Google Sheets import attempt')
    
    logger.info("=" * 80)
    logger.info("GOOGLE SHEETS SERVICE IMPORT CHECK")
    logger.info("=" * 80)
    logger.info(f"Current file: {current_file}")
    logger.info(f"Project root: {project_root}")
    logger.info(f"Project root normalized: {os.path.normpath(project_root)}")
    
    # Path to check
    target_path = os.path.join(project_root, 'app', 'services', 'google_sheets', 'service.py')
    logger.info(f"Target path: {target_path}")
    path_exists = os.path.exists(target_path)
    logger.info(f"Path exists: {path_exists}")
    
    trace_log('Import', 'google_sheets_import.py', f'Checking path: {target_path} (exists: {path_exists})')
    
    # Log all paths we'll try
    paths_to_try = [
        os.path.join(project_root, 'app', 'services', 'google_sheets', 'service.py'),
        os.path.join(os.path.dirname(project_root), 'app', 'services', 'google_sheets', 'service.py'),
    ]
    logger.info("Paths to check:")
    for idx, p in enumerate(paths_to_try, 1):
        exists = os.path.exists(p)
        logger.info(f"  {idx}. {p} - Exists: {exists}")
        trace_log('Import', 'google_sheets_import.py', f'PathChecked={p} | Exists={exists}')
    
    # Import strategy 1: Direct import with project root in path
    try:
        logger.info("Attempt 1: Direct import from app.services.google_sheets.service")
        trace_log('Import', 'google_sheets_import.py', 'Attempt 1: Direct import from app.services.google_sheets.service')
        
        # Ensure project_root is in sys.path (normalize both for comparison)
        normalized_paths = [os.path.normpath(p) for p in sys.path]
        normalized_project_root = os.path.normpath(project_root)
        
        if normalized_project_root not in normalized_paths:
            sys.path.insert(0, project_root)
            logger.info(f"Added to sys.path: {project_root}")
        else:
            # Move to front if it's not first
            idx = normalized_paths.index(normalized_project_root)
            if idx > 0:
                sys.path.insert(0, sys.path.pop(idx))
                logger.info(f"Moved project_root from position {idx} to position 0")
        
        # Verify path is actually in sys.path
        logger.info(f"Current sys.path[0]: {sys.path[0]}")
        logger.info(f"Normalized sys.path[0]: {os.path.normpath(sys.path[0])}")
        logger.info(f"Project root normalized: {normalized_project_root}")
        logger.info(f"Match: {os.path.normpath(sys.path[0]) == normalized_project_root}")
        
        # Verify the app package directory exists
        app_dir_check = os.path.join(project_root, 'app')
        logger.info(f"app directory exists: {os.path.exists(app_dir_check)}")
        logger.info(f"app directory path: {app_dir_check}")
        
        # Verify __init__.py files exist
        app_init = os.path.join(project_root, 'app', '__init__.py')
        services_init = os.path.join(project_root, 'app', 'services', '__init__.py')
        sheets_init = os.path.join(project_root, 'app', 'services', 'google_sheets', '__init__.py')
        
        logger.info(f"app/__init__.py exists: {os.path.exists(app_init)}")
        logger.info(f"app/services/__init__.py exists: {os.path.exists(services_init)}")
        logger.info(f"app/services/google_sheets/__init__.py exists: {os.path.exists(sheets_init)}")
        
        # Use regular import - project_root is now in sys.path
        # This is the cleanest approach and will work if the path is correct
        logger.info("Attempting regular import with project_root in sys.path")
        
        # Double-check project_root is first in path
        if sys.path[0] != project_root:
            sys.path.insert(0, project_root)
            logger.info(f"Moved project_root to first position in sys.path")
        
        # Use importlib to load directly from file - bypasses Python's module resolution
        # This avoids conflicts with backend/app/ directory
        service_file_path = os.path.join(project_root, 'app', 'services', 'google_sheets', 'service.py')
        logger.info(f"Loading module directly from file: {service_file_path}")
        
        try:
            # Use compile + exec to load module directly (bypasses importlib's strict name checking)
            logger.info("Loading module using compile + exec...")
            
            # Read the file
            with open(service_file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # Create a module object
            import types
            module = types.ModuleType("app.services.google_sheets.service")
            module.__file__ = service_file_path
            module.__package__ = "app.services.google_sheets"
            
            # Temporarily add parent modules to sys.modules
            parent_modules = [
                'app',
                'app.services',
                'app.services.google_sheets'
            ]
            
            for mod_name in parent_modules:
                if mod_name not in sys.modules:
                    fake_module = types.ModuleType(mod_name)
                    mod_path = os.path.join(project_root, *mod_name.split('.'))
                    if os.path.isdir(mod_path):
                        fake_module.__path__ = [mod_path]
                        fake_module.__file__ = os.path.join(mod_path, '__init__.py')
                    sys.modules[mod_name] = fake_module
                    logger.info(f"Created parent module: {mod_name}")
            
            # Add module to sys.modules before execution
            sys.modules["app.services.google_sheets.service"] = module
            
            # Compile and execute
            code = compile(source_code, service_file_path, 'exec')
            exec(code, module.__dict__)
            logger.info("✅ Module loaded successfully using compile + exec")
            
            # Extract required attributes
            _fetch = getattr(module, 'fetch_schedule_data', None)
            _GS = getattr(module, 'GoogleSheetsService', None)
            _list = getattr(module, 'list_sheets', None)
            _validate = getattr(module, 'validate_sheets', None)
            
            logger.info(f"Extracted - fetch_schedule_data: {_fetch is not None}, GoogleSheetsService: {_GS is not None}, list_sheets: {_list is not None}, validate_sheets: {_validate is not None}")
            
            if _fetch is None or _GS is None:
                raise ImportError(
                    f"Required attributes not found in module. "
                    f"fetch_schedule_data: {_fetch is not None}, "
                    f"GoogleSheetsService: {_GS is not None}"
                )
            
            logger.info("✅ Successfully extracted all required attributes")
            
        except Exception as e:
            logger.error(f"Failed to load module using importlib: {e}")
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            raise
        
        fetch_schedule_data = _fetch
        GoogleSheetsService = _GS
        list_sheets = _list
        validate_sheets = _validate
        SHEETS_AVAILABLE = True
        
        logger.info("✅ Google Sheets service loaded successfully from: app.services.google_sheets.service")
        logger.info(f"✅ Import path: {project_root}")
        logger.info("=" * 80)
        trace_import_success('app.services.google_sheets.service', project_root)
        
        # Verify imports are actually available
        if fetch_schedule_data is None or GoogleSheetsService is None:
            logger.error("[TRACE] Import reported success but fetch_schedule_data or GoogleSheetsService is None!")
            SHEETS_AVAILABLE = False
            return False, "Import succeeded but modules are None"
        
        logger.info(f"[TRACE] ✅ Verified imports - fetch_schedule_data: {fetch_schedule_data is not None}, GoogleSheetsService: {GoogleSheetsService is not None}")
        return True, project_root
        
    except ImportError as e1:
        _last_import_error = str(e1)
        logger.warning(f"Attempt 1 failed: {e1}")
        import traceback
        logger.error(f"Import error traceback:\n{traceback.format_exc()}")
    
    # Import strategy 2: Check if file exists, then try with absolute path
    try:
        logger.info("Attempt 2: Checking absolute path and file existence")
        if not os.path.exists(target_path):
            logger.error(f"Target file does not exist: {target_path}")
        else:
            logger.info(f"Target file exists, trying import again with explicit path")
            # Try again with explicit path manipulation
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            from app.services.google_sheets.service import (
                fetch_schedule_data as _fetch,
                GoogleSheetsService as _GS,
                list_sheets as _list,
                validate_sheets as _validate
            )
            
            fetch_schedule_data = _fetch
            GoogleSheetsService = _GS
            list_sheets = _list
            validate_sheets = _validate
            SHEETS_AVAILABLE = True
            
            logger.info("✅ Google Sheets service loaded successfully (attempt 2)")
            logger.info("=" * 80)
            return True, project_root
            
    except ImportError as e2:
        _last_import_error = str(e2)
        logger.warning(f"Attempt 2 failed: {e2}")
        import traceback
        logger.error(f"Import error traceback:\n{traceback.format_exc()}")
    
    # Import strategy 3: Try importing from parent directory
    try:
        logger.info("Attempt 3: Checking parent directory")
        parent_dir = os.path.dirname(project_root)
        parent_target = os.path.join(parent_dir, 'app', 'services', 'google_sheets', 'service.py')
        
        if os.path.exists(parent_target):
            logger.info(f"Found in parent: {parent_target}")
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            from app.services.google_sheets.service import (
                fetch_schedule_data as _fetch,
                GoogleSheetsService as _GS,
                list_sheets as _list,
                validate_sheets as _validate
            )
            
            fetch_schedule_data = _fetch
            GoogleSheetsService = _GS
            list_sheets = _list
            validate_sheets = _validate
            SHEETS_AVAILABLE = True
            
            logger.info("✅ Google Sheets service loaded successfully (attempt 3)")
            logger.info("=" * 80)
            return True, parent_dir
            
    except ImportError as e3:
        _last_import_error = str(e3)
        logger.warning(f"Attempt 3 failed: {e3}")
        import traceback
        logger.error(f"Import error traceback:\n{traceback.format_exc()}")
    
    # All attempts failed
    _last_import_error = "All import attempts failed"
    logger.error("❌ Google Sheets service not available after all import attempts")
    logger.error("Checked paths:")
    logger.error(f"  1. {project_root}/app/services/google_sheets/service.py")
    logger.error(f"  2. {os.path.dirname(project_root)}/app/services/google_sheets/service.py")
    logger.error(f"Current sys.path (first 5): {sys.path[:5]}")
    logger.error("=" * 80)
    logger.error("💡 TIP: Make sure backend is run from backend/ directory")
    logger.error("💡 TIP: Check that app/services/google_sheets/service.py exists at project root")
    
    trace_import_failure(_last_import_error, attempts=3)
    return False, None


def get_google_sheets_service():
    """Get GoogleSheetsService instance if available"""
    success, path = _try_import_google_sheets()
    if success and GoogleSheetsService:
        return GoogleSheetsService
    return None


def get_fetch_schedule_data():
    """Get fetch_schedule_data function if available"""
    success, path = _try_import_google_sheets()
    if success and fetch_schedule_data:
        return fetch_schedule_data
    return None

