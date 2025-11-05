"""
Schedule task model for tracking scheduling jobs
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database.connection import Base


class ScheduleTask(Base):
    """Schedule task model"""
    __tablename__ = "schedule_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(String(255), unique=True, index=True, nullable=False)  # Celery task ID
    
    # Task configuration
    input_source = Column(String(50), nullable=False)  # 'excel' or 'google_sheets'
    input_config = Column(JSON, nullable=False)  # Input configuration
    output_destination = Column(String(50), nullable=False)  # 'excel' or 'google_sheets'
    output_config = Column(JSON, nullable=False)  # Output configuration
    
    # Task parameters
    time_limit = Column(Integer, default=90)  # Time limit in seconds
    debug_shift = Column(String(255), nullable=True)
    log_level = Column(String(20), default="INFO")
    
    # Task status
    status = Column(String(50), default="pending")  # pending, running, success, failed, cancelled
    progress = Column(Integer, default=0)  # Progress percentage (0-100)
    
    # Results
    result_data = Column(JSON, nullable=True)  # Task result data
    error_message = Column(Text, nullable=True)  # Error message if failed
    
    # File storage
    input_file_path = Column(String(500), nullable=True)  # Path to uploaded input file
    output_file_path = Column(String(500), nullable=True)  # Path to generated output file
    chart_file_path = Column(String(500), nullable=True)  # Path to generated chart
    
    # Google Sheets URLs
    input_sheet_url = Column(String(500), nullable=True)
    output_sheet_url = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="schedule_tasks")
    
    def __repr__(self):
        return f"<ScheduleTask(id={self.id}, task_id='{self.task_id}', status='{self.status}')>"
