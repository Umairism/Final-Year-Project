#ifndef WIFI_MANAGER_H
#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include <Arduino.h>

class WiFiManager {
private:
    String ssid;
    String password;
    bool isConnectedState;
    unsigned long lastRetryTime;
    const unsigned long retryInterval = 30000; // Non-blocking 30-second retry

public:
    WiFiManager(const char* ssid = "HealSense_Net", const char* password = "secure_password");
    bool begin();
    bool isConnected();
    void update();
    bool checkBackendHealth(const char* backendUrl);
};

#endif // WIFI_MANAGER_H
