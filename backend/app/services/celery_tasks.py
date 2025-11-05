import importlib.util
import importlib.machinery
import sys
from pathlib import Path
from app.extensions import init_celery
from flask import current_app
from app.services.google_io import get_default_input_url, get_default_output_url


def _load_phase1_run_schedule():
    # Import run_refactored.run_schedule_task from project root
    repo_root = Path(__file__).resolve().parents[2].parent
    repo_root_str = str(repo_root)
    # Ensure repo root takes precedence over current backend dir
    if sys.path and sys.path[0] == "":
        sys.path[0] = repo_root_str
    elif repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    module = importlib.import_module("run_refactored")
    return getattr(module, "run_schedule_task")


# Celery task bound at runtime via app factory; import task for registration
celery = None


def bind_celery(celery_app):
    global celery
    celery = celery_app
    
    # Register the schedule execution task
    register_schedule_execution_task(celery_app)

    @celery.task(bind=True, name="async_run_schedule")
    def async_run_schedule(self, input_url: str | None = None, output_url: str | None = None):
        self.update_state(state="STARTED")
        # Lazy import to avoid package name collisions at app startup
        original_app_module = sys.modules.get("app")
        try:
            # Prepare path
            repo_root = Path(__file__).resolve().parents[2].parent
            repo_root_str = str(repo_root)
            if sys.path and sys.path[0] == "":
                sys.path[0] = repo_root_str
            elif repo_root_str not in sys.path:
                sys.path.insert(0, repo_root_str)

            # Temporarily alias root app package
            from types import ModuleType
            phase1_pkg_name = "phase1"
            if phase1_pkg_name not in sys.modules:
                pkg_spec = importlib.machinery.ModuleSpec(phase1_pkg_name, loader=None, is_package=True)
                phase1_pkg = importlib.util.module_from_spec(pkg_spec)
                phase1_pkg.__path__ = [str(repo_root / "app")]  # type: ignore[attr-defined]
                sys.modules[phase1_pkg_name] = phase1_pkg
            # Point 'app' to phase1 during import
            sys.modules['app'] = sys.modules[phase1_pkg_name]

            mod = importlib.import_module("run_refactored")
            run_schedule_task = getattr(mod, "run_schedule_task")

            # Derive defaults from config when not provided
            cfg_in = current_app.config.get("GOOGLE_INPUT_URL")
            cfg_out = current_app.config.get("GOOGLE_OUTPUT_URL")
            sheet_id = current_app.config.get("GOOGLE_SHEET_ID")
            in_url = input_url or cfg_in or get_default_input_url(sheet_id)
            out_url = output_url or cfg_out or get_default_output_url(sheet_id)

            # Execute Phase 1 with Google Sheets mapping
            creds_path = current_app.config.get("GOOGLE_APPLICATION_CREDENTIALS", "service-account-creds.json")
            input_config = {"spreadsheet_url": in_url, "credentials_path": creds_path}
            output_config = {"spreadsheet_url": out_url, "credentials_path": creds_path}
            result = run_schedule_task(
                input_source="google_sheets",
                input_config=input_config,
                output_destination="google_sheets",
                output_config=output_config,
            )
        finally:
            # Restore original mapping if any
            if original_app_module is not None:
                sys.modules['app'] = original_app_module
            else:
                sys.modules.pop('app', None)

        self.update_state(state="SUCCESS", meta=result)
        return result

    return async_run_schedule


def register_schedule_execution_task(celery_app):
    """
    Register the execute_scheduling_task for manual schedule runs
    """
    from app import db
    from app.models import ScheduleJobLog
    from datetime import datetime
    import logging
    from app.services.schedule_executor import execute_schedule_task_sync
    
    logger = logging.getLogger(__name__)
    
    @celery_app.task(name="celery_tasks.execute_scheduling_task", bind=True)
    def execute_scheduling_task(self, schedule_config, job_log_id=None):
        """
        Execute a scheduling task via Celery
        
        Args:
            schedule_config: Dictionary with schedule configuration
            job_log_id: ID of the job log to update
        """
        try:
            logger.info(f"[INFO] Schedule run request received")
            logger.info(f"[INFO] Valid parameters: schedule_def_id={schedule_config.get('schedule_def_id')}, job_log_id={job_log_id}")
            logger.info(f"[INFO] Task submitted to Celery queue")
            
            # Update job log status
            if job_log_id:
                job_log = ScheduleJobLog.query.get(job_log_id)
                if job_log:
                    job_log.status = 'running'
                    job_log.startTime = datetime.utcnow()
                    db.session.commit()
            
            # Execute the schedule task (sync function handles the actual work)
            success = execute_schedule_task_sync(schedule_config, job_log_id)
            
            if success:
                logger.info(f"[INFO] Schedule job completed successfully")
                if job_log_id:
                    logger.info(f"[INFO] Execution log saved (job_id={job_log_id})")
            else:
                logger.error(f"[ERROR] Schedule job failed for job_log_id={job_log_id}")
            
            return {"success": success, "job_log_id": job_log_id}
            
        except Exception as e:
            logger.error(f"[ERROR] Schedule execution task failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Update job log to failed
            if job_log_id:
                try:
                    job_log = ScheduleJobLog.query.get(job_log_id)
                    if job_log:
                        job_log.status = 'failed'
                        job_log.endTime = datetime.utcnow()
                        job_log.error_message = str(e)
                        db.session.commit()
                except:
                    pass
            
            raise
    
    return execute_scheduling_task


def register_periodic_tasks(celery_app):
    """Register periodic tasks (including daily midnight auto-run)."""
    try:
        from celery.schedules import crontab
    except Exception:
        return

    @celery_app.on_after_finalize.connect
    def setup_periodic_tasks(sender, **kwargs):
        # Lightweight liveness run every 5 minutes (noop default runner)
        sender.add_periodic_task(300.0, trigger_sheet_run.s(), name="auto-run-schedule-5m")
        # Daily auto-run at midnight (server local time)
        sender.add_periodic_task(
            crontab(minute=0, hour=0),
            daily_run_all_schedules.s(),
            name="daily-run-all-schedules-midnight",
        )
        # Daily Google Sheets refresh at 1 AM (validate all sheets are accessible)
        sender.add_periodic_task(
            crontab(minute=0, hour=1),
            refresh_google_sheets_data.s(),
            name="daily-refresh-google-sheets",
        )

    @celery_app.task(name="trigger_sheet_run")
    def trigger_sheet_run():
        # Fire and forget a new run using defaults
        celery_app.send_task("async_run_schedule", args=[None, None])

    @celery_app.task(name="daily_run_all_schedules")
    def daily_run_all_schedules():
        """Enumerate all tenants and schedule definitions and enqueue runs."""
        try:
            from flask import current_app as flask_app
            from app import db
            from app.models import Tenant, ScheduleDefinition, ScheduleJobLog, SchedulePermission, User
            from datetime import datetime

            # Iterate tenants
            tenants = db.session.query(Tenant).all()
            for tenant in tenants:
                # Fetch schedule definitions for tenant
                defs = db.session.query(ScheduleDefinition).filter_by(tenantID=tenant.tenantID, is_active=True).all()
                for sd in defs:
                    # Pick any user with permission to run (prefer ScheduleManager)
                    perm = db.session.query(SchedulePermission).filter_by(
                        tenantID=tenant.tenantID, scheduleDefID=sd.scheduleDefID, canRunJob=True, is_active=True
                    ).first()
                    run_by_user_id = perm.userID if perm else None
                    # Fallback to any active user in tenant
                    if not run_by_user_id:
                        u = db.session.query(User).filter_by(tenantID=tenant.tenantID, status='active').first()
                        run_by_user_id = u.userID if u else None

                    # Create job log
                    job_log = ScheduleJobLog(
                        tenantID=tenant.tenantID,
                        scheduleDefID=sd.scheduleDefID,
                        runByUserID=run_by_user_id or "system",
                        status='pending',
                        metadata={
                            'parameters': {},
                            'priority': 'normal',
                            'requested_at': datetime.utcnow().isoformat(),
                            'trigger': 'daily-auto-run'
                        }
                    )
                    db.session.add(job_log)
                    db.session.commit()

                    # Enqueue Celery task for this schedule
                    schedule_config = {
                        'input_source': 'google_sheets',
                        'input_config': {
                            'spreadsheet_url': sd.paramsSheetURL,
                            'credentials_path': flask_app.config.get('GOOGLE_APPLICATION_CREDENTIALS', 'service-account-creds.json')
                        },
                        'output_destination': 'google_sheets',
                        'output_config': {
                            'spreadsheet_url': sd.resultsSheetURL,
                            'credentials_path': flask_app.config.get('GOOGLE_APPLICATION_CREDENTIALS', 'service-account-creds.json')
                        },
                        'schedule_def_id': sd.scheduleDefID,
                        'job_log_id': job_log.logID
                    }
                    celery_app.send_task(
                        'celery_tasks.execute_scheduling_task',
                        args=[schedule_config],
                        kwargs={'job_log_id': job_log.logID}
                    )
        except Exception:  # best-effort; log and continue
            import logging, traceback
            logging.getLogger(__name__).error("Daily auto-run failed:\n" + traceback.format_exc())

    @celery_app.task(name="refresh_google_sheets_data")
    def refresh_google_sheets_data():
        """
        Daily task to refresh/validate Google Sheets data for all active schedule definitions.
        This ensures all sheets are accessible and credentials are valid.
        """
        try:
            from flask import current_app as flask_app
            from app import db
            from app.models import ScheduleDefinition
            import logging
            import sys
            import os
            
            logger = logging.getLogger(__name__)
            logger.info("Starting daily Google Sheets refresh...")
            
            # Import GoogleSheetsService
            project_root = Path(__file__).resolve().parents[2].parent
            project_root_str = str(project_root)
            if project_root_str not in sys.path:
                sys.path.insert(0, project_root_str)
            
            try:
                from app.services.google_sheets.service import GoogleSheetsService
            except ImportError:
                # Try alternative path
                sys.path.insert(0, os.path.join(project_root_str, 'app'))
                from services.google_sheets.service import GoogleSheetsService
            
            # Get credentials path
            creds_path = flask_app.config.get('GOOGLE_APPLICATION_CREDENTIALS', 'service-account-creds.json')
            service = GoogleSheetsService(creds_path)
            
            # Get all active schedule definitions
            with flask_app.app_context():
                schedule_defs = db.session.query(ScheduleDefinition).filter_by(is_active=True).all()
                
                refresh_results = {
                    "total": len(schedule_defs),
                    "success": 0,
                    "failed": 0,
                    "details": []
                }
                
                for sd in schedule_defs:
                    try:
                        # Validate and refresh all 6 sheets for this schedule definition
                        main_spreadsheet_url = sd.paramsSheetURL
                        results_spreadsheet_url = sd.resultsSheetURL
                        
                        # Read all sheets to validate they're accessible
                        params_data = service.read_parameters_sheet(main_spreadsheet_url)
                        employee_data = service.read_employee_sheet(main_spreadsheet_url)
                        preferences_data = service.read_preferences_sheet(main_spreadsheet_url)
                        preschedule_data = service.read_preschedule_sheet(sd.prefsSheetURL or main_spreadsheet_url)
                        designation_flow_data = service.read_designation_flow_sheet(main_spreadsheet_url)
                        final_output_data = service.read_final_output_sheet(results_spreadsheet_url)
                        
                        # Count successful reads
                        success_count = sum([
                            params_data.get("success", False),
                            employee_data.get("success", False),
                            preferences_data.get("success", False),
                            preschedule_data.get("success", False),
                            designation_flow_data.get("success", False),
                            final_output_data.get("success", False)
                        ])
                        
                        if success_count >= 4:  # At least Parameters and Pre-Schedule must succeed
                            refresh_results["success"] += 1
                            logger.info(f"✓ Refreshed sheets for schedule: {sd.scheduleName} ({sd.scheduleDefID})")
                        else:
                            refresh_results["failed"] += 1
                            logger.warning(f"✗ Some sheets failed for schedule: {sd.scheduleName} ({sd.scheduleDefID})")
                        
                        refresh_results["details"].append({
                            "schedule_def_id": sd.scheduleDefID,
                            "schedule_name": sd.scheduleName,
                            "success": success_count >= 4,
                            "sheets_read": success_count,
                            "sheets_total": 6
                        })
                        
                    except Exception as e:
                        refresh_results["failed"] += 1
                        logger.error(f"Error refreshing sheets for schedule {sd.scheduleDefID}: {e}")
                        refresh_results["details"].append({
                            "schedule_def_id": sd.scheduleDefID,
                            "schedule_name": sd.scheduleName,
                            "success": False,
                            "error": str(e)
                        })
                
                logger.info(f"Daily Google Sheets refresh completed: {refresh_results['success']}/{refresh_results['total']} succeeded")
                return refresh_results
                
        except Exception as e:
            import logging, traceback
            logger = logging.getLogger(__name__)
            logger.error(f"Daily Google Sheets refresh failed:\n{traceback.format_exc()}")
            return {"success": False, "error": str(e)}


