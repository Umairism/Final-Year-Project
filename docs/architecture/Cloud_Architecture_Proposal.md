# HealSense Cloud-Native Architecture Specification

## Project Title & Identity

**HealSense: Deep Learning-Based Smart Health Surveillance and Prediction Model Using IoT**

> [!IMPORTANT]
> **Project Identity Statement**:  
> *HealSense is an explainable IoT-based clinical decision support prototype that combines deterministic physiological safety rules with temporal machine learning analysis.*  
> The system does **not** perform medical diagnosis, disease prediction, mortality prediction, or discovery of clinical truth.

---

## Executive Summary

This document specifies the finalized cloud-native architecture for HealSense. The design removes the Raspberry Pi 5 from the core data acquisition path, transitioning all computational logic (preprocessing, deterministic rule evaluation, temporal LSTM analysis, fusion engine execution, and LLM explanation generation) to a centralized FastAPI backend service.

Sensors connect directly to an ESP32 micro-controller, which acts strictly as a telemetry acquisition gateway with local offline buffering capabilities.

---

## Architecture Design & Data Flow

```
┌────────────────────────────────────────────────────────┐
│ Physiological Telemetry Acquisition Layer              │
│ • MAX30100 (Heart Rate & SpO₂)                         │
│ • MLX90614 (Body Temperature)                          │
│ • Optional BP Input (Manual / BLE Cuff / Future UART)  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ ESP32 IoT Gateway                                      │
│ • Telemetry acquisition & JSON formatting              │
│ • Offline storage (NVS buffer) & retry queue           │
└───────────────────────────┬────────────────────────────┘
                            │ WiFi (Direct HTTPS)
                            ▼
┌────────────────────────────────────────────────────────┐
│ FastAPI Cloud Backend                                  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ Canonical Clinical Schema Validation                   │
└───────────────────────────┬────────────────────────────┘
                            │
          ┌─────────────────┴─────────────────┐
          ▼                                   ▼
┌───────────────────────────┐       ┌───────────────────────────┐
│ Deterministic Safety      │       │ Temporal LSTM Analysis    │
│ Rules Engine              │       │ (Rule-Derived Proxy       │
│ (Medical Safety Bounds)   │       │  Label Model)             │
└─────────┬─────────────────┘       └─────────┬─────────────────┘
          │                                   │
          └─────────────────┬─────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ Fusion Engine                                          │
│ • Deterministic Safety Override (Hard Priority)        │
│ • ML Confidence Augmentation (Experimental Weights)    │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ Gemini Explanation Layer                               │
│ • Natural Language Explanation (Non-diagnostic)        │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ Persistence & Presentation                             │
│ • PostgreSQL Database                                  │
│ • Web & Mobile Dashboards                              │
└────────────────────────────────────────────────────────┘
```

---

## Data Acquisition & Hardware Scope

### Deployed Sensors
* **MAX30100**: Optical PPG sensor measuring Heart Rate (bpm) and Blood Oxygen Saturation ($\text{SpO}_2\%$).
* **MLX90614**: Non-contact infrared sensor measuring body temperature (°C).

### Optional Contextual Feature: Blood Pressure (BP)
Blood Pressure is explicitly designated as an **optional contextual feature**. Deployed optical hardware does **not** perform continuous BP measurement.

Blood pressure inputs can be supplied through:
1. **Manual Entry**: User/clinician input via Web or Mobile Dashboard (`bp_source: "manual_entry"`).
2. **Bluetooth Cuff Integration**: Mobile app syncing with standard GATT BLE BP cuffs (`bp_source: "ble_cuff"`).
3. **Future UART Expansion**: External OEM Non-Invasive Blood Pressure (NIBP) hardware modules attached to ESP32 serial pins (`bp_source: "hardware_uart"`).

If BP data is omitted, Pydantic validation handles fields as `None`, and deterministic safety rules operate on remaining active telemetry streams.

---

## ESP32 Firmware Responsibilities & Offline Resilience

### Primary Responsibilities
1. Read I2C telemetry from MAX30100 and MLX90614.
2. Format sensor data into standard JSON payloads.
3. Transmit HTTP POST payloads over Wi-Fi directly to the FastAPI cloud ingestion endpoint.

### Offline Resiliency Logic
If Wi-Fi or Internet connectivity is interrupted:
* ESP32 persists up to $N$ un-uploaded records in local Non-Volatile Storage (NVS / SPIFFS buffer).
* A background retry loop checks connectivity every $X$ seconds.
* Upon reconnection, buffered records are transmitted with `delayed_sync: true` and their original hardware timestamp (`recorded_at`).

> [!NOTE]
> TLS encryption increases memory usage on the ESP32 and must be monitored during continuous telemetry sampling.

---

## Machine Learning Scope & Explicit Limitations

> [!WARNING]
> **LSTM Model Boundary**:  
> *The LSTM is trained on rule-derived proxy labels generated from deterministic safety constraints. Therefore, the model evaluates temporal consistency with safety boundaries rather than predicting independently validated clinical outcomes.*

* **Sequence Windowing**: Analyzes temporal trends across 60-second sliding windows (buffered in Python backend memory / PostgreSQL sequence queries).
* **Model Purpose**: Pattern detection for physiological stability vs. degradation trends under proxy conditions.

---

## Deterministic Rules & Fusion Engine Logic

### 1. Deterministic Safety Rules Engine
Medical safety constraints maintain absolute priority over probabilistic ML predictions.
* **Severe Hypoxemia**: $\text{SpO}_2 < 92\%$ $\rightarrow$ **CRITICAL**
* **Extreme Tachycardia**: $\text{Heart Rate} > 120\text{ bpm}$ $\rightarrow$ **WARNING / CRITICAL**
* **High Fever**: $\text{Temperature} > 39.0^\circ\text{C}$ $\rightarrow$ **WARNING / CRITICAL**

### 2. Decision Fusion Hierarchy
Rather than claiming clinically validated scoring algorithms, the fusion engine executes a 3-tier hierarchy:
1. **Deterministic Critical Override**: If safety rules trigger a `CRITICAL` state, the final system output is forced to `CRITICAL` regardless of ML predictions.
2. **ML Confidence Augmentation**: Probabilistic outputs modify confidence metrics only within non-critical states.
3. **Explanation Generation**: The combined output feeds into the LLM layer.

*Note*: Fusion weights (e.g., $0.6 \times \text{Rule} + 0.4 \times \text{ML}$) remain **experimental prototype parameters** and are not clinically optimized.

---

## Gemini Explanation Layer

The Gemini LLM service acts strictly as a natural language synthesizer.
* **Allowed**: Summarizing triggered rule constraints, describing temporal degradation trends in plain text, presenting system status clearly.
* **Prohibited**: Changing risk scores, altering confidence metrics, or generating medical diagnoses/prescriptions.

---

## System Limitations and Ethical Boundaries

This section documents the formal boundaries for academic evaluation and clinical scope:

1. **No Medical Diagnosis**: The system does not diagnose clinical conditions or diseases.
2. **No Clinical Outcome Prediction**: Predictions reflect synthetic proxy-label trend trajectories, not actual clinical prognosis or mortality rates.
3. **No Physician Replacement**: The tool is strictly a technical prototype for clinical decision support study.
4. **Rule-Derived Proxy Labels**: ML training data relies on synthetic boundaries rather than validated hospital EHR outcomes.
5. **Hardware Scope**: Deployed IoT hardware does not measure continuous Blood Pressure; BP remains an optional manual or external peripheral input.
6. **Prototype Status**: Implemented as a research prototype under simplified deployment conditions.

---

## Justification for Raspberry Pi 5 Removal

The Raspberry Pi 5 was removed from the core operational pipeline for the following defensible engineering reasons:

1. **Elimination of Unnecessary Relays**: The Pi operated solely as a pass-through network bridge between ESP32 and Cloud.
2. **Reduced Hardware & Deployment Complexity**: Eliminating the intermediate gateway reduces hardware costs, thermal failure points, and configuration overhead.
3. **Cloud-Native Ingestion**: Direct ESP32-to-FastAPI communication aligns with standard IoT cloud architecture.

---

## Conclusion

The updated HealSense architecture presents an academically defensible, cloud-native IoT framework. By establishing clear ethical boundaries, removing unnecessary intermediary hardware, explicitly acknowledging proxy-label ML constraints, and designating Blood Pressure as an optional contextual parameter, the project provides a solid engineering foundation for FYP defense.