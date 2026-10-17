# Safety & Imputation Hardening — v1.1

**Date:** 17 October 2026
**Scope:** Two correctness defects in the decision pipeline
**Status:** Implemented, unit-tested (11 new tests), no regressions (32 existing tests pass)

---

## 1. Safety Invariant 2 — the ML layer may not originate a CRITICAL decision

### Defect

`fusion_engine.fuse_risk()` computed a weighted score `det × 0.6 + ml × 0.4` whenever the
deterministic layer did **not** report CRITICAL. Consider a patient the rules classify as
WARNING, where the LSTM predicts `critical` with high probability:

```
0.6 × 0.5 (WARNING)  +  0.4 × 1.0 (ML critical)  =  0.70  ≥ 0.70  →  CRITICAL
```

The resulting CRITICAL alarm was **authored entirely by the ML layer**. This violated the
project's stated safety principle:

> *"The ML model and LLM layer can NEVER override a CRITICAL classification made by the
> deterministic rules engine."*

The principle was enforced in only one direction. Inference could not *downgrade* a
rules-authored CRITICAL (that override is unconditional and correct), but it *could*
*upgrade* a WARNING into a CRITICAL — a false-positive alarm path that no clinical rule
authorised.

### Fix

`backend/api/services/fusion_engine.py` — a cap is applied after threshold classification:

```python
det_class = deterministic_output["risk_class"]
ml_escalation_capped = False
if final_risk == "critical" and det_class != HealthStatus.CRITICAL:
    final_risk = "warning"
    ml_escalation_capped = True
```

The fused response now reports `ml_escalation_capped: true/false` so the behaviour is
observable in the API, the WebSocket payload, and the report.

### Resulting authority model

| Deterministic | ML prediction | Final | Rationale |
|---|---|---|---|
| CRITICAL | any | **CRITICAL** | Absolute override — unchanged |
| WARNING | critical | **WARNING** (capped) | ML cannot invent a critical |
| NORMAL | critical | **WARNING** | ML early-warning authority preserved |
| NORMAL | warning | **NORMAL** | `0.6×0 + 0.4×0.5 = 0.20 < 0.40` threshold |
| any | none | deterministic only | Unchanged |

**Stated plainly:** the ML layer's entire escalation authority is *"request a warning."*
It can never create a critical state.

---

## 2. Train/serve imputation skew — missing values are now imputed identically

### Defect

Training and inference used **different** replacement values for missing features:

| Stage | Missing value filled with | File |
|---|---|---|
| Training | `-1.0` | `scripts/train_model.py:98` (pre-fix) |
| Inference | `0.0` | `backend/api/services/prediction_service.py:87` (pre-fix) |

Two compounding consequences:

1. **Physiological impossibility** — `-1.0 °C` body temperature. The `StandardScaler` fitted a
   bimodal distribution with a large mass at −1.0, and columns that were entirely missing
   (temperature and both BPs in BIDMC) collapsed to near-zero variance, making
   `(x − μ)/σ` explode for any real value.
2. **Train/serve skew** — every inference call fed `0.0` into a scaler that had been fitted
   on `-1.0`. Predictions were arithmetically corrupted even when a model existed.

A third, related defect: missing BP was silently replaced with `120/80` at three separate
points (`telemetry_service`, `fusion_engine.create_canonical_feature_vector`), fabricating
data that was never measured.

### Fix

1. **Training** (`scripts/train_model.py`): missing values are filled with the
   **training-split median** per feature. Medians are persisted to
   `data/models/<version>/imputer.pkl` together with the feature order and fallbacks.
   A missing-data report is printed so the feature coverage is visible at training time.
2. **Inference** (`prediction_service.py`): loads the **same** `imputer.pkl` and applies it
   through `_resolve_feature()`. No `0.0`. No `-1.0`. If the artifact is absent, the service
   logs a warning and uses documented clinical fallbacks, reporting
   `imputation_source` in every prediction.
3. **Missing BP is no longer fabricated.** `systolic_bp`/`diastolic_bp` remain `None` when
   unmeasured; the rules engine skips BP rules via explicit `is not None` guards rather
   than inventing a normal reading.
4. `scripts/generate_synthetic_data.py` thresholds were aligned to match
   `fusion_engine.py` exactly (previously HR > 130 / SpO₂ < 90 vs the rules' > 150 / < 92).

### Why medians rather than mean or forward-fill

- **Median** is robust to the skew and outliers typical of physiological data.
- It is a single scalar per feature, so it is trivially reproducible at inference.
- Forward-fill was rejected because it requires per-patient state in the inference path and
  would still require a defined value for a patient's first reading.

> **Limitation to state in the report:** median imputation compresses the variance of
> missing features. A missing-indicator channel (5 extra binary features) is the
> recommended next step once the training dataset contains all five features; it lets the
> model *know* a value was imputed rather than silently receiving a plausible number.

---

## 3. Test evidence

New suite: `backend/tests/test_fusion_safety.py` — 11 tests, all passing.

```
test_ml_cannot_escalate_warning_to_critical        PASSED
test_ml_cannot_escalate_normal_to_critical         PASSED
test_ml_can_still_raise_normal_to_warning          PASSED
test_ml_warning_alone_does_not_change_normal       PASSED
test_deterministic_critical_is_absolute            PASSED
test_deterministic_only_mode_reports_no_cap        PASSED
test_missing_bp_stays_none_in_canonical_vector     PASSED
test_missing_bp_does_not_crash_or_trip_rules       PASSED
test_hypertensive_crisis_still_detected_when_bp_present PASSED
test_missing_values_use_medians_never_zero         PASSED
test_present_values_are_never_overwritten          PASSED
```

Existing suite: **32 passed**. Two pre-existing failures (`test_db_endpoints.py`,
`test_phone_integration.py`) are live-server smoke scripts that call
`http://localhost:5000` and require a running instance; they are not unit tests and are
unaffected by these changes.

Run command:

```bash
cd backend
DATABASE_URL="sqlite:///./_test.db" python -m pytest tests/test_fusion_safety.py -v
```

---

## 4. Defence-ready summary

> *"The fusion engine enforces two invariants. First, a CRITICAL authored by the
> deterministic rules is absolute and cannot be downgraded by either the LSTM or the LLM.
> Second, the ML layer can raise a patient to WARNING but can never itself originate a
> CRITICAL alarm. Imputation is performed once on the training split using per-feature
> medians, persisted as an artifact, and applied identically at inference, eliminating
> train/serve skew. Both invariants are covered by regression tests."*
