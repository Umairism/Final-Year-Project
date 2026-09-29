# HealSense Machine Learning Model Explainability Report

**Model Architecture**: LSTM (Long Short-Term Memory)  
**Target Domain**: Temporal Risk Estimation  
**Version**: v1.5.0-ml-validation  
**Date**: August 3, 2026  

---

> [!IMPORTANT]
> **Project Identity Anchor**:  
> *HealSense is an explainable IoT-based clinical decision support prototype combining deterministic physiological safety rules with temporal machine learning analysis.*

---

## 1. Justification: Why LSTM for Vital Signs Monitoring?

1. **Temporal Dependencies**: Physiological vitals are dynamic time-series sequences. A single isolated reading of $HR=105$ BPM may be harmless, but a continuous upward trajectory from $70 \rightarrow 85 \rightarrow 105$ over 10 minutes signals physiological degradation.
2. **Noise Resilience**: Short-term sensor fluctuations (e.g. motion artifacts on optical MAX30100) are smoothed across 60-second sliding windows.
3. **Early Trend Detection**: The LSTM cell state retains historical context to detect subtle deterioration before clinical alarm thresholds are breached.

---

## 2. Model Role & Academic Scope Boundaries

```
                      What the LSTM Model DOES:
  ┌─────────────────────────────────────────────────────────────┐
  │ • Evaluates 60-second temporal vital sign trends.           │
  │ • Computes risk trend probabilities (normal/warning/critical).│
  │ • Provides input weighting for the Hybrid Fusion Engine.    │
  └─────────────────────────────────────────────────────────────┘

                    What the LSTM Model DOES NOT:
  ┌─────────────────────────────────────────────────────────────┐
  │ ❌ Perform independent medical or clinical diagnosis.       │
  │ ❌ Predict clinical mortality or disease etiologies.         │
  │ ❌ Override deterministic WHO physiological safety bounds.   │
  └─────────────────────────────────────────────────────────────┘
```
