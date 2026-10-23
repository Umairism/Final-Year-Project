from datetime import datetime

def compute_device_presence(device, now=None, online_window_seconds=45):
    now = now or datetime.utcnow()
    if not device.connected:
        age = None if not device.last_heartbeat else max(0, int((now - device.last_heartbeat).total_seconds()))
        return {"presence_status": "disabled", "is_online": False, "last_seen_at": device.last_heartbeat, "last_seen_seconds_ago": age}
    if device.last_heartbeat is None:
        return {"presence_status": "never_seen", "is_online": False, "last_seen_at": None, "last_seen_seconds_ago": None}
    age = max(0, int((now - device.last_heartbeat).total_seconds()))
    online = age <= online_window_seconds
    return {"presence_status": "online" if online else "stale", "is_online": online, "last_seen_at": device.last_heartbeat, "last_seen_seconds_ago": age}
