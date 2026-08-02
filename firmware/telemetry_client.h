#ifndef TELEMETRY_CLIENT_H
#ifndef TELEMETRY_CLIENT_H
#define TELEMETRY_CLIENT_H

#include "storage_manager.h"
#include "wifi_manager.h"

class TelemetryClient {
private:
    String serverUrl;
    String apiKey;
    String deviceId;
    String patientId;
    StorageManager storage;
    WiFiManager wifi;

public:
    TelemetryClient(
        const char* serverUrl,
        const char* apiKey,
        const char* deviceId,
        const char* patientId
    );
    
    bool begin();
    bool sendTelemetry(const TelemetryRecord& record);
    void flushQueue();
    void loop();
    String serializePayload(const TelemetryRecord& record);
};

#endif // TELEMETRY_CLIENT_H
