"""
Google Sheets Client - Direct access to Google Sheets for QA testing
Provides direct gspread access to read sheets for comparison testing
"""
import os
import logging
from typing import Dict, Any, Optional, List
import pandas as pd

logger = logging.getLogger(__name__)

# Try to import gspread
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    logger.error("gspread not available - Install with: pip install gspread google-auth")


class GoogleSheetsClient:
    """
    Direct Google Sheets client for QA testing
    Reads sheets directly from Google Sheets API (source of truth)
    """
    
    def __init__(self, credentials_path: Optional[str] = None, spreadsheet_id: Optional[str] = None):
        """
        Initialize Google Sheets Client
        
        Args:
            credentials_path: Path to service account JSON file
            spreadsheet_id: Google Sheets spreadsheet ID
        """
        if not GSPREAD_AVAILABLE:
            raise ImportError("gspread library not installed. Install with: pip install gspread google-auth")
        
        self.credentials_path = credentials_path or os.getenv(
            "GOOGLE_SHEETS_CREDENTIALS_PATH",
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "service-account-creds.json")
        )
        self.spreadsheet_id = spreadsheet_id
        self._credentials = None
        self._client = None
        self._spreadsheet = None
    
    def _get_credentials(self):
        """Get Google service account credentials"""
        if self._credentials:
            return self._credentials
        
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(
                f"Google credentials file not found: {self.credentials_path}. "
                "Please ensure service-account-creds.json exists or set GOOGLE_SHEETS_CREDENTIALS_PATH environment variable."
            )
        
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/spreadsheets'
            ]
            self._credentials = Credentials.from_service_account_file(
                self.credentials_path, 
                scopes=scope
            )
            return self._credentials
        except Exception as e:
            logger.error(f"Error loading Google credentials: {e}")
            raise
    
    def _get_client(self):
        """Get authorized gspread client"""
        if self._client:
            return self._client
        
        creds = self._get_credentials()
        self._client = gspread.authorize(creds)
        return self._client
    
    def _get_spreadsheet(self):
        """Get spreadsheet object"""
        if self._spreadsheet:
            return self._spreadsheet
        
        if not self.spreadsheet_id:
            raise ValueError("spreadsheet_id must be provided")
        
        client = self._get_client()
        try:
            self._spreadsheet = client.open_by_key(self.spreadsheet_id)
            logger.info(f"Connected to spreadsheet: {self._spreadsheet.title}")
            return self._spreadsheet
        except Exception as e:
            logger.error(f"Error opening spreadsheet {self.spreadsheet_id}: {e}")
            raise
    
    def list_all_sheets(self) -> List[str]:
        """
        List all sheet names in the spreadsheet
        
        Returns:
            List of sheet names
        """
        spreadsheet = self._get_spreadsheet()
        worksheets = spreadsheet.worksheets()
        return [ws.title for ws in worksheets]
    
    def read_sheet(self, sheet_name: str, as_dataframe: bool = True) -> Dict[str, Any]:
        """
        Read a specific sheet from the spreadsheet
        
        Args:
            sheet_name: Name of the sheet to read
            as_dataframe: If True, return as pandas DataFrame; if False, return raw list of lists
        
        Returns:
            Dictionary with:
            - success: bool
            - data: DataFrame or list of lists
            - rows: int (number of data rows, excluding header)
            - columns: list of column names (if DataFrame)
            - error: str (if failed)
        """
        try:
            spreadsheet = self._get_spreadsheet()
            worksheet = spreadsheet.worksheet(sheet_name)
            
            # Get all values
            values = worksheet.get_all_values()
            
            if not values or len(values) == 0:
                return {
                    "success": True,
                    "data": pd.DataFrame() if as_dataframe else [],
                    "rows": 0,
                    "columns": [],
                    "sheet_name": sheet_name
                }
            
            # Remove empty rows
            values = [row for row in values if any(cell.strip() for cell in row)]
            
            if len(values) == 0:
                return {
                    "success": True,
                    "data": pd.DataFrame() if as_dataframe else [],
                    "rows": 0,
                    "columns": [],
                    "sheet_name": sheet_name
                }
            
            # First row is header
            header = values[0]
            data_rows = values[1:]
            
            if as_dataframe:
                # Create DataFrame
                df = pd.DataFrame(data_rows, columns=header)
                # Remove rows where all columns are empty/NaN
                df = df.dropna(how='all')
                # Convert empty strings to NaN for consistency
                df = df.replace('', pd.NA)
                
                logger.info(f"Read {len(df)} rows from sheet '{sheet_name}' with columns: {list(df.columns)}")
                
                return {
                    "success": True,
                    "data": df,
                    "rows": len(df),
                    "columns": list(df.columns),
                    "sheet_name": sheet_name,
                    "raw_data": values  # Keep raw data for comparison
                }
            else:
                return {
                    "success": True,
                    "data": data_rows,
                    "rows": len(data_rows),
                    "columns": header,
                    "sheet_name": sheet_name,
                    "raw_data": values
                }
        
        except gspread.exceptions.WorksheetNotFound:
            error_msg = f"Sheet '{sheet_name}' not found in spreadsheet"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "data": None,
                "rows": 0,
                "columns": [],
                "sheet_name": sheet_name
            }
        except Exception as e:
            error_msg = f"Error reading sheet '{sheet_name}': {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "data": None,
                "rows": 0,
                "columns": [],
                "sheet_name": sheet_name
            }
    
    def read_multiple_sheets(self, sheet_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Read multiple sheets at once
        
        Args:
            sheet_names: List of sheet names to read
        
        Returns:
            Dictionary mapping sheet names to their data
        """
        results = {}
        for sheet_name in sheet_names:
            results[sheet_name] = self.read_sheet(sheet_name)
        return results


def extract_spreadsheet_id(url_or_id: str) -> str:
    """
    Extract spreadsheet ID from URL or return as-is if already an ID
    
    Args:
        url_or_id: Full Google Sheets URL or spreadsheet ID
    
    Returns:
        Spreadsheet ID
    """
    if '/spreadsheets/d/' in url_or_id:
        # Extract ID from URL
        parts = url_or_id.split('/spreadsheets/d/')[1].split('/')
        return parts[0]
    elif '/d/' in url_or_id:
        # Alternative URL format
        parts = url_or_id.split('/d/')[1].split('/')
        return parts[0]
    else:
        # Assume it's already an ID
        return url_or_id



