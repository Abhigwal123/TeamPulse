#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CP-SAT Scheduling System (Refactored)
Main entry point for the scheduling system with Google Sheets integration
"""

import argparse
import json
import os
import sys
import pandas as pd
from typing import Dict, Any, Optional

# Import our refactored modules
from app.data_provider import create_data_provider
from app.data_writer import create_data_writer, write_all_results_to_excel, write_all_results_to_google_sheets
from app.schedule_cpsat import process_input_data, solve_cpsat
from app.schedule_helpers import (
    build_rows, build_daily_analysis_report, check_hard_constraints, 
    check_soft_constraints, generate_soft_constraint_report, 
    create_schedule_chart, debug_schedule
)
from app.utils.logger import setup_logging, get_logger

# Initialize logger
logger = get_logger(__name__)


def run_schedule_task(
    input_source: str,
    input_config: Dict[str, Any],
    output_destination: str,
    output_config: Dict[str, Any],
    time_limit: float = 90.0,
    debug_shift: Optional[str] = None,
    log_level: str = "INFO"
) -> Dict[str, Any]:
    """
    Main function to run the scheduling task
    
    Args:
        input_source: 'excel' or 'google_sheets'
        input_config: Configuration for input source
        output_destination: 'excel' or 'google_sheets'
        output_config: Configuration for output destination
        time_limit: Time limit for solving in seconds
        debug_shift: Optional debug shift in format "YYYY/MM/DD,班別,崗位"
        log_level: Logging level
    
    Returns:
        Dictionary containing results and status
    """
    
    # Setup logging with file handler
    setup_logging(level=log_level, log_file="logs/system.log")
    logger = get_logger(__name__)
    logger.info("Starting CP-SAT scheduling task...")
    
    try:
        # Step 1: Create data provider and load input data
        logger.info(f"Loading data from {input_source}...")
        data_provider = create_data_provider(input_source, **input_config)
        provided = process_input_data(data_provider)
        logger.info("Input data processed successfully")
        
        # Debug mode - analyze specific shift
        if debug_shift:
            try:
                parts = debug_shift.split(',')
                if len(parts) != 3:
                    logger.error("Debug shift format must be YYYY/MM/DD,班別,崗位")
                    return {"error": "Invalid debug shift format"}
                debug_schedule(provided, parts[0], parts[1], parts[2])
                return {"status": "debug_complete"}
            except Exception as e:
                logger.error(f"Error during debug analysis: {e}")
                return {"error": str(e)}
        
        # Step 2: Solve the scheduling problem
        logger.info("Starting CP-SAT solving...")
        result = solve_cpsat(provided, time_limit=time_limit)
        logger.info("CP-SAT solving completed")
        
        # Step 3: Generate reports and analysis
        logger.info("Generating reports and analysis...")
        
        # Build the final schedule grid and get complete assignments
        rows_for_sheet, complete_assignments = build_rows(result["finalAssignments"], provided)
        
        # Generate daily analysis report
        detailed_report_lines = build_daily_analysis_report(provided, complete_assignments)
        detailed_report_df = pd.DataFrame(detailed_report_lines, columns=['每日分析'])
        
        # Perform compliance checks
        hard_violations = check_hard_constraints(complete_assignments, provided)
        soft_violations = check_soft_constraints(result, provided, result["audit"]["byKey"])
        
        # Generate gap analysis if gaps exist
        gaps = [item for item in result["audit"]["byKey"] if item.get("gap", 0) > 0]
        gap_analysis_df = pd.DataFrame()
        if gaps:
            from app.schedule_helpers import generate_gap_analysis_report
            gap_report_lines = generate_gap_analysis_report(provided, gaps)
            gap_analysis_df = pd.DataFrame(gap_report_lines, columns=['人力缺口分析與建議'])
        
        # Generate analysis report
        report_text = generate_soft_constraint_report(
            soft_violations, 
            result["audit"]["summary"]["totalDemand"], 
            len(complete_assignments), 
            result, 
            provided, 
            result["audit"]["byKey"]
        )
        
        # Generate chart
        chart_path = create_schedule_chart(complete_assignments, provided)
        
        # Step 4: Prepare results for output
        results_data = {
            "schedule_results": pd.DataFrame(rows_for_sheet),
            "audit_details": pd.DataFrame(result["audit"]["byKey"]),
            "hard_constraints": pd.DataFrame(hard_violations),
            "soft_constraints": pd.DataFrame(soft_violations),
            "daily_analysis": detailed_report_df,
            "analysis_report": report_text,
            "chart_path": chart_path
        }
        
        if not gap_analysis_df.empty:
            results_data["gap_analysis"] = gap_analysis_df
        
        # Step 5: Write results to output destination
        logger.info(f"Writing results to {output_destination}...")
        
        if output_destination.lower() == 'excel':
            success = write_all_results_to_excel(output_config['output_path'], results_data)
        elif output_destination.lower() in ['google_sheets', 'google', 'sheets']:
            success = write_all_results_to_google_sheets(
                output_config['spreadsheet_url'], 
                results_data, 
                output_config.get('credentials_path')
            )
        else:
            raise ValueError(f"Unsupported output destination: {output_destination}")
        
        if not success:
            logger.error("Failed to write results")
            return {"error": "Failed to write results"}
        
        logger.info("Scheduling task completed successfully")
        
        return {
            "status": "success",
            "summary": result.get("summary", ""),
            "assignments_count": len(complete_assignments),
            "total_demand": result["audit"]["summary"]["totalDemand"],
            "gap_count": result["audit"]["summary"]["gap"],
            "hard_violations_count": len(hard_violations),
            "soft_violations_count": len(soft_violations)
        }
        
    except Exception as e:
        logger.error(f"Error during scheduling task: {e}")
        return {"error": str(e)}


def main():
    """
    Command-line interface for the refactored scheduling system
    """
    parser = argparse.ArgumentParser(description="CP-SAT Scheduling System (Refactored)")
    
    # Input configuration
    parser.add_argument("--input-type", choices=['excel', 'google_sheets'], required=True,
                       help="Input data source type")
    parser.add_argument("--input-file", help="Input Excel file path (for excel input)")
    parser.add_argument("--input-sheet-url", help="Input Google Sheet URL (for google_sheets input)")
    parser.add_argument("--credentials", default="service-account-creds.json",
                       help="Path to Google service account credentials file")
    
    # Output configuration
    parser.add_argument("--output-type", choices=['excel', 'google_sheets'], required=True,
                       help="Output destination type")
    parser.add_argument("--output-file", help="Output Excel file path (for excel output)")
    parser.add_argument("--output-sheet-url", help="Output Google Sheet URL (for google_sheets output)")
    
    # Scheduling parameters
    parser.add_argument("--time-limit", type=float, default=90.0,
                       help="Time limit for solving in seconds (default: 90)")
    parser.add_argument("--debug-shift", help="Debug specific shift: YYYY/MM/DD,班別,崗位")
    parser.add_argument("--log-level", default="INFO", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help="Logging level (default: INFO)")
    
    args = parser.parse_args()
    
    # Validate input configuration
    if args.input_type == 'excel':
        if not args.input_file:
            print("Error: --input-file is required for excel input type")
            sys.exit(1)
        input_config = {"file_path": args.input_file}
    elif args.input_type == 'google_sheets':
        if not args.input_sheet_url:
            print("Error: --input-sheet-url is required for google_sheets input type")
            sys.exit(1)
        input_config = {
            "spreadsheet_url": args.input_sheet_url,
            "credentials_path": args.credentials
        }
    
    # Validate output configuration
    if args.output_type == 'excel':
        if not args.output_file:
            print("Error: --output-file is required for excel output type")
            sys.exit(1)
        output_config = {"output_path": args.output_file}
    elif args.output_type == 'google_sheets':
        if not args.output_sheet_url:
            print("Error: --output-sheet-url is required for google_sheets output type")
            sys.exit(1)
        output_config = {
            "spreadsheet_url": args.output_sheet_url,
            "credentials_path": args.credentials
        }
    
    # Run the scheduling task
    result = run_schedule_task(
        input_source=args.input_type,
        input_config=input_config,
        output_destination=args.output_type,
        output_config=output_config,
        time_limit=args.time_limit,
        debug_shift=args.debug_shift,
        log_level=args.log_level
    )
    
    # Output result
    if result.get("error"):
        print(f"Error: {result['error']}")
        sys.exit(1)
    elif result.get("status") == "debug_complete":
        print("Debug analysis completed")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
