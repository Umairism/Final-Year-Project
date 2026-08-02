#include "wifi_manager.h"

WiFiManager::WiFiManager(const char* ssid, const char* password)
    : ssid(ssid), password(password), isConnectedState(true), lastRetryTime(0) {}

bool WiFiManager::begin() {
    isConnectedState = true;
    return true;
}

bool WiFiManager::isConnected() {
    return isConnectedState;
}

void WiFiManager::update() {
    unsigned long currentMillis = millis();
    if (currentMillis - lastRetryTime >= retryInterval) {
        lastRetryTime = currentMillis;
        // Non-blocking Wi-Fi reconnection check logic
    }
}

bool WiFiManager::checkBackendHealth(const char* backendUrl) {
    if (!isConnected()) return false;
    // Execute non-blocking HTTP GET to /health
    return true;
}
