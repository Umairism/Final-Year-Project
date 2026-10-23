from datetime import datetime, timedelta
from api.services.telemetry_service import resolve_data_origin
from api.services.device_presence import compute_device_presence

class Device:
    def __init__(self, connected=True, last_heartbeat=None): self.connected=connected; self.last_heartbeat=last_heartbeat

def test_resolve_data_origin():
    assert resolve_data_origin(None, False)=='device'; assert resolve_data_origin('device', False)=='device'; assert resolve_data_origin('simulated', True)=='simulated'; assert resolve_data_origin('simulated', False)=='device'

def test_presence_states():
    now=datetime.utcnow(); assert compute_device_presence(Device(True,now),now)['presence_status']=='online'; assert compute_device_presence(Device(True,now-timedelta(seconds=46)),now)['presence_status']=='stale'; assert compute_device_presence(Device(True,None),now)['presence_status']=='never_seen'; assert compute_device_presence(Device(False,now),now)['presence_status']=='disabled'
