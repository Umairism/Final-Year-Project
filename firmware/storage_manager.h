#ifndef STORAGE_MANAGER_H
#ifndef STORAGE_MANAGER_H
#define STORAGE_MANAGER_H

#include <Arduino.h>

#define MAX_BUFFER_CAPACITY 500

struct TelemetryRecord {
    float heart_rate;
    float spo2;
    float temperature;
    float systolic_bp;
    float diastolic_bp;
    bool delayed_sync;
    uint64_t timestamp;
};

class StorageManager {
private:
    uint16_t headIndex;
    uint16_t tailIndex;
    uint16_t currentCount;

public:
    StorageManager();
    bool begin();
    bool enqueueRecord(const TelemetryRecord& record);
    bool dequeueRecord(TelemetryRecord& record);
    bool peekRecord(TelemetryRecord& record) const;
    uint16_t getQueueSize() const;
    bool isFull() const;
    bool isEmpty() const;
    void clearQueue();
};

#endif // STORAGE_MANAGER_H
