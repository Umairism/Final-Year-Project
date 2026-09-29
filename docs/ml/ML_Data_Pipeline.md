# HealSense Machine Learning Data Pipeline

**Version**: v1.5.0-ml-validation  
**Date**: August 3, 2026  

---

## Data Transformation Flow

```
┌──────────────────────────────────────────────┐
│ Raw IoT Telemetry Sample                     │
│ (HR, SpO2, Temp, Systolic BP, Diastolic BP) │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│ Data Cleaning & Imputation                   │
│ (Null BP filled with 120/80 default or null)│
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│ StandardScaler Normalization                 │
│ (Scales features using fitted scaler.pkl)    │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│ 60-Second Sliding Window Construction        │
│ Shape: (1, 60, 5)                            │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│ LSTM Model Forward Pass                      │
│ (Softmax probabilities over 3 risk classes)  │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│ Output Probability & Predicted Class         │
│ (normal, warning, critical)                  │
└──────────────────────────────────────────────┘
```

---

## Feature Specifications

| Feature Name | Acquisition Source | Sampling Unit | Normalization Range |
| :--- | :--- | :--- | :--- |
| `heart_rate` | MAX30100 Optical Sensor | BPM | Continuous Z-score |
| `spo2` | MAX30100 Optical Sensor | % | Continuous Z-score |
| `temperature` | MLX90614 Infrared | °C | Continuous Z-score |
| `systolic_bp` | BLE Cuff / Manual | mmHg | Continuous Z-score |
| `diastolic_bp` | BLE Cuff / Manual | mmHg | Continuous Z-score |
