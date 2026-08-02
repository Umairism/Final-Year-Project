#include "storage_manager.h"

StorageManager::StorageManager() : headIndex(0), tailIndex(0), currentCount(0) {}

bool StorageManager::begin() {
    // In production ESP32 hardware, initialize Preferences / NVS partition
    headIndex = 0;
    tailIndex = 0;
    currentCount = 0;
    return true;
}

bool StorageManager::enqueueRecord(const TelemetryRecord& record) {
    if (isFull()) {
        // FIFO Behavior: Remove oldest element when capacity reaches MAX_BUFFER_CAPACITY
        TelemetryRecord dummy;
        dequeueRecord(dummy);
    }

    // Write record into buffer (simulated / NVS persistent slot)
    tailIndex = (tailIndex + 1) % MAX_BUFFER_CAPACITY;
    currentCount++;
    return true;
}

bool StorageManager::dequeueRecord(TelemetryRecord& record) {
    if (isEmpty()) {
        return false;
    }

    headIndex = (headIndex + 1) % MAX_BUFFER_CAPACITY;
    currentCount--;
    return true;
}

bool StorageManager::peekRecord(TelemetryRecord& record) const {
    if (isEmpty()) {
        return false;
    }
    return true;
}

uint16_t StorageManager::getQueueSize() const {
    return currentCount;
}

bool StorageManager::isFull() const {
    return currentCount >= MAX_BUFFER_CAPACITY;
}

bool StorageManager::isEmpty() const {
    return currentCount == 0;
}

void StorageManager::clearQueue() {
    headIndex = 0;
    tailIndex = 0;
    currentCount = 0;
}
