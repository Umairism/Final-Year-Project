import argparse
from datetime import datetime, timedelta
from api.models.database import SessionLocal
from api.models.database.models import Patient, Device, VitalSigns, BpSource, HealthStatus

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--confirm-demo', action='store_true'); args=parser.parse_args()
    if not args.confirm_demo: raise SystemExit('Refusing demo seed: rerun with --confirm-demo')
    db=SessionLocal()
    try:
        if not db.query(Patient).filter_by(id='P001').first() or not db.query(Device).filter_by(device_id='DEV001').first(): raise SystemExit('Run init_db.py first to create P001 and DEV001')
        db.query(VitalSigns).filter(VitalSigns.patient_id=='P001', VitalSigns.data_origin=='simulated').delete(synchronize_session=False)
        now=datetime.utcnow(); rows=[]
        for i in range(23):
            f=i/22; bp=(122+4*(i//4),68+4*(i//4)) if i%4==0 else (None,None)
            rows.append(VitalSigns(id=f'DEMO{i+1:02d}',patient_id='P001',device_id='DEV001',heart_rate=round(82+36*f),spo2=round(98.8-4.8*f,1),temperature=round(36.8+1.6*f,1),systolic_bp=bp[0],diastolic_bp=bp[1],bp_source=BpSource.MANUAL_ENTRY if bp[0] else BpSource.NONE,delayed_sync=False,data_origin='simulated',timestamp=now-timedelta(hours=23-i),status=HealthStatus.NORMAL))
        db.add_all(rows); db.commit(); print(f'inserted row count: {len(rows)}'); print(f'first timestamp: {rows[0].timestamp.isoformat()}'); print(f'last timestamp: {rows[-1].timestamp.isoformat()}')
    finally: db.close()
if __name__=='__main__': main()
