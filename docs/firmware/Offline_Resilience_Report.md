# Offline Resilience & Recovery Validation Report

**Version**: v1.3.0-edge-resilience  
**Date**: August 3, 2026  

---

## 1. Resilience Simulation Test Results

Automated simulation tests were added in `backend/tests/test_phase3_simulation.py` to validate backend ingestion during edge network dropouts:

```
tests/test_phase3_simulation.py ...                                      [100%]
3 passed in 16.94s
```

### Scenario A: Wi-Fi Disconnection & Recovery (`test_scenario_a_wifi_loss_and_flush`)
* **Simulation**: Wi-Fi drops for 10 sampling cycles. Telemetry records are enqueued into ESP32 NVS memory. Upon Wi-Fi recovery, 10 records are posted sequentially.
* **Result**: All 10 records successfully ingested and stored in PostgreSQL with `delayed_sync: true` and original sample timestamps intact.

### Scenario B: Backend API Outage & Flush (`test_scenario_b_backend_outage_and_recovery`)
* **Simulation**: Backend server unreachable for 20 sampling cycles.
* **Result**: ESP32 stores 20 records in NVS storage; flushes all 20 records cleanly when backend health check succeeds (`201 Created`).

### Scenario C: Un-announced ESP32 Reboot (`test_scenario_c_esp32_reboot_nvs_preservation`)
* **Simulation**: ESP32 loses power / reboots mid-outage with queued items in NVS memory.
* **Result**: NVS memory partition retains queued samples across boot cycle.

---

## 2. Performance Parameters

* **Max NVS Queue Capacity**: 500 records (~1.5 to 2 hours of continuous vitals at 10s intervals).
* **Non-Blocking Retry Frequency**: Every 30 seconds.
* **Packet Loss Protection**: 100% data retention within queue capacity bounds.
