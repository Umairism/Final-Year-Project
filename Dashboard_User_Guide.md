# HealSense Dashboard User & Clinical Guide

**Version**: v1.4.0-frontend-integration  
**Target Audience**: Clinical Reviewers, FYP Defense Evaluators, Operators  
**Date**: August 3, 2026  

---

## 1. Navigating the Dashboard (`/dashboard`)

### A. Vitals Monitoring Cards
* **Heart Rate**: Real-time heart rate value in BPM with pulse animation and status badge.
* **Blood Oxygen (SpO₂)**: Real-time SpO₂ percentage display. Highlights values $< 92\%$ in red (`CRITICAL`).
* **Body Temperature**: Continuous temperature reading in °C.
* **Blood Pressure Card**: Displays BP reading (`Systolic / Diastolic`) alongside the exact **Acquisition Source Badge**:
  - `Source: Manual Entry`
  - `Source: BLE Cuff`
  - `Source: Hardware UART`
  - `Source: No BP Recorded` (when BP is unavailable)

### B. Offline Sync Badge (`Delayed Sync`)
When telemetry data is uploaded after an ESP32 Wi-Fi reconnect or backend recovery, a grey **Delayed Sync** badge automatically attaches to the card, preserving historical transparency.

### C. Risk Assessment & Decision Support Panel
* **Risk Gauge**: Visualizes the fused risk level (`NORMAL`, `WARNING`, `CRITICAL`), fused score, and triggered deterministic safety rule flags.
* **Decision Support Explanation**: Displays AI-generated non-diagnostic clinical explanation text from Gemini LLM.

---

## 2. Gateway Device Management (`/devices`)

Access `/devices` from the navigation header to view:
* Hardware Device ID (`ESP32_PATIENT_001`, `PHONE_1`).
* Live Connectivity Status (`Online` / `Offline`).
* Last Seen Heartbeat Timestamp.
* Device Battery Level.
