# AI_ENGINE_REPORT.md — HealSense AI Engine & LSTM Deep-Dive

> **Scope:** Custom AI Engine · LSTM Risk Model · LLM (Gemini) Explanation Layer  
> **Audit Date:** 2026-09-29  
> **Method:** Direct code inspection — every claim is cited to an exact file and line number  
> **Context:** You confirmed that real-time sensor data (I2C / ESP32) is NOT yet flowing. Training is intended to use Kaggle/PhysioNet datasets.

---

## 1. AI Engine Overview — What You Actually Built

HealSense's AI engine is a **5-layer hybrid decision pipeline**. Understanding which layers are real vs. mocked is the starting point for everything.

```
┌────────────────────────────────────────────────────────────────────┐
│  LAYER 1 — Canonical Feature Vector                                │
│  File: fusion_engine.py:25-45                                      │
│  Status: ✅ REAL                                                   │
│  Input: Patient ORM + VitalSigns ORM                               │
│  Output: CanonicalClinicalFeatureSchema (5 vitals + history)       │
│  Problem: Missing BP silently defaults to 120/80 (line 31-32)     │
└─────────────────────────────┬──────────────────────────────────────┘
                              │
┌─────────────────────────────▼──────────────────────────────────────┐
│  LAYER 2 — Deterministic Rules Engine                              │
│  File: fusion_engine.py:47-94                                      │
│  Status: ✅ REAL AND CORRECT                                       │
│  SpO2 < 92 → CRITICAL | HR > 150 or < 40 → CRITICAL              │
│  BP ≥ 180/120 → CRITICAL | SpO2 < 95 → WARNING | Temp ≥ 38 → WARN │
│  Confidence penalty for missing history (age/diabetes/smoking)     │
└─────────────────────────────┬──────────────────────────────────────┘
                              │
┌─────────────────────────────▼──────────────────────────────────────┐
│  LAYER 3 — LSTM PredictionService                                  │
│  File: prediction_service.py:65-120                                │
│  Status: ❌ ALWAYS RETURNS None (no model file on disk)            │
│  The code path is correct; the artifact files are missing          │
│  Problem: data/models/v1.0.1/lstm_best.h5 does not exist          │
│  Problem: Config says v1.0.1; train_model.py writes v1.0.2        │
└─────────────────────────────┬──────────────────────────────────────┘
                              │
┌─────────────────────────────▼──────────────────────────────────────┐
│  LAYER 4 — Fusion Engine                                           │
│  File: fusion_engine.py:96-141                                     │
│  Status: ⚠️  REAL but always "deterministic_only" mode             │
│  because ml_prediction is always None                              │
│  Safety override is real and correct                               │
│  Weighted fusion (det×0.6 + ml×0.4) code exists but unreachable   │
└─────────────────────────────┬──────────────────────────────────────┘
                              │
┌─────────────────────────────▼──────────────────────────────────────┐
│  LAYER 5 — Gemini LLM Explanation                                  │
│  File: fusion_engine.py:143-208                                    │
│  Status: ✅ REAL (if GEMINI_API_KEY is set)                        │
│  Correctly constrained: cannot modify decision                     │
│  Problem: No GEMINI_API_KEY → returns fallback string every time  │
│  Problem: system_prompt in wrong API field (user role, not system) │
└────────────────────────────────────────────────────────────────────┘
```

**Net result of a live telemetry call today:**  
Layer 2 runs → deterministic rules applied → Layer 3 returns `None` → Layer 4 uses `"deterministic_only"` mode → Layer 5 returns fallback string.  
**The LSTM is completely disconnected at runtime.**

---

## 2. Every LSTM Break-Point (Exact File + Line)

### Break 1 — Training data file does not exist

```
File:    scripts/train_model.py:32
Code:    DATA_PATH = '../data/raw/bidmc_vitals.csv'
Runtime: pd.read_csv on line 57 → FileNotFoundError
Status:  FATAL — script crashes immediately
```

`bidmc_vitals.csv` is produced by `scripts/preprocess_bidmc.py`, which downloads from PhysioNet using the `wfdb` library. Neither download nor preprocessing has been run. The `data/` directory contains only `.gitignore`.

---

### Break 2 — Model version mismatch (config vs training script)

```
File A:  backend/api/config.py:73-74
Code:    MODEL_VERSION: str = "v1.0.1"
         LSTM_MODEL_PATH = "../data/models/v1.0.1/lstm_best.h5"

File B:  scripts/train_model.py:33-35
Code:    MODEL_VERSION = "v1.0.2"
         MODEL_DIR = '../data/models/v1.0.2'
         CHECKPOINT_PATH = f"{MODEL_DIR}/lstm_best.h5"
```

If you train successfully, artifacts land in `v1.0.2/`. The backend reads from `v1.0.1/`. Model load returns `False`. Everything silently falls back to deterministic-only.

**Fix:** Change `config.py:73` → `MODEL_VERSION: str = "v1.0.2"`.

---

### Break 3 — Silent degradation (no crash, no indicator in API response)

```
File: prediction_service.py:75-77
    if not self.model or not self.scaler or not self.label_encoder:
        logger.warning("PredictionService is not fully loaded. Skipping prediction.")
        return None
```

`None` is passed to `fuse_risk()`. The fusion response includes `"fusion_method": "deterministic_only"` — but the frontend doesn't check this field. A judge looking at the dashboard sees no indication the ML layer is inactive.

---

### Break 4 — BIDMC dataset lacks 3 of 5 required LSTM input features

```
File: scripts/preprocess_bidmc.py:31-33
    mapped_df['temperature'] = np.nan      ← always missing
    mapped_df['systolic_bp'] = np.nan      ← always missing
    mapped_df['diastolic_bp'] = np.nan     ← always missing
```

The LSTM input shape is `(60, 5)` — 5 features. BIDMC only provides HR and SpO2. **60% of the feature space is always NaN before imputation.**

---

### Break 5 — Imputation strategy: -1.0 is physiologically impossible

```
File: scripts/train_model.py:98-99
    X_imputed = np.where(np.isnan(X_reshaped), -1.0, X_reshaped)
```

**Problems with -1.0:**
- -1.0°C temperature is physiologically impossible. The `StandardScaler` fits a bimodal distribution: real values + a large mass at -1.0.
- When the scaler sees columns with near-zero variance (temperature/BP always = -1.0), `scale_` approaches 0. Division by near-zero in `transform()` produces very large values or NaN.
- At runtime inference, missing BP defaults to `0.0` (not `-1.0`) in `prediction_service.py:87`: `v.get(f, 0.0)`. **The scaler was fit on -1.0; inference feeds 0.0. This is train-serve skew that corrupts all predictions.**

---

### Break 6 — LSTM labels are circular (model learns the rules, not health)

```
File: scripts/preprocess_bidmc.py:38-44  ← label derivation
    if spo2 < 92: → 'critical'
    elif hr > 120: → 'warning'
    elif spo2 < 95: → 'warning'

File: fusion_engine.py:54-73  ← same thresholds in production
    if features.spo2 < 92: → CRITICAL
    elif features.heart_rate > 120: → WARNING
    elif features.spo2 < 95: → WARNING
```

The LSTM is trained to predict the output of the same rule engine it sits inside. The model learns nothing beyond what the rules already know. The weighted fusion `(det×0.6 + ml×0.4)` will almost always agree with pure deterministic, making the ML contribution meaningless in practice.

---

### Break 7 — Synthetic data generator uses different thresholds than rules engine

```
generate_synthetic_data.py:17    heart_rate > 130 → critical (rules say > 150)
generate_synthetic_data.py:24    spo2 < 90 → critical (rules say < 92)
generate_synthetic_data.py:26    spo2 < 92 → warning (rules use 92 as critical threshold)
```

The `notebook/02_lstm_health_prediction.ipynb` trains on synthetic data (line 105: `DATA_PATH = '../data/raw/synthetic/synthetic_vital_signs.csv'`). The `train_model.py` trains on BIDMC. They target different datasets with different label definitions. **Results from the notebook cannot be applied to the production system.**

---

### Break 8 — Sequence length (60) requires substantial history before ML activates

```
File: prediction_service.py:79-81
    if len(vitals_history) < self.sequence_length:  # 60 readings
        return None
```

With one reading per minute from the ESP32, a new patient must be monitored for **60 minutes** before the LSTM contributes at all. For the first hour, every patient is deterministic-only regardless of model state.

---

### Break 9 — Evaluation script generates metrics from random numbers

```
File: backend/ml/evaluate_model.py:14-21
    y_true = np.random.choice([0, 1, 2], size=300, p=[0.7, 0.2, 0.1])
    y_pred = y_true.copy()
    noise = np.random.choice([0, 1], size=300, p=[0.9, 0.1])
    y_pred = (y_pred + noise) % 3
```

Committed `backend/ml/results/metrics_report.json`:
```json
{ "accuracy": 0.87, "precision": 0.87, "recall": 0.87, "f1_score": 0.877 }
```

These numbers are mathematically correct for the random inputs — but **no model exists** and **no real predictions were made**. This file must not be presented to judges or included in a paper.

---

### Break 10 — Scaler fit on near-zero variance columns (BIDMC issue)

With temperature/BP always = -1.0 during training:
- `scaler.mean_[2]` ≈ -1.0, `scaler.scale_[2]` ≈ 0
- `scaler.transform()` computes `(x - mean) / scale` → division by ~0 → extremely large values or NaN for real inputs

At inference with a real temperature of 37.0°C:  
`(37.0 - (-1.0)) / ε` → the LSTM input becomes a huge number, producing garbage predictions.

---

## 3. The Mock Data Problem — Full Diagnosis

### 3.1 Where Mock Data Is Currently Active

| Location | What is Mocked | Impact |
|---|---|---|
| `config.ts:6` | `VITE_USE_MOCK_DATA !== 'false'` — **defaults to true** | All web app users see fake data |
| `useVitals.ts:17-41` | `generateVitalReading()` — random walk | Fake animated vitals on dashboard |
| `Dashboard.tsx:190-196` | `mlProbability={0.15}` hardcoded; static explanation | Real fusion results never shown |
| `prediction_service.py:75-77` | Returns `None` when model missing | Backend silently deterministic-only |
| `firmware/telemetry_client.cpp:50` | `bool success = true; // Simulated` | No real HTTP POST from ESP32 |
| `sensor_service.dart:8` | `MethodChannel` with no native impl | Flutter cannot read phone sensors |

### 3.2 Lack of ESP32 Data Does NOT Block LSTM Training

Real-time sensor data is for **inference** (runtime). Training uses **historical datasets** from Kaggle/PhysioNet. You do not need the ESP32 running to train the model.

**What you need for training:** The Kaggle dataset (already identified in notebook 01). 

**What you need for live demo:** A working backend + database + any device sending data (could be the test client or manual POST via curl/Postman instead of real ESP32).

### 3.3 After ESP32 Is Connected

1. ESP32 → `POST /api/v1/telemetry` → `TelemetryIngestionService.ingest()`
2. `get_vitals_history()` fetches last 60 DB readings
3. `predict_risk(vitals_history)` called — returns `None` for first 60 minutes
4. After 60 readings: LSTM inference runs (if model exists)
5. Fusion uses weighted combination

So even with a trained model, the first 60 minutes of any patient's monitoring session is deterministic-only. This is correct behavior.

---

## 4. Your Kaggle Datasets — Feature Compatibility Analysis

From `notebooks/01_data_exploration.ipynb` — 309,751 total records across 7 datasets.

### 4.1 Feature Coverage Matrix

| Dataset | Records | HR | SpO2 | Temp | SBP | DBP | Usable for LSTM |
|---|---|---|---|---|---|---|---|
| **Human Vital Signs 2024** | 200,020 | ✅ | ✅ | ✅ | ✅ | ✅ | **⭐ PRIMARY** |
| **CVD Vital Signs** | 23,468 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Secondary |
| Synthetic Vitals | 10,000 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Supplementary |
| Body Signals (Smoking) | 55,692 | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ No HR/SpO2 |
| Diabetes Dataset | 10,000 | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ No HR/SpO2 |
| Heart Attack Risk | 9,651 | ✅ | ❌ | ❌ | ✅ | ❌ | ⚠️ Partial |
| UCI Heart Disease | 920 | ✅ | ❌ | ❌ | ✅ | ❌ | ⚠️ Too small |
| BIDMC PhysioNet | ~9,400 | ✅ | ✅ | ❌ | ❌ | ❌ | ⚠️ Missing 3 features |

**Use Human Vital Signs 2024 as your primary training dataset.** It has all 5 features and 200K records — drop BIDMC for now.

### 4.2 Column Name Mapping (Notebook → Schema)

```python
rename_map = {
    'Heart Rate': 'heart_rate',
    'Oxygen Saturation': 'spo2',
    'Body Temperature': 'temperature',      # CHECK: may be Fahrenheit
    'Systolic Blood Pressure': 'systolic_bp',
    'Diastolic Blood Pressure': 'diastolic_bp',
}
# Convert if Fahrenheit (max > 50 means F):
if df['temperature'].max() > 50:
    df['temperature'] = (df['temperature'] - 32) * 5 / 9
```

### 4.3 How to Create Patient Groups (Cross-Sectional → Sequences)

The Kaggle dataset is cross-sectional (one row = one snapshot, not time series). For LSTM training you need groups of 60+ consecutive readings per "patient":

```python
df = df.dropna(subset=['heart_rate', 'spo2', 'temperature', 'systolic_bp', 'diastolic_bp'])
df = df.reset_index(drop=True)
df['patient_id'] = df.index // 200   # 200-row groups → 1000 virtual patients
```

This creates ~1000 virtual patients from 200K records. Each patient has 200 readings — enough for multiple 60-step sequences.

---

## 5. LLM (Gemini) Integration — Full Analysis

### 5.1 What Works Well

- **Safety constraints are correct** — 8 rules in system prompt (lines 156-163) explicitly prevent the LLM from deciding or changing risk
- **Async with timeout** — 30-second timeout; errors fall back gracefully (lines 195-208)
- **Separation of concerns** — Gemini in `fusion_engine.py` (clinical reasoning) is separate from Gemini in `routes/ai.py` (free-form chat)
- **Context quality** — the user prompt provides patient history, triggered rules, ML probability, and final decision — everything needed for a meaningful explanation

### 5.2 Problems Found

**P1 — No GEMINI_API_KEY → all explanations are fallback strings**
```
File: fusion_engine.py:145-146
    if not settings.GEMINI_API_KEY:
        return "AI Explanation unavailable. (GEMINI_API_KEY not configured)"
```
Fix: Add `GEMINI_API_KEY=your_key` to `backend/.env`.

---

**P2 — System prompt placed in wrong API field**
```
File: fusion_engine.py:192
    payload = {"contents": [{"parts": [{"text": f"{system_prompt}\n\nUser: {user_prompt}"}]}]}
```
Concatenating system_prompt into the user content role reduces instruction-following for Gemini 1.5+.

Correct structure:
```python
payload = {
    "system_instruction": {"parts": [{"text": system_prompt}]},
    "contents": [{"parts": [{"text": user_prompt}]}],
    "generationConfig": {"maxOutputTokens": 150, "temperature": 0.2}
}
```

---

**P3 — Model version likely deprecated**
```
File: config.py:70
    GEMINI_MODEL: str = "gemini-1.5-flash"
```
Update to `"gemini-2.0-flash"` or `"gemini-2.5-flash"` (verify at aistudio.google.com).

---

**P4 — No `maxOutputTokens` constraint**
No `generationConfig` in the payload. A verbose response can be very long and display poorly in the UI. Add `"maxOutputTokens": 150` and `"temperature": 0.2` for clinical determinism.

---

**P5 — Dashboard ignores backend explanation**
```
File: Dashboard.tsx:195-196 — static explanation string hardcoded
```
`TelemetryResponse.explanation` (schemas.py:221) is populated by the backend but never fetched or rendered by the web UI. The real Gemini output is discarded.

---

**P6 — `/ai/chat` route has no clinical safety constraints**
```
File: routes/ai.py:18
    system_prompt: Optional[str] = Field(default="You are a helpful health assistant.")
```
Callers can inject any system prompt into the free-form `/ai/chat` endpoint. For a clinical system, this should have mandatory safety guardrails or be gated behind authentication.

---

## 6. Root Cause Summary

| Break | Root Cause | Fix |
|---|---|---|
| No model file | Training never run | Run `preprocess_kaggle_vitals.py` then `train_model.py` |
| Version mismatch v1.0.1 vs v1.0.2 | Config and training script diverged | `config.py:73` → `"v1.0.2"` |
| 3/5 features always NaN (BIDMC) | Wrong dataset for feature vector | Switch to Human Vital Signs 2024 Kaggle |
| -1.0 imputation in train, 0.0 at inference | Inconsistent preprocessing | Use mean imputation consistently |
| Circular labels | Labels from same rules as pipeline | Limitation to document; not fixable without external outcome data |
| Fabricated evaluation metrics | `evaluate_model.py` uses `np.random` | Replace with real evaluation after training |
| Gemini always returning fallback | No API key in `.env` | Add `GEMINI_API_KEY=...` |
| System prompt in wrong API role | Payload structure incorrect | Add `system_instruction` field |
| Frontend shows hardcoded values | Dashboard never connected to API | Fetch from `/fusion_risk` endpoint |
| Train-serve skew on imputation | `v.get(f, 0.0)` vs `-1.0` in training | Make imputation consistent |

---

## 7. Repair Plan — Ordered by Priority

### A: Core Training (1-2 days)

1. **Fix version** — `config.py:73`: `"v1.0.1"` → `"v1.0.2"` (1 line)
2. **Download Kaggle dataset** — Human Vital Signs 2024 (manual or `kaggle datasets download`)
3. **Write `scripts/preprocess_kaggle_vitals.py`** — rename columns, convert Fahrenheit, create patient groups, derive labels using exact same thresholds as `fusion_engine.py`
4. **Fix imputation** — change `-1.0` to mean imputation in `train_model.py:98-99`
5. **Fix inference skew** — `prediction_service.py:87`: `v.get(f, 0.0)` → use scaler mean for missing values
6. **Run training** → `data/models/v1.0.2/` gets populated
7. **Run real evaluation** — `scripts/evaluate_system.py` with real model
8. **Delete or replace** `backend/ml/evaluate_model.py` and `backend/ml/results/`

### B: Gemini Fix (1 hour)

1. Add `GEMINI_API_KEY` to `backend/.env`
2. Update model to `gemini-2.0-flash` in `config.py:70`
3. Fix payload structure: add `system_instruction`, add `generationConfig`
4. Connect `Dashboard.tsx` to `/api/v1/patients/{id}/fusion_risk` endpoint to display real explanation

### C: Frontend Connection (2-4 hours)

1. Set `VITE_USE_MOCK_DATA=false` in frontend `.env`
2. Add `useQuery` for fusion risk in Dashboard
3. Display `fused_decision.fusion_method` in UI so judges can see "weighted_fusion" vs "deterministic_only"
4. Show `ml_risk_probability` from real fusion result, not hardcoded 0.15

---

## 8. What "Done" Looks Like

When all repairs are complete, a telemetry call with 60+ readings returns:

```json
{
  "status": "warning",
  "fused_decision": {
    "final_risk_level": "warning",
    "ml_risk_probability": 0.61,
    "fusion_method": "weighted_fusion",
    "deterministic_flags": ["Abnormal Heart Rate"]
  },
  "explanation": "This patient's elevated heart rate of 125 bpm has triggered a deterministic warning flag consistent with clinical tachycardia guidelines. The ML model assigns a 61% probability to the warning class. No critical thresholds have been breached. Continued monitoring is recommended."
}
```

Startup log:
```
INFO: Loading PredictionService artifacts from data/models/v1.0.2
INFO: ✅ ML prediction service initialized
```

---

*End of AI Engine Report — HealSense*  
*All findings are evidence-based and directly file-cited.*
