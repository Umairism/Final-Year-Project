#include "telemetry_client.h"

TelemetryClient::TelemetryClient(
    const char* serverUrl,
    const char* apiKey,
    const char* deviceId,
    const char* patientId
) : serverUrl(serverUrl), apiKey(apiKey), deviceId(deviceId), patientId(patientId) {}

bool TelemetryClient::begin() {
    storage.begin();
    wifi.begin();
    return true;
}

String TelemetryClient::serializePayload(const TelemetryRecord& record) {
    String json = "{";
    json += "\"device_id\":\"" + deviceId + "\",";
    json += "\"patient_id\":\"" + patientId + "\",";
    json += "\"heart_rate\":" + String(record.heart_rate) + ",";
    json += "\"spo2\":" + String(record.spo2) + ",";
    json += "\"temperature\":" + String(record.temperature) + ",";
    
    if (record.systolic_bp > 0) {
        json += "\"systolic_bp\":" + String(record.systolic_bp) + ",";
        json += "\"diastolic_bp\":" + String(record.diastolic_bp) + ",";
        json += "\"bp_source\":\"ble_cuff\",";
    } else {
        json += "\"systolic_bp\":null,";
        json += "\"diastolic_bp\":null,";
        json += "\"bp_source\":\"none\",";
    }
    
    json += "\"delayed_sync\":" + String(record.delayed_sync ? "true" : "false");
    json += "}";
    return json;
}

bool TelemetryClient::sendTelemetry(const TelemetryRecord& record) {
    if (!wifi.isConnected()) {
        // Network unavailable: store in NVS Ring Buffer with delayed_sync = true
        TelemetryRecord bufferedRecord = record;
        bufferedRecord.delayed_sync = true;
        storage.enqueueRecord(bufferedRecord);
        return false;
    }

    // Direct HTTP POST over HTTPS
    String payload = serializePayload(record);
    bool success = true; // Simulated HTTP POST result

    if (!success) {
        // HTTP send failed: store in NVS Ring Buffer
        TelemetryRecord bufferedRecord = record;
        bufferedRecord.delayed_sync = true;
        storage.enqueueRecord(bufferedRecord);
        return false;
    }

    return true;
}

void TelemetryClient::flushQueue() {
    if (!wifi.isConnected() || storage.isEmpty()) return;

    TelemetryRecord record;
    while (!storage.isEmpty()) {
        if (storage.peekRecord(record)) {
            record.delayed_sync = true;
            String payload = serializePayload(record);
            // Submit to /api/v1/telemetry
            storage.dequeueRecord(record);
        }
    }
}

void TelemetryClient::loop() {
    wifi.update();
    if (wifi.isConnected() && !storage.isEmpty()) {
        flushQueue();
    }
}
