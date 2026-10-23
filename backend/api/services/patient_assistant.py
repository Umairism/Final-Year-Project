import json
from datetime import datetime, timezone
from api.services.device_presence import compute_device_presence
from api.config import get_settings

def _age(a,b):
 if a.tzinfo is None: a=a.replace(tzinfo=timezone.utc)
 if b.tzinfo is None: b=b.replace(tzinfo=timezone.utc)
 return max(0,int((a-b).total_seconds()))
def build_patient_context(db, patient, now=None):
 now=now or datetime.utcnow(); rows=db.query(type(patient).vital_signs.property.mapper.class_).filter_by(patient_id=patient.id).order_by(type(patient).vital_signs.property.mapper.class_.timestamp.desc()).limit(200).all(); rows=list(reversed(rows)); latest=rows[-1] if rows else None
 if not latest: return None
 alerts=db.query(__import__('api.models.database.models',fromlist=['Alert']).Alert).filter_by(patient_id=patient.id,acknowledged=False,dismissed=False).order_by(__import__('api.models.database.models',fromlist=['Alert']).Alert.timestamp.desc()).limit(10).all()
 devices=db.query(__import__('api.models.database.models',fromlist=['Device']).Device).filter_by(patient_id=patient.id).all()
 def vital(r): return {k:getattr(r,k) for k in ['timestamp','heart_rate','spo2','temperature','systolic_bp','diastolic_bp','respiratory_rate','bp_source','data_origin','delayed_sync','status','risk_score','prediction_confidence','full_probability_distribution','model_version','device_id']}
 return {'patient':{k:getattr(patient,k) for k in ['age','gender','blood_type','diabetes','smoking_status','medications','past_conditions']},'latest':vital(latest),'data_as_of':latest.timestamp,'data_freshness_seconds':_age(now,latest.timestamp),'alerts':[{'severity':a.severity,'vital_type':a.vital_type,'message':a.message,'timestamp':a.timestamp} for a in alerts],'devices':[{'device_id':d.device_id,'device_type':d.device_type,'battery_level':d.battery_level,**compute_device_presence(d,online_window_seconds=get_settings().DEVICE_ONLINE_WINDOW_SECONDS)} for d in devices],'origin_counts':{o:sum(1 for r in rows if r.data_origin==o) for o in set(r.data_origin for r in rows)},'is_simulated_data':any(r.data_origin in ('simulated','seed') for r in rows),'rows':[vital(r) for r in rows]}
def build_prompt(context,message,conversation): return 'Use only this context. Decision support only, not diagnosis. Do not prescribe medication or treatment changes. Cite values and timestamps; state stale, missing, simulated, or seeded data. Backend risk decision is final. For critical values recommend immediate clinician/emergency escalation. Context:\n'+json.dumps(context,default=str)+'\nConversation:\n'+json.dumps(conversation[-6:],default=str)+'\nQuestion:\n'+message
