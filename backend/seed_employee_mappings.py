#!/usr/bin/env python3
"""
Seed Employee Mappings
Creates EmployeeMapping records to link database userIDs with Google Sheets identifiers
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import User, ScheduleDefinition, EmployeeMapping
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_employee_mappings():
    """Seed employee mappings based on common patterns"""
    app = create_app()
    
    with app.app_context():
        logger.info("="*60)
        logger.info("Seeding Employee Mappings")
        logger.info("="*60)
        
        # Get all users
        users = User.query.all()
        logger.info(f"Found {len(users)} users")
        
        # Get default schedule definition
        schedule_def = ScheduleDefinition.query.filter_by(is_active=True).first()
        if not schedule_def:
            logger.error("No active schedule definition found. Cannot create mappings.")
            return
        
        logger.info(f"Using schedule definition: {schedule_def.scheduleName} ({schedule_def.scheduleDefID})")
        
        # Common mappings based on user patterns
        # user-004 -> E04, user-003 -> E03, etc.
        mappings_created = 0
        mappings_existing = 0
        
        for user in users:
            # Check if mapping already exists
            existing = EmployeeMapping.find_by_user(user.userID, schedule_def.scheduleDefID)
            if existing:
                logger.info(f"Mapping already exists for {user.username} ({user.userID})")
                mappings_existing += 1
                continue
            
            # Try to extract employee ID from userID (e.g., "user-004" -> "E04")
            # Pattern: user-004 -> E04, user-003 -> E03, etc.
            employee_id = None
            if user.userID.startswith("user-"):
                try:
                    # Extract number from user-004
                    num_part = user.userID.split("-")[-1]
                    # Convert "004" to "04" or "4" depending on format
                    if num_part.startswith("0"):
                        num_part = num_part[1:]  # "004" -> "04"
                    employee_id = f"E{num_part}"  # "04" -> "E04"
                except:
                    pass
            
            # Also try extracting from username if it matches pattern
            if not employee_id and user.username:
                # If username contains employee pattern (e.g., "employee" might map to E01)
                username_lower = user.username.lower()
                if "employee" in username_lower:
                    # Try to find corresponding employee number
                    # This is a heuristic - adjust based on actual data
                    employee_id = "E01"  # Default for "employee" user
            
            if employee_id:
                try:
                    mapping = EmployeeMapping(
                        userID=user.userID,
                        tenantID=user.tenantID,
                        sheets_identifier=employee_id,
                        sheets_name_id=employee_id,  # Will be updated when we find full format from sheet
                        schedule_def_id=schedule_def.scheduleDefID
                    )
                    db.session.add(mapping)
                    db.session.commit()
                    logger.info(f"✅ Created mapping: {user.username} ({user.userID}) -> {employee_id}")
                    mappings_created += 1
                except Exception as e:
                    logger.error(f"❌ Failed to create mapping for {user.username}: {e}")
                    db.session.rollback()
            else:
                logger.warning(f"⚠️  Could not determine employee ID for {user.username} ({user.userID})")
        
        logger.info("="*60)
        logger.info(f"Mappings created: {mappings_created}")
        logger.info(f"Mappings existing: {mappings_existing}")
        logger.info(f"Total users: {len(users)}")
        logger.info("="*60)
        
        # List all mappings
        all_mappings = EmployeeMapping.query.all()
        logger.info(f"\nAll Employee Mappings:")
        for mapping in all_mappings:
            logger.info(f"  - {mapping.user.username} ({mapping.userID}) -> {mapping.sheets_identifier}")

if __name__ == '__main__':
    try:
        seed_employee_mappings()
        logger.info("✅ Employee mappings seeded successfully!")
    except Exception as e:
        logger.error(f"❌ Error seeding mappings: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)





