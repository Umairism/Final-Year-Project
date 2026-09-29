# Phase 5: Machine Learning Audit & Inventory Report

**Project Identity**:  
*HealSense is an explainable IoT-based clinical decision support prototype combining deterministic physiological safety rules with temporal machine learning analysis.*

**Target Model**: LSTM Temporal Risk Estimator  
**Audit Date**: August 3, 2026  
**Status**: AUDIT COMPLETE (NO CODE MODIFIED IN THIS PHASE STEP)  

---

## 1. Model Architecture & Parameters

* **Model Type**: Recurrent Neural Network (LSTM / Long Short-Term Memory).
* **Input Tensor Shape**: `(batch_size, 60, 5)` — representing a sliding temporal window of 60 seconds (or readings) across 5 physiological features.
* **Input Features (5)**:
  1. `heart_rate` (BPM)
  2. `spo2` (%)
  3. `temperature` (°C)
  4. `systolic_bp` (mmHg)
  5. `diastolic_bp` (mmHg)
* **Output Classification Classes (3)**:
  - `0`: `normal`
  - `1`: `warning`
  - `2`: `critical`
* **Artifact Files**:
  - `data/models/v1.0.0/model.h5`
  - `data/models/v1.0.0/scaler.pkl`
  - `data/models/v1.0.0/label_encoder.pkl`

---

## 2. Training Process & Dataset Provenance

* **Training Pipeline Script**: [notebooks/02_lstm_health_prediction.ipynb](file:///e:/Study%20Material/FYP/FYP-Project/healsense/notebooks/02_lstm_health_prediction.ipynb) & [scripts/train_model.py](file:///e:/Study%20Material/FYP/FYP-Project/healsense/scripts/train_model.py).
* **Label Provenance**: Rule-derived proxy labels generated from deterministic safety constraints (e.g. SpO2 thresholds, HR ranges).
* **Important Academic Limitation**: Model evaluates temporal consistency with deterministic safety boundaries rather than independently validated diagnostic clinical outcomes.

---

## 3. Identified Gaps & Reproducibility Audit

1. **Evaluation Reports**: Missing standalone evaluation script generating `confusion_matrix.png` and `roc_curve.png`.
2. **Missing Metadata File**: `data/models/metadata/model_card.json` needs formalization.
3. **Synthetic Clinical Scenario Testing**: Backend test suite requires explicit multi-step temporal trend scenarios.
