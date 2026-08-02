# Fusion Engine Validation Report

**Subsystem**: Hybrid Clinical Risk Engine (`backend/api/services/fusion_engine.py`)  
**Version**: v1.5.0-ml-validation  
**Date**: August 3, 2026  

---

## 1. Multi-Tier Decision Hierarchy

```
                    ┌─────────────────────────┐
                    │ Canonical Feature Input │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ Layer 1: Safety Bounds  │
                    │ (SpO2 < 92%, HR > 150)  │
                    └────────────┬────────────┘
                                 │
                      Is Critical Boundary Breached?
                      /                         \
                    YES                          NO
                     │                           │
                     ▼                           ▼
        ┌─────────────────────────┐ ┌─────────────────────────┐
        │ DETERMINISTIC OVERRIDE  │ │ Layer 2: Hybrid Score   │
        │ Force Risk = CRITICAL   │ │ 0.6 * Rule Score +      │
        │ Force Confidence = 1.0  │ │ 0.4 * LSTM Score        │
        └─────────────────────────┘ └─────────────────────────┘
```

---

## 2. Weight Distribution & Safety Verification

* **Deterministic Rule Weight**: `0.6` (60%)
* **LSTM Model Score Weight**: `0.4` (40%)
* **Safety Override Rule**: If any deterministic WHO rule triggers a `CRITICAL` status (e.g. Hypoxia $SpO_2 < 92\%$), the engine immediately overrides all ML output, outputting `CRITICAL` risk with maximum confidence ($1.0$).
