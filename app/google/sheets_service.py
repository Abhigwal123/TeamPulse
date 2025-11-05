"""
Google Sheets Service - Sync functions for Flask backend integration
Provides sync_from_google and sync_to_google functions for Google Sheets integration
"""
import os
import logging
from typing import Dict, Any, Optional, List
import pandas as pd

logger = logging.getLogger(__name__)

# Try to import gspread, but provide fallback if not available
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    logger.warning("gspread not available - Google Sheets functionality will be limited")


def _get_credentials(credentials_path: Optional[str] = None) -> Optional[Any]:
    """Get Google service account credentials"""
    if not GSPREAD_AVAILABLE:
        return None
    
    creds_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "service-account-creds.json")
    
    if not os.path.exists(creds_path):
        logger.error(f"Google credentials file not found: {creds_path}")
        raise FileNotFoundError(f"Google credentials file not found: {creds_path}. Please ensure service-account-creds.json exists or set GOOGLE_APPLICATION_CREDENTIALS environment variable.")
    
    try:
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_file(creds_path, scopes=scope)
        return creds
    except Exception as e:
        logger.error(f"Error loading Google credentials: {e}")
        raise


def sync_from_google(
    spreadsheet_url: str,
    sheet_name: Optional[str] = None,
    credentials_path: Optional[str] = None,
    range_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sync data from Google Sheets
    
    Args:
        spreadsheet_url: Full URL or spreadsheet ID
        sheet_name: Optional sheet/tab name (if None, uses first sheet)
        credentials_path: Path to service account JSON file
        range_name: Optional range (e.g., 'A1:Z100')
    
    Returns:
        Dictionary with 'success', 'data', and optionally 'error' keys
    """
    if not GSPREAD_AVAILABLE:
        return {
            "success": False,
            "error": "gspread library not installed. Install with: pip install gspread google-auth",
            "data": None
        }
    
    try:
        creds = _get_credentials(credentials_path)
        if not creds:
            return {
                "success": False,
                "error": "Failed to load Google credentials",
                "data": None
            }
        
        gc = gspread.authorize(creds)
        
        # Extract spreadsheet ID from URL if needed
        if '/spreadsheets/d/' in spreadsheet_url:
            spreadsheet_id = spreadsheet_url.split('/spreadsheets/d/')[1].split('/')[0]
        else:
            spreadsheet_id = spreadsheet_url
        
        # Open spreadsheet
        spreadsheet = gc.open_by_key(spreadsheet_id)
        
        # Get worksheet
        if sheet_name:
            worksheet = spreadsheet.worksheet(sheet_name)
        else:
            worksheet = spreadsheet.sheet1
        
        # Read data
        if range_name:
            values = worksheet.get(range_name)
        else:
            values = worksheet.get_all_values()
        
        # Convert to DataFrame if we have data
        if values:
            df = pd.DataFrame(values[1:], columns=values[0])
        else:
            df = pd.DataFrame()
        
        logger.info(f"Successfully synced {len(df)} rows from Google Sheet: {spreadsheet.title}")
        
        return {
            "success": True,
            "data": df.to_dict('records') if not df.empty else [],
            "rows": len(df),
            "columns": list(df.columns) if not df.empty else []
        }
    
    except FileNotFoundError as e:
        return {
            "success": False,
            "error": str(e),
            "data": None
        }
    except Exception as e:
        logger.error(f"Error syncing from Google Sheets: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": None
        }


def sync_to_google(
    data: List[Dict[str, Any]] or pd.DataFrame,
    spreadsheet_url: str,
    sheet_name: Optional[str] = None,
    credentials_path: Optional[str] = None,
    clear_existing: bool = True
) -> Dict[str, Any]:
    """
    Sync data to Google Sheets
    
    Args:
        data: List of dictionaries or pandas DataFrame to write
        spreadsheet_url: Full URL or spreadsheet ID
        sheet_name: Optional sheet/tab name (creates new if doesn't exist)
        credentials_path: Path to service account JSON file
        clear_existing: Whether to clear existing data before writing
    
    Returns:
        Dictionary with 'success' and optionally 'error' keys
    """
    if not GSPREAD_AVAILABLE:
        return {
            "success": False,
            "error": "gspread library not installed. Install with: pip install gspread google-auth"
        }
    
    try:
        creds = _get_credentials(credentials_path)
        if not creds:
            return {
                "success": False,
                "error": "Failed to load Google credentials"
            }
        
        gc = gspread.authorize(creds)
        
        # Extract spreadsheet ID from URL if needed
        if '/spreadsheets/d/' in spreadsheet_url:
            spreadsheet_id = spreadsheet_url.split('/spreadsheets/d/')[1].split('/')[0]
        else:
            spreadsheet_id = spreadsheet_url
        
        # Open spreadsheet
        spreadsheet = gc.open_by_key(spreadsheet_id)
        
        # Get or create worksheet
        if sheet_name:
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
            except gspread.exceptions.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=100, cols=20)
        else:
            worksheet = spreadsheet.sheet1
        
        # Convert data to list of lists
        if isinstance(data, pd.DataFrame):
            values = [data.columns.tolist()] + data.values.tolist()
        elif isinstance(data, list) and len(data) > 0:
            # Assume list of dicts
            if isinstance(data[0], dict):
                columns = list(data[0].keys())
                values = [columns] + [[row.get(col, '') for col in columns] for row in data]
            else:
                values = data
        else:
            values = []
        
        # Clear existing if requested
        if clear_existing and worksheet.row_count > 0:
            worksheet.clear()
        
        # Write data
        if values:
            worksheet.update(values, value_input_option='USER_ENTERED')
        
        logger.info(f"Successfully synced {len(values) - 1 if values else 0} rows to Google Sheet: {worksheet.title}")
        
        return {
            "success": True,
            "rows_written": len(values) - 1 if values else 0,
            "sheet_name": worksheet.title
        }
    
    except FileNotFoundError as e:
        return {
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Error syncing to Google Sheets: {e}")
        return {
            "success": False,
            "error": str(e)
        }


