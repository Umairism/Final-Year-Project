# Model Architecture Specification

**Model Architecture**: LSTM (Long Short-Term Memory) Recurrent Neural Network  
**Target Function**: Temporal Risk Estimation across Physiological Sequences  
**Version**: v1.5.0-ml-validation  
**Date**: August 3, 2026  

---

## 1. Input Tensor Specification

* **Shape**: `(batch_size, 60, 5)`
* **Sequence Length**: 60 seconds (or readings).
* **Feature Dimension (5)**:
  1. `heart_rate`
  2. `spo2`
  3. `temperature`
  4. `systolic_bp`
  5. `diastolic_bp`

---

## 2. Model Layer Diagram

```
Input Sequence Shape: (Batch, 60, 5)
                 │
                 ▼
          ┌─────────────┐
          │ LSTM Layer  │  (Units: 64, Return Sequences = False)
          └──────┬──────┘
                 │
                 ▼
          ┌─────────────┐
          │ Dropout     │  (Rate: 0.2)
          └──────┬──────┘
                 │
                 ▼
          ┌─────────────┐
          │ Dense Layer │  (Units: 32, Activation: ReLU)
          └──────┬──────┘
                 │
                 ▼
          ┌─────────────┐
          │ Dense Output│  (Units: 3, Activation: Softmax)
          └─────────────┘
                 │
                 ▼
Output Probability vector over ['normal', 'warning', 'critical']
```
