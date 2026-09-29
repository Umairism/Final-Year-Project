# Telemetry Ingestion API Specification

**Endpoint Path**: `POST /api/v1/telemetry`  
**Authentication**: `X-Device-API-Key` HTTP Header  
**Content-Type**: `application/json`  

---

## 1. Authentication Flow

```
ESP32 / Client Ingestion Request
  │
  ├─► Check X-Device-API-Key Header
  │      ├── Missing? ──► Return 401 Unauthorized ("Missing X-Device-API-Key header")
  │      └── Present? ──► Hash key via SHA-256
  │
  ├─► Query Database Device Record (`device_id`)
  │      ├── Not found? ──► Return 401 Unauthorized ("Unregistered device")
  │      ├── Disconnected? ──► Return 401 Unauthorized ("Device disabled")
  │      └── Hash mismatch? ──► Return 401 Unauthorized ("Invalid X-Device-API-Key")
  │
  └─► Authentication Success ──► Proceed to Telemetry Ingestion Pipeline
```

---

## 2. Request & Response Specifications

### HTTP Request Example
```http
POST /api/v1/telemetry HTTP/1.1
Host: api.healsense.io
Content-Type: application/json
X-Device-API-Key: secret_esp32_key_123

{
  "device_id": "ESP32_PATIENT_001",
  "patient_id": "p_12345",
  "heart_rate": 78.0,
  "spo2": 98.0,
  "temperature": 36.8,
  "systolic_bp": null,
  "diastolic_bp": null,
  "bp_source": "none",
  "delayed_sync": false,
  "timestamp": "2026-08-02T12:00:00Z"
}
```

### HTTP Response Example (`201 Created`)
```json
{
  "success": true,
  "message": "Telemetry ingested and evaluated successfully",
  "vital_id": "8f3d61b2-3c1a-4d2b-9e4f-01a2b3c4d5e6",
  "patient_id": "p_12345",
  "device_id": "ESP32_PATIENT_001",
  "status": "normal",
  "fused_decision": {
    "final_risk_level": "normal",
    "confidence_score": 1.0,
    "deterministic_flags": [],
    "ml_risk_probability": null,
    "fusion_method": "deterministic_only"
  },
  "explanation": null
}
```

---

## 3. Error Responses

| Status Code | Error Message / Reason | Solution |
| :--- | :--- | :--- |
| `401 Unauthorized` | `"Missing X-Device-API-Key header"` | Provide valid `X-Device-API-Key` header |
| `401 Unauthorized` | `"Invalid X-Device-API-Key"` | Verify hardware secret matches device record |
| `404 Not Found` | `"Patient p_99999 not found"` | Verify `patient_id` matches registered patient |
| `422 Validation Error` | Field validation constraint failed | Check JSON types and physiological ranges |
