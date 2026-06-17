"""
Database initialization and seeding script
"""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime
import uuid

from api.models.database.database import SessionLocal, init_db
from api.models.database.models import Patient, VitalSigns, Alert, Device, HealthStatus, AlertSeverity


def seed_data():
    """Seed the database with initial test data"""
    db = SessionLocal()
    
    try:
        print("\n🌱 Seeding database with test data...")
        
        # Create patients
        patient1 = Patient(
            id="P001",
            first_name="Muhammad",
            last_name="Umair",
            age=24,
            gender="Male",
            blood_type="O+",
            email="umair@healsense.com",
            phone="+92-300-1234567",
            created_at=datetime(2025, 1, 1, 10, 0, 0),
            updated_at=datetime.utcnow()
        )
        
        patient2 = Patient(
            id="P002",
            first_name="Sarah",
            last_name="Ahmed",
            age=32,
            gender="Female",
            blood_type="A+",
            email="sarah@healsense.com",
            phone="+92-300-9876543",
            created_at=datetime(2025, 6, 15, 14, 30, 0),
            updated_at=datetime.utcnow()
        )
        
        db.add_all([patient1, patient2])
        print("✅ Added 2 patients")
        
        # Create devices
        device1 = Device(
            device_id="DEV001",
            patient_id="P001",
            connected=True,
            battery_level=85,
            signal_strength=92,
            last_heartbeat=datetime.utcnow()
        )
        
        device2 = Device(
            device_id="DEV002",
            patient_id="P002",
            connected=True,
            battery_level=45,
            signal_strength=78,
            last_heartbeat=datetime.utcnow()
        )
        
        db.add_all([device1, device2])
        print("✅ Added 2 devices")
        
        # Create vital signs
        vital1 = VitalSigns(
            id="V001",
            patient_id="P001",
            device_id="DEV001",
            heart_rate=75.0,
            spo2=98.0,
            temperature=37.2,
            systolic_bp=120.0,
            diastolic_bp=80.0,
            respiratory_rate=16.0,
            timestamp=datetime.utcnow(),
            status=HealthStatus.NORMAL,
            risk_score=0.15
        )
        
        vital2 = VitalSigns(
            id="V002",
            patient_id="P002",
            device_id="DEV002",
            heart_rate=92.0,
            spo2=95.0,
            temperature=37.8,
            systolic_bp=135.0,
            diastolic_bp=88.0,
            respiratory_rate=18.0,
            timestamp=datetime.utcnow(),
            status=HealthStatus.WARNING,
            risk_score=0.45
        )
        
        db.add_all([vital1, vital2])
        print("✅ Added 2 vital signs records")
        
        # Create alert for patient 2
        alert1 = Alert(
            id="A001",
            patient_id="P002",
            message="Elevated heart rate detected",
            severity=AlertSeverity.MEDIUM,
            vital_type="heart_rate",
            timestamp=datetime.utcnow(),
            acknowledged=False,
            dismissed=False
        )
        
        db.add(alert1)
        print("✅ Added 1 alert")
        
        db.commit()
        print("\n✅ Database seeded successfully!\n")
        
        # Print summary
        print("📊 Database Summary:")
        print(f"   Patients: {db.query(Patient).count()}")
        print(f"   Devices: {db.query(Device).count()}")
        print(f"   Vital Signs: {db.query(VitalSigns).count()}")
        print(f"   Alerts: {db.query(Alert).count()}\n")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("="*60)
    print("  🗄️  HealSense Database Initialization")
    print("="*60)
    
    # Initialize database tables
    init_db()
    
    # Seed with test data
    seed_data()
    
    print("="*60)
    print("  🎉 Setup Complete!")
    print("="*60)
    print("\nYou can now start the backend server:")
    print("  python run.py\n")
