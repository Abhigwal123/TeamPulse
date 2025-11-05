"""
Schedule task endpoints
"""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from ....database.connection import get_db
from ....models.user import User
from ....models.schedule_task import ScheduleTask
from ....schemas.schedule_task import (
    ScheduleTaskCreate, 
    ScheduleTask as ScheduleTaskSchema,
    ScheduleTaskResponse,
    TaskStatus
)
from ....api.dependencies import get_current_active_user
from ....tasks.schedule import process_schedule_task
from ....core.config import settings

router = APIRouter()


@router.post("/", response_model=ScheduleTaskResponse)
def create_schedule_task(
    task_data: ScheduleTaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new schedule task"""
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Create task record in database
    db_task = ScheduleTask(
        user_id=current_user.id,
        task_id=task_id,
        input_source=task_data.input_source,
        input_config=task_data.input_config,
        output_destination=task_data.output_destination,
        output_config=task_data.output_config,
        time_limit=task_data.time_limit,
        debug_shift=task_data.debug_shift,
        log_level=task_data.log_level,
        status="pending"
    )
    
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Dispatch task to Celery
    celery_task = process_schedule_task.delay(
        task_id=task_id,
        user_id=current_user.id,
        input_source=task_data.input_source,
        input_config=task_data.input_config,
        output_destination=task_data.output_destination,
        output_config=task_data.output_config,
        time_limit=task_data.time_limit,
        debug_shift=task_data.debug_shift,
        log_level=task_data.log_level
    )
    
    return ScheduleTaskResponse(
        task_id=task_id,
        message="Schedule task created successfully",
        status="pending"
    )


@router.post("/upload", response_model=ScheduleTaskResponse)
def create_schedule_task_with_upload(
    input_source: str = Form(...),
    output_destination: str = Form(...),
    output_config: str = Form(...),  # JSON string
    time_limit: int = Form(90),
    debug_shift: str = Form(None),
    log_level: str = Form("INFO"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a schedule task with file upload"""
    
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Excel files (.xlsx, .xls) are allowed"
        )
    
    # Validate file size
    if file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE} bytes"
        )
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Save uploaded file
    import json
    import os
    from datetime import datetime
    
    upload_dir = f"uploads/{current_user.id}"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_extension = os.path.splitext(file.filename)[1]
    file_path = f"{upload_dir}/{task_id}{file_extension}"
    
    with open(file_path, "wb") as buffer:
        content = file.file.read()
        buffer.write(content)
    
    # Parse output config
    try:
        output_config_dict = json.loads(output_config)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid output_config JSON format"
        )
    
    # Create task record in database
    db_task = ScheduleTask(
        user_id=current_user.id,
        task_id=task_id,
        input_source=input_source,
        input_config={"file_path": file_path},
        output_destination=output_destination,
        output_config=output_config_dict,
        time_limit=time_limit,
        debug_shift=debug_shift,
        log_level=log_level,
        status="pending",
        input_file_path=file_path
    )
    
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Dispatch task to Celery
    celery_task = process_schedule_task.delay(
        task_id=task_id,
        user_id=current_user.id,
        input_source=input_source,
        input_config={"file_path": file_path},
        output_destination=output_destination,
        output_config=output_config_dict,
        time_limit=time_limit,
        debug_shift=debug_shift,
        log_level=log_level
    )
    
    return ScheduleTaskResponse(
        task_id=task_id,
        message="Schedule task created successfully with file upload",
        status="pending"
    )


@router.get("/", response_model=List[ScheduleTaskSchema])
def get_user_tasks(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's schedule tasks"""
    tasks = db.query(ScheduleTask).filter(
        ScheduleTask.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    return tasks


@router.get("/{task_id}", response_model=TaskStatus)
def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get specific task status"""
    task = db.query(ScheduleTask).filter(
        ScheduleTask.task_id == task_id,
        ScheduleTask.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return TaskStatus(
        task_id=task.task_id,
        status=task.status,
        progress=task.progress,
        result_data=task.result_data,
        error_message=task.error_message,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at
    )


@router.delete("/{task_id}")
def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancel a running task"""
    task = db.query(ScheduleTask).filter(
        ScheduleTask.task_id == task_id,
        ScheduleTask.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    if task.status in ["completed", "failed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task cannot be cancelled"
        )
    
    # Update task status
    task.status = "cancelled"
    db.commit()
    
    # TODO: Cancel Celery task if running
    
    return {"message": "Task cancelled successfully"}
