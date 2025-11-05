#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Report Generator for CP-SAT Scheduling System
Generates comprehensive reports and analysis like the original run.py
"""

import pandas as pd
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

from .utils.logger import get_logger
from .schedule_helpers import (
    build_daily_analysis_report, 
    check_hard_constraints, 
    check_soft_constraints, 
    generate_soft_constraint_report,
    create_schedule_chart,
    generate_gap_analysis_report
)

logger = get_logger(__name__)

def generate_comprehensive_report(result: Dict[str, Any], provided: Dict[str, Any], output_dir: str = ".") -> Dict[str, str]:
    """
    Generate comprehensive reports like the original run.py
    
    Args:
        result: CP-SAT solving result
        provided: Input data
        output_dir: Directory to save reports
    
    Returns:
        Dictionary with report file paths
    """
    logger.info("Generating comprehensive reports...")
    
    report_files = {}
    
    try:
        # 1. Generate JSON summary report
        json_report_path = os.path.join(output_dir, "schedule_summary.json")
        generate_json_summary(result, provided, json_report_path)
        report_files["json_summary"] = json_report_path
        
        # 2. Generate text analysis report
        text_report_path = os.path.join(output_dir, "schedule_analysis.txt")
        generate_text_analysis(result, provided, text_report_path)
        report_files["text_analysis"] = text_report_path
        
        # 3. Generate detailed constraint report
        constraint_report_path = os.path.join(output_dir, "constraint_analysis.txt")
        generate_constraint_analysis(result, provided, constraint_report_path)
        report_files["constraint_analysis"] = constraint_report_path
        
        # 4. Generate employee workload report
        workload_report_path = os.path.join(output_dir, "employee_workload.txt")
        generate_employee_workload_report(result, provided, workload_report_path)
        report_files["employee_workload"] = workload_report_path
        
        # 5. Generate daily summary report
        daily_report_path = os.path.join(output_dir, "daily_summary.txt")
        generate_daily_summary_report(result, provided, daily_report_path)
        report_files["daily_summary"] = daily_report_path
        
        # 6. Generate chart if matplotlib is available
        try:
            chart_path = create_schedule_chart(result["finalAssignments"], provided, 
                                             os.path.join(output_dir, "schedule_chart.png"))
            if chart_path:
                report_files["chart"] = chart_path
        except Exception as e:
            logger.warning(f"Could not generate chart: {e}")
        
        logger.info(f"Generated {len(report_files)} report files")
        return report_files
        
    except Exception as e:
        logger.error(f"Error generating reports: {e}")
        return {}

def generate_json_summary(result: Dict[str, Any], provided: Dict[str, Any], output_path: str):
    """Generate JSON summary report"""
    try:
        summary = {
            "timestamp": datetime.now().isoformat(),
            "solver_status": result.get("summary", ""),
            "statistics": {
                "total_assignments": len(result.get("finalAssignments", [])),
                "total_demand": result.get("audit", {}).get("summary", {}).get("totalDemand", 0),
                "gap_count": result.get("audit", {}).get("summary", {}).get("gap", 0),
                "filled_positions": result.get("audit", {}).get("summary", {}).get("filled", 0)
            },
            "employees": {
                "total_count": len(provided.get("employees", [])),
                "employee_list": [
                    {
                        "id": emp.get("id"),
                        "name": emp.get("name"),
                        "skills": emp.get("skills", []),
                        "eligible_posts": emp.get("eligiblePosts", [])
                    }
                    for emp in provided.get("employees", [])
                ]
            },
            "schedule_period": {
                "start_date": min(provided.get("schedulePeriod", {}).get("dates", [])) if provided.get("schedulePeriod", {}).get("dates") else None,
                "end_date": max(provided.get("schedulePeriod", {}).get("dates", [])) if provided.get("schedulePeriod", {}).get("dates") else None,
                "total_days": len(provided.get("schedulePeriod", {}).get("dates", []))
            },
            "demand_summary": {
                "total_demand_entries": len(provided.get("weeklyDemand", [])),
                "unique_posts": list(set(d.get("post") for d in provided.get("weeklyDemand", []))),
                "shift_types": list(set(d.get("shiftAlias") for d in provided.get("weeklyDemand", [])))
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"JSON summary report saved to: {output_path}")
        
    except Exception as e:
        logger.error(f"Error generating JSON summary: {e}")

def generate_text_analysis(result: Dict[str, Any], provided: Dict[str, Any], output_path: str):
    """Generate comprehensive text analysis report"""
    try:
        lines = []
        lines.append("=" * 60)
        lines.append("CP-SAT 排班系統 - 綜合分析報告")
        lines.append("=" * 60)
        lines.append(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 1. 基本統計
        lines.append("【基本統計】")
        lines.append("-" * 30)
        total_assignments = len(result.get("finalAssignments", []))
        total_demand = result.get("audit", {}).get("summary", {}).get("totalDemand", 0)
        gap_count = result.get("audit", {}).get("summary", {}).get("gap", 0)
        filled = result.get("audit", {}).get("summary", {}).get("filled", 0)
        
        lines.append(f"總排班數: {total_assignments}")
        lines.append(f"總需求數: {total_demand}")
        lines.append(f"人力缺口: {gap_count}")
        lines.append(f"已填補: {filled}")
        lines.append(f"滿足率: {(filled/total_demand*100):.1f}%" if total_demand > 0 else "滿足率: N/A")
        lines.append("")
        
        # 2. 員工統計
        lines.append("【員工統計】")
        lines.append("-" * 30)
        employees = provided.get("employees", [])
        lines.append(f"總員工數: {len(employees)}")
        
        # 按技能分組
        skill_groups = defaultdict(list)
        for emp in employees:
            for skill in emp.get("skills", []):
                skill_groups[skill].append(emp.get("name", emp.get("id")))
        
        for skill, emp_list in skill_groups.items():
            lines.append(f"{skill}: {len(emp_list)} 人 ({', '.join(emp_list)})")
        lines.append("")
        
        # 3. 排班期間
        lines.append("【排班期間】")
        lines.append("-" * 30)
        dates = provided.get("schedulePeriod", {}).get("dates", [])
        if dates:
            lines.append(f"開始日期: {min(dates)}")
            lines.append(f"結束日期: {max(dates)}")
            lines.append(f"總天數: {len(dates)}")
        lines.append("")
        
        # 4. 班別統計
        lines.append("【班別統計】")
        lines.append("-" * 30)
        shift_counts = defaultdict(int)
        for assignment in result.get("finalAssignments", []):
            shift_counts[assignment.get("shift", "")] += 1
        
        for shift, count in sorted(shift_counts.items()):
            lines.append(f"{shift}班: {count} 次")
        lines.append("")
        
        # 5. 崗位統計
        lines.append("【崗位統計】")
        lines.append("-" * 30)
        post_counts = defaultdict(int)
        for assignment in result.get("finalAssignments", []):
            post_counts[assignment.get("post", "")] += 1
        
        for post, count in sorted(post_counts.items()):
            lines.append(f"{post}: {count} 次")
        lines.append("")
        
        # 6. 求解器狀態
        lines.append("【求解器狀態】")
        lines.append("-" * 30)
        lines.append(f"狀態: {result.get('summary', 'Unknown')}")
        lines.append("")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        logger.info(f"Text analysis report saved to: {output_path}")
        
    except Exception as e:
        logger.error(f"Error generating text analysis: {e}")

def generate_constraint_analysis(result: Dict[str, Any], provided: Dict[str, Any], output_path: str):
    """Generate constraint analysis report"""
    try:
        lines = []
        lines.append("=" * 60)
        lines.append("CP-SAT 排班系統 - 限制條件分析報告")
        lines.append("=" * 60)
        lines.append(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 硬性限制檢查
        lines.append("【硬性限制符合性檢查】")
        lines.append("-" * 40)
        hard_violations = check_hard_constraints(result.get("finalAssignments", []), provided)
        
        if not hard_violations:
            lines.append("✅ 所有硬性限制均符合")
        else:
            lines.append(f"❌ 發現 {len(hard_violations)} 項硬性限制違規:")
            for violation in hard_violations:
                lines.append(f"  - {violation.get('詳細資訊', '')} (日期: {violation.get('日期', '')}, 員工: {violation.get('員工ID', '')})")
        lines.append("")
        
        # 軟性限制檢查
        lines.append("【軟性限制符合性檢查】")
        lines.append("-" * 40)
        soft_violations = check_soft_constraints(result, provided, result.get("audit", {}).get("byKey", []))
        
        if not soft_violations:
            lines.append("✅ 所有軟性限制均符合")
        else:
            lines.append(f"⚠️ 發現 {len(soft_violations)} 項軟性限制違規:")
            violation_types = defaultdict(list)
            for violation in soft_violations:
                violation_types[violation.get("違規類型", "Unknown")].append(violation)
            
            for v_type, v_list in violation_types.items():
                lines.append(f"  {v_type}: {len(v_list)} 項")
                for violation in v_list[:3]:  # Show first 3 examples
                    lines.append(f"    - {violation.get('詳細資訊', '')}")
                if len(v_list) > 3:
                    lines.append(f"    ... 還有 {len(v_list) - 3} 項")
        lines.append("")
        
        # 自訂規則狀態
        lines.append("【自訂規則狀態】")
        lines.append("-" * 40)
        custom_rules = provided.get("customRules", [])
        if custom_rules:
            lines.append(f"已啟用 {len(custom_rules)} 項自訂規則:")
            for rule in custom_rules:
                lines.append(f"  - {rule.get('rule_type', '')}: 權重 {rule.get('weight', 0)}")
        else:
            lines.append("未啟用任何自訂規則")
        lines.append("")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        logger.info(f"Constraint analysis report saved to: {output_path}")
        
    except Exception as e:
        logger.error(f"Error generating constraint analysis: {e}")

def generate_employee_workload_report(result: Dict[str, Any], provided: Dict[str, Any], output_path: str):
    """Generate employee workload analysis report"""
    try:
        lines = []
        lines.append("=" * 60)
        lines.append("CP-SAT 排班系統 - 員工工作量分析報告")
        lines.append("=" * 60)
        lines.append(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 計算每個員工的工作量
        employee_workload = defaultdict(lambda: {
            "total_shifts": 0,
            "shifts_by_date": defaultdict(list),
            "shifts_by_shift_type": defaultdict(int),
            "shifts_by_post": defaultdict(int)
        })
        
        for assignment in result.get("finalAssignments", []):
            emp_id = assignment.get("employeeId", "")
            date = assignment.get("date", "")
            shift = assignment.get("shift", "")
            post = assignment.get("post", "")
            
            employee_workload[emp_id]["total_shifts"] += 1
            employee_workload[emp_id]["shifts_by_date"][date].append(f"{shift}班-{post}")
            employee_workload[emp_id]["shifts_by_shift_type"][shift] += 1
            employee_workload[emp_id]["shifts_by_post"][post] += 1
        
        # 員工資訊映射
        emp_info = {emp.get("id"): emp for emp in provided.get("employees", [])}
        
        lines.append("【員工工作量統計】")
        lines.append("-" * 40)
        
        # 按工作量排序
        sorted_employees = sorted(employee_workload.items(), 
                                key=lambda x: x[1]["total_shifts"], 
                                reverse=True)
        
        for emp_id, workload in sorted_employees:
            emp_name = emp_info.get(emp_id, {}).get("name", emp_id)
            lines.append(f"\n{emp_name} ({emp_id}):")
            lines.append(f"  總班數: {workload['total_shifts']}")
            
            # 班別分布
            shift_dist = workload["shifts_by_shift_type"]
            if shift_dist:
                lines.append(f"  班別分布: {', '.join([f'{k}班{v}次' for k, v in sorted(shift_dist.items())])}")
            
            # 崗位分布
            post_dist = workload["shifts_by_post"]
            if post_dist:
                lines.append(f"  崗位分布: {', '.join([f'{k}{v}次' for k, v in sorted(post_dist.items())])}")
            
            # 工作天數
            work_days = len(workload["shifts_by_date"])
            total_days = len(provided.get("schedulePeriod", {}).get("dates", []))
            lines.append(f"  工作天數: {work_days}/{total_days} 天")
        
        # 工作量統計摘要
        lines.append("\n【工作量統計摘要】")
        lines.append("-" * 40)
        total_shifts = [w["total_shifts"] for w in employee_workload.values()]
        if total_shifts:
            lines.append(f"平均班數: {sum(total_shifts)/len(total_shifts):.1f}")
            lines.append(f"最多班數: {max(total_shifts)}")
            lines.append(f"最少班數: {min(total_shifts)}")
            lines.append(f"班數差異: {max(total_shifts) - min(total_shifts)}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        logger.info(f"Employee workload report saved to: {output_path}")
        
    except Exception as e:
        logger.error(f"Error generating employee workload report: {e}")

def generate_daily_summary_report(result: Dict[str, Any], provided: Dict[str, Any], output_path: str):
    """Generate daily summary report"""
    try:
        lines = []
        lines.append("=" * 60)
        lines.append("CP-SAT 排班系統 - 每日摘要報告")
        lines.append("=" * 60)
        lines.append(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 使用現有的每日分析報告功能
        daily_report_lines = build_daily_analysis_report(provided, result.get("finalAssignments", []))
        
        lines.extend(daily_report_lines)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        logger.info(f"Daily summary report saved to: {output_path}")
        
    except Exception as e:
        logger.error(f"Error generating daily summary report: {e}")

def generate_all_reports(result: Dict[str, Any], provided: Dict[str, Any], output_dir: str = ".") -> Dict[str, str]:
    """
    Generate all reports and return file paths
    
    Args:
        result: CP-SAT solving result
        provided: Input data
        output_dir: Directory to save reports
    
    Returns:
        Dictionary with all report file paths
    """
    logger.info("Generating all reports...")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate comprehensive reports
    report_files = generate_comprehensive_report(result, provided, output_dir)
    
    # Add additional reports
    try:
        # Generate soft constraint detailed report
        soft_constraint_report_path = os.path.join(output_dir, "soft_constraint_detailed.txt")
        soft_violations = check_soft_constraints(result, provided, result.get("audit", {}).get("byKey", []))
        report_text = generate_soft_constraint_report(
            soft_violations, 
            result.get("audit", {}).get("summary", {}).get("totalDemand", 0),
            len(result.get("finalAssignments", [])),
            result, 
            provided, 
            result.get("audit", {}).get("byKey", [])
        )
        
        with open(soft_constraint_report_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        report_files["soft_constraint_detailed"] = soft_constraint_report_path
        
        # Generate gap analysis if there are gaps
        gaps = [item for item in result.get("audit", {}).get("byKey", []) if item.get("gap", 0) > 0]
        if gaps:
            gap_report_path = os.path.join(output_dir, "gap_analysis.txt")
            gap_report_lines = generate_gap_analysis_report(provided, gaps)
            
            with open(gap_report_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(gap_report_lines))
            
            report_files["gap_analysis"] = gap_report_path
        
    except Exception as e:
        logger.error(f"Error generating additional reports: {e}")
    
    logger.info(f"Generated {len(report_files)} report files in {output_dir}")
    return report_files

